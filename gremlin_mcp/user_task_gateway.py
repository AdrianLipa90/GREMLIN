from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from gremlin_mcp.authority import authority_envelope
from gremlin_mcp.router import route
from gremlin_mcp.semantic_graph_transformer import SemanticGraphTransformer
from gremlin_mcp.memory_ontology_algebra import build_memory_ontology_handoff
from gremlin_mcp.phase_memory_runtime import (
    MAX_BIAS as PHASE_MEMORY_MAX_BIAS,
    memory_order,
    validate_memory_state,
)
from tools.gremlin_bestiary_phasenav_phase_gates_v02 import PhaseState36, octopus_route
from tools.gremlin_geometry_phase_scheduler_v02 import derived_phase36

SCHEMA = "GREMLIN_USER_TASK_GATEWAY_V0_1"
VERSION = "0.1.0"
AUTHORITY = "GREMLIN_SUPERVISOR"
EPISTEMIC = "CHYBA"

_TEST_RE = re.compile(
    r"\b(test|tests|testing|benchmark|audit|debug|validate|validation|"
    r"sprawd(?:z|ź|zenie|zić)|testuj|benchmarkuj|audyt|debuguj|waliduj)\b",
    re.I,
)
_MUTATION_RE = re.compile(
    r"\b(merge|commit|push|write|update|edit|delete|remove|send|publish|deploy|"
    r"create|implement|implementuj|wdro(?:z|ż)|zmien|zmień|usuń|wyslij|wyślij|"
    r"zapisz|mergeuj)\b",
    re.I,
)
_RESEARCH_RE = re.compile(
    r"\b(search|research|find|latest|source|sources|evidence|article|paper|web|"
    r"szukaj|wyszukaj|zbadaj|najnowsz|źródł|zrodł|dowod|dowód|artykuł|publikac)\w*",
    re.I,
)
_REPO_RE = re.compile(r"\b(repo|repository|github|branch|pull request|\bpr\b|merge|commit)\b", re.I)
_LIBRARY_RE = re.compile(r"\b(library|noema|plik|file|folder|artifact|artefakt)\b", re.I)
_WORD_RE = re.compile(r"[^\W\d_][\w\-']*", re.UNICODE)
_CONTINUATION_RE = re.compile(
    r"^(?:continue|continue\s+this|go\s+on|keep\s+going|same|do\s+it|do\s+that|"
    r"kontynuuj|dalej|jedź\s+dalej|jedz\s+dalej|rób\s+dalej|rob\s+dalej|"
    r"zrób\s+to|zrob\s+to|to\s+dalej|tak|ok|okej)[.!?\s]*$",
    re.I,
)
_DEICTIC_RE = re.compile(
    r"\b(this|that|it|same|previous|above|to|tego|tym|tamto|poprzedni|poprzednie)\b",
    re.I,
)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("gateway payload must be finite JSON data") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str, *, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    if len(out) > max_chars:
        raise ValueError(f"{field} exceeds {max_chars} characters")
    return out


def _context(value: Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("context must be a sequence of strings")
    if len(value) > 32:
        raise ValueError("context supports at most 32 documents")
    out: list[str] = []
    total = 0
    for index, item in enumerate(value):
        text = _text(item, f"context[{index}]", max_chars=50_000)
        total += len(text)
        if total > 250_000:
            raise ValueError("context exceeds 250000 total characters")
        out.append(text)
    return out


def _seed_terms(task: str, compiled: Mapping[str, Any], *, limit: int = 8) -> list[str]:
    graph = compiled.get("graph")
    if not isinstance(graph, Mapping):
        return []
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        return []
    known = {str(row.get("term")) for row in nodes if isinstance(row, Mapping)}
    out: list[str] = []
    for raw in _WORD_RE.findall(task.casefold()):
        term = raw.strip("-_'")
        if len(term) < 2 or term not in known or term in out:
            continue
        out.append(term)
        if len(out) >= limit:
            break
    return out


def _context_routing_mode(task: str, has_context: bool) -> str:
    if not has_context:
        return "NO_CONTEXT"
    stripped = " ".join(task.strip().split())
    if _CONTINUATION_RE.fullmatch(stripped):
        return "CONTINUATION_CONTEXT"
    words = _WORD_RE.findall(stripped)
    if len(words) <= 6 and _DEICTIC_RE.search(stripped):
        return "CONTINUATION_CONTEXT"
    return "TASK_ONLY"


def _intent_flags(task: str) -> dict[str, bool]:
    return {
        "validation": bool(_TEST_RE.search(task)),
        "mutation": bool(_MUTATION_RE.search(task)),
        "research": bool(_RESEARCH_RE.search(task)),
        "repository": bool(_REPO_RE.search(task)),
        "library": bool(_LIBRARY_RE.search(task)),
    }


def _policy_species(flags: Mapping[str, bool]) -> list[str]:
    out: list[str] = []
    if flags.get("validation"):
        out.extend(("HOUND", "MANTIS"))
    if flags.get("mutation") and "HOUND" not in out:
        out.append("HOUND")
    return out


def _merge_species(
    semantic_species: Sequence[str],
    policy_species: Sequence[str],
    *,
    max_total_species: int,
) -> list[str]:
    out: list[str] = []
    for raw in [*semantic_species, *policy_species]:
        name = str(raw).strip().upper()
        if not name or name in out:
            continue
        out.append(name)
        if len(out) >= max_total_species:
            break
    return out


def _phase_schedule_order(phase36: Sequence[float], species: Sequence[str]) -> tuple[list[str], dict[str, float]]:
    if not species:
        return [], {}
    state = PhaseState36(phase36)
    result = octopus_route(
        state,
        list(species),
        max_species=max(1, len(species)),
        min_score=0.0,
    )
    rows = ((result.get("data") or {}).get("routes") or [])
    ordered = [str(row["species"]) for row in rows if isinstance(row, Mapping) and row.get("species")]
    scores = {
        str(row["species"]): float(row["score"])
        for row in rows
        if isinstance(row, Mapping) and row.get("species") is not None and row.get("score") is not None
    }
    for name in species:
        if name not in ordered:
            ordered.append(name)
    return ordered, scores


def _live_witness(surface_root: str) -> dict[str, Any]:
    root = Path(surface_root)
    witness: dict[str, Any] = {
        "surface_root": str(root),
        "present": root.is_dir(),
        "used_for_semantic_route": False,
        "used_for_species_inclusion": False,
    }
    if not root.is_dir():
        return witness
    for name in ("phi", "aux_phi", "working_state.json"):
        path = root / name
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        witness[name] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    return witness


def _tool_hints(flags: Mapping[str, bool]) -> list[str]:
    out: list[str] = []
    if flags.get("repository"):
        out.append("GITHUB")
    if flags.get("library"):
        out.append("LIBRARY")
    if flags.get("research"):
        out.append("WEB")
    return out


def build_user_task_plan(
    task: str,
    *,
    context: Sequence[str] | None = None,
    request_id: str | None = None,
    max_species: int = 4,
    max_total_species: int = 7,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
    max_neighbors: int = 6,
    causal_depth: int = 2,
    surface_root: str = "/dev/shm/ciel_noema",
    phase_memory_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one user task into GREMLIN + PhaseNav execution state.

    OCTOPUS owns specialist inclusion. PhaseNav may reorder the admitted mask for
    scheduling locality, but cannot add/remove semantic specialists. Explicit
    validation policy may append HOUND/MANTIS. External effects remain outside
    this gateway and require the host's normal authorization boundary.
    """
    text = _text(task, "task", max_chars=50_000)
    docs = _context(context)
    if isinstance(max_species, bool) or not isinstance(max_species, int) or not 1 <= max_species <= 8:
        raise ValueError("max_species must be in 1..8")
    if (
        isinstance(max_total_species, bool)
        or not isinstance(max_total_species, int)
        or not max_species <= max_total_species <= 10
    ):
        raise ValueError("max_total_species must be in max_species..10")
    if isinstance(causal_depth, bool) or not isinstance(causal_depth, int) or not 0 <= causal_depth <= 8:
        raise ValueError("causal_depth must be in 0..8")

    compiler = SemanticGraphTransformer(max_neighbors=max_neighbors)
    compiled = compiler.compile([text, *docs])
    task_compiled = compiled if not docs else compiler.compile([text])
    context_routing_mode = _context_routing_mode(text, bool(docs))
    seeds = (
        []
        if context_routing_mode == "CONTINUATION_CONTEXT"
        else _seed_terms(text, compiled)
    )
    if seeds:
        cone = compiler.causal_cone(compiled, seeds, depth=causal_depth)
        active_graph = {
            "nodes": cone["nodes"],
            "relations": cone["relations"],
            "relation_codes": compiled["graph"]["relation_codes"],
        }
        cone_status = "BOUNDED_CAUSAL_CONE"
    else:
        cone = None
        active_graph = compiled["graph"]
        cone_status = "FULL_GRAPH_NO_SEED"

    flags = _intent_flags(text)
    active_terms = [str(row["term"]) for row in active_graph["nodes"][:128]]
    task_terms = [str(row["term"]) for row in task_compiled["graph"]["nodes"][:128]]
    routing_terms = (
        active_terms
        if context_routing_mode == "CONTINUATION_CONTEXT"
        else task_terms
    )
    semantic_payload = {
        "task": text,
        "active_terms": routing_terms,
        "intent_flags": flags,
    }
    semantic_route = route(
        semantic_payload,
        max_species=max_species,
        min_score=min_score,
        relative_cutoff=relative_cutoff,
    )
    semantic_species = [str(x) for x in semantic_route.get("route_mask") or []]
    policy_species = _policy_species(flags)
    included_species = _merge_species(
        semantic_species,
        policy_species,
        max_total_species=max_total_species,
    )

    active_graph_sha256 = _sha(active_graph)
    task_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    gateway_task_id = request_id or f"task:{task_sha256[:16]}"
    memory_ontology = build_memory_ontology_handoff(
        subject_id=f"user-task:{task_sha256}",
        generation_id=f"graph:{compiled['graph_sha256']}",
        task_id=gateway_task_id,
        context_commitment=f"sha256:{active_graph_sha256}",
    )
    phase_payload = {
        "task": text,
        "active_graph_sha256": active_graph_sha256,
        "semantic_route_commitment": semantic_route.get("route_commitment"),
        "included_species": included_species,
    }
    phase36 = derived_phase36(phase_payload)
    base_phase_order, base_phase_scores = _phase_schedule_order(phase36, included_species)
    if phase_memory_state is None:
        phase_order = list(base_phase_order)
        phase_scores = dict(base_phase_scores)
        phase_memory = {
            "applied": False,
            "state_commitment": None,
            "sequence": 0,
            "max_bias": 0.0,
        }
    else:
        memory_state = validate_memory_state(phase_memory_state)
        phase_order, phase_scores = memory_order(
            base_phase_order,
            base_phase_scores,
            memory_state,
            max_bias=PHASE_MEMORY_MAX_BIAS,
        )
        if (
            len(phase_order) != len(base_phase_order)
            or set(phase_order) != set(base_phase_order)
            or set(phase_scores) != set(base_phase_scores)
        ):
            raise ValueError(
                "phase memory may reorder OCTOPUS membership but cannot change it"
            )
        phase_memory = {
            "applied": True,
            "state_commitment": memory_state["commitment"],
            "sequence": memory_state["sequence"],
            "last_role": memory_state["last_role"],
            "max_bias": PHASE_MEMORY_MAX_BIAS,
            "base_phase_scores": dict(base_phase_scores),
            "memory_adjusted_scores": dict(phase_scores),
            "membership_changed": set(phase_order) != set(base_phase_order),
        }

    mode = "DIRECT" if not included_species else "GREMLIN_ROUTED"
    action_authority = (
        "GREMLIN_SUPERVISED_EXTERNAL_ADMISSION_REQUIRED"
        if flags["mutation"]
        else "GREMLIN_SUPERVISED_INTERNAL_ONLY"
    )
    action_envelope = authority_envelope(
        admission_basis=(
            "EXPLICIT_OPERATOR_AND_CONSTITUTION_REQUIRED"
            if flags["mutation"]
            else "INTERNAL_GREMLIN"
        )
    )
    live = _live_witness(surface_root)
    context_commitments = [hashlib.sha256(item.encode("utf-8")).hexdigest() for item in docs]
    compact_graph = {
        "schema": compiled["schema"],
        "graph_sha256": compiled["graph_sha256"],
        "active_graph_sha256": active_graph_sha256,
        "mode": cone_status,
        "seeds": seeds,
        "metrics": compiled["metrics"],
        "active_nodes": len(active_graph["nodes"]),
        "active_relations": len(active_graph["relations"]),
        "nodes": active_graph["nodes"],
        "relations": active_graph["relations"],
        "relation_codes": active_graph["relation_codes"],
    }
    worker_payload = {
        "schema": "GREMLIN_USER_TASK_WORKER_PAYLOAD_V0_1",
        "task": text,
        "request_id": request_id,
        "semantic_graph": compact_graph,
        "phasenav": {
            "space": "T^36",
            "phase36": list(phase36),
            "schedule_order": phase_order,
            "phase_scores": phase_scores,
            "base_phase_scores": base_phase_scores,
            "phase_memory": phase_memory,
            "species_inclusion_authority": False,
        },
        "context_sha256": context_commitments,
        "memory_ontology": {
            "source_contract_sha256": memory_ontology["source_contract_sha256"],
            "historical_signature": memory_ontology["historical_signature"],
            "behavioral_signature": memory_ontology["behavioral_signature"],
            "certified_behavioral_core": memory_ontology["certified_behavioral_core"],
            "authority": memory_ontology["authority"],
            "canon_allowed": memory_ontology["canon_allowed"],
        },
        "intent_flags": flags,
        "authority_mode": action_authority,
        "authority": action_envelope,
    }

    plan: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "READY",
        "mode": mode,
        "request_id": request_id,
        "task_sha256": task_sha256,
        "semantic_graph": compact_graph,
        "memory_ontology": memory_ontology,
        "context_routing": {
            "mode": context_routing_mode,
            "context_count": len(docs),
            "context_may_change_species_membership": context_routing_mode == "CONTINUATION_CONTEXT",
            "task_only_for_explicit_new_task": True,
        },
        "octopus": {
            "status": semantic_route.get("status"),
            "semantic_route": semantic_species,
            "route_commitment": semantic_route.get("route_commitment"),
            "policy_validation_species": policy_species,
            "final_species_membership": included_species,
            "species_inclusion_authority": "OCTOPUS_PLUS_EXPLICIT_VALIDATION_POLICY",
        },
        "phasenav": {
            "space": "T^36",
            "dimension": 36,
            "phase36": list(phase36),
            "state_id": PhaseState36(phase36).state_id,
            "schedule_order": phase_order,
            "phase_scores": phase_scores,
            "base_phase_scores": base_phase_scores,
            "phase_memory": phase_memory,
            "role": "SCHEDULING_LOCALITY_ORDER_AND_BOUNDED_MEMORY_HINT",
            "may_change_species_membership": False,
            "live_surface_witness": live,
        },
        "execution": {
            "route_species": phase_order,
            "queue_recommended": bool(phase_order),
            "host_tool_hints": _tool_hints(flags),
            "external_effects_authorized": False,
            "requires_explicit_external_authorization": bool(flags["mutation"]),
            "authority_mode": action_authority,
            "authority": action_envelope,
        },
        "worker_payload": worker_payload,
        "claims": {
            "default_user_task_entrypoint": True,
            "semantic_graph_compiled": True,
            "memory_ontology_algebra_bound": True,
            "phasenav_bound": True,
            "phase_memory_law_bound": phase_memory_state is not None,
            "phase_memory_changes_membership": False,
            "phasenav_overrides_semantic_membership": False,
            "stale_context_can_override_explicit_task_membership": False,
            "trained_neural_transformer_claim": False,
            "answer_quality_measured": False,
            "external_effect_admitted": False,
            "canon_promotion_admitted": False,
        },
        "epistemic": EPISTEMIC,
        "authority_mode": AUTHORITY,
        "authority": action_envelope,
    }
    plan["plan_sha256"] = _sha(plan)
    return plan


__all__ = ["SCHEMA", "VERSION", "build_user_task_plan"]
