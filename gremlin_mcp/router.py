from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping

from gremlin_mcp.pipeline import SPECIALISTS, fanout
from gremlin_mcp.workers import WorkerBroker

ROUTER_SCHEMA = "GREMLIN_MCP_OCTOPUS_ROUTER_V0_5"
ROUTER_VERSION = "0.5.0"
ROUTER_MODE = "DETERMINISTIC_AUDITABLE_SEMANTIC_ROUTER"
ROUTE_DOMAIN = b"GREMLIN-MCP-OCTOPUS-ROUTE/v0.5\x00"


@dataclass(frozen=True)
class Cue:
    term: str
    weight: float


# The reference router is deliberately transparent: every route has an auditable
# finite cue set rather than an opaque model decision. Multi-word cues are
# matched as substrings after Unicode normalization; single words are matched as
# tokens. Structural payload keys add independent evidence below.
CUES: dict[str, tuple[Cue, ...]] = {
    "SPIDER": (
        Cue("relation", 3.0), Cue("relationship", 3.0), Cue("dependency", 3.0),
        Cue("dependencies", 3.0), Cue("graph", 3.0), Cue("edge", 2.0), Cue("node", 2.0),
        Cue("link", 2.0), Cue("network", 2.0), Cue("isomorphism", 4.0),
        Cue("mapping", 2.0), Cue("topology", 3.0), Cue("bridge", 2.0),
        Cue("connect", 2.0), Cue("powiaz", 2.0), Cue("zalezn", 2.0),
    ),
    "RAVEN": (
        Cue("memory", 4.0), Cue("recall", 4.0), Cue("remember", 3.0), Cue("previous", 3.0),
        Cue("prior", 3.0), Cue("history", 3.0), Cue("archive", 3.0), Cue("earlier", 2.0),
        Cue("similar", 2.0), Cue("precedent", 3.0), Cue("retrieve", 2.0),
        Cue("pamiec", 3.0), Cue("wczesniej", 2.0), Cue("poprzed", 2.0),
    ),
    "HOUND": (
        Cue("contradiction", 4.0), Cue("inconsistent", 4.0), Cue("anomaly", 4.0),
        Cue("error", 3.0), Cue("bug", 3.0), Cue("fail", 3.0), Cue("mismatch", 4.0),
        Cue("falsify", 4.0), Cue("test", 2.0), Cue("verify", 2.0), Cue("validate", 2.0),
        Cue("regression", 3.0), Cue("debug", 3.0), Cue("sprzecz", 3.0),
        Cue("blad", 3.0), Cue("testuj", 2.0),
    ),
    "MOLE": (
        Cue("derive", 4.0), Cue("derivation", 4.0), Cue("proof", 4.0), Cue("equation", 3.0),
        Cue("formula", 3.0), Cue("solve", 3.0), Cue("mechanism", 3.0), Cue("theorem", 3.0),
        Cue("calculate", 2.0), Cue("compute", 2.0), Cue("local", 1.0), Cue("deep", 2.0),
        Cue("inspect", 2.0), Cue("wyprowadz", 4.0), Cue("rownan", 3.0), Cue("oblicz", 2.0),
        Cue("dowod", 4.0),
    ),
    "OWL": (
        Cue("audit", 4.0), Cue("evidence", 4.0), Cue("source", 3.0), Cue("citation", 3.0),
        Cue("provenance", 4.0), Cue("claim", 2.0), Cue("confidence", 3.0), Cue("epistemic", 4.0),
        Cue("validity", 3.0), Cue("status", 1.0), Cue("review", 2.0), Cue("methodology", 2.0),
        Cue("quality", 2.0), Cue("verify evidence", 4.0), Cue("audyt", 4.0),
        Cue("zrodlo", 3.0), Cue("dowody", 3.0),
    ),
    "ANT": (
        Cue("enumerate", 4.0), Cue("combination", 4.0), Cue("combinations", 4.0),
        Cue("permutation", 4.0), Cue("search space", 3.0), Cue("grid", 3.0), Cue("sweep", 3.0),
        Cue("brute force", 4.0), Cue("candidate set", 3.0), Cue("variants", 2.0),
        Cue("enumeruj", 4.0), Cue("kombinac", 4.0), Cue("wariant", 2.0),
    ),
    "MANTIS": (
        Cue("duplicate", 4.0), Cue("deduplicate", 4.0), Cue("redundant", 4.0),
        Cue("prune", 4.0), Cue("dead branch", 4.0), Cue("obsolete", 3.0), Cue("cleanup", 3.0),
        Cue("simplify", 2.0), Cue("merge duplicate", 4.0), Cue("overlap", 2.0),
        Cue("duplik", 4.0), Cue("usun", 2.0), Cue("przytn", 3.0), Cue("redund", 4.0),
    ),
}

STRUCTURAL_KEYS: dict[str, frozenset[str]] = {
    "SPIDER": frozenset({"graph", "graphs", "edges", "nodes", "dependencies", "relations", "links", "topology"}),
    "RAVEN": frozenset({"memory", "history", "previous", "prior", "archive", "timeline"}),
    "HOUND": frozenset({"errors", "failures", "tests", "mismatches", "anomalies", "contradictions"}),
    "MOLE": frozenset({"equation", "equations", "formula", "derivation", "proof", "solver", "parameters"}),
    "OWL": frozenset({"sources", "citations", "evidence", "provenance", "claims", "confidence", "methodology"}),
    "ANT": frozenset({"candidates", "variants", "permutations", "combinations", "grid", "search_space"}),
    "MANTIS": frozenset({"duplicates", "redundancy", "dead_branches", "obsolete", "prune"}),
}


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be finite JSON data") from exc


def _normalize_text(value: str) -> str:
    raw = unicodedata.normalize("NFKD", value).casefold()
    return "".join(ch for ch in raw if not unicodedata.combining(ch))


def _walk(value: Any, *, strings: list[str], keys: list[str], stats: dict[str, int]) -> None:
    if isinstance(value, Mapping):
        stats["mapping_count"] += 1
        for key, child in value.items():
            key_text = _normalize_text(str(key))
            keys.append(key_text)
            strings.append(key_text.replace("_", " "))
            _walk(child, strings=strings, keys=keys, stats=stats)
    elif isinstance(value, (list, tuple)):
        stats["sequence_count"] += 1
        stats["sequence_items"] += len(value)
        for child in value:
            _walk(child, strings=strings, keys=keys, stats=stats)
    elif isinstance(value, str):
        strings.append(_normalize_text(value))
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, (int, float)):
        stats["numeric_count"] += 1
    else:
        strings.append(_normalize_text(str(value)))


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9_+./#-]+", text))


def _matches(cue: str, text: str, tokens: frozenset[str]) -> bool:
    normalized = _normalize_text(cue)
    if " " in normalized:
        return normalized in text
    # Stem-like cues ending before a natural suffix intentionally use prefix
    # matching (e.g. `zalezn` -> zaleznosc/zaleznosci).
    if normalized in {"powiaz", "zalezn", "poprzed", "sprzecz", "wyprowadz", "rownan", "oblicz", "dowod", "kombinac", "wariant", "duplik", "usun", "przytn", "redund"}:
        return any(token.startswith(normalized) for token in tokens)
    return normalized in tokens


def route(
    payload: Mapping[str, Any],
    *,
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    """Produce an auditable OCTOPUS route mask from JSON payload semantics.

    The reference router is deterministic and dependency-free. It does not use
    an LLM or embeddings. A route is emitted only when positive lexical or
    structural evidence crosses the configured threshold; otherwise the result
    is `NO_CONFIDENT_ROUTE` and nothing is queued.
    """
    if not isinstance(payload, Mapping) or not payload:
        raise ValueError("payload must be a non-empty mapping")
    body = dict(payload)
    _canonical(body)

    limit = int(max_species)
    if limit <= 0 or limit > len(SPECIALISTS):
        raise ValueError(f"max_species must be in 1..{len(SPECIALISTS)}")
    floor = float(min_score)
    cutoff = float(relative_cutoff)
    if floor <= 0:
        raise ValueError("min_score must be positive")
    if not (0.0 < cutoff <= 1.0):
        raise ValueError("relative_cutoff must be in (0, 1]")

    strings: list[str] = []
    keys: list[str] = []
    stats = {"mapping_count": 0, "sequence_count": 0, "sequence_items": 0, "numeric_count": 0}
    _walk(body, strings=strings, keys=keys, stats=stats)
    text = " \n ".join(strings)
    tokens = _tokenize(text)
    keyset = frozenset(keys)

    rows: list[dict[str, Any]] = []
    for species in SPECIALISTS:
        score = 0.0
        evidence: list[dict[str, Any]] = []
        for cue in CUES[species]:
            if _matches(cue.term, text, tokens):
                score += cue.weight
                evidence.append({"kind": "semantic_cue", "cue": cue.term, "weight": cue.weight})

        structural = sorted(keyset & STRUCTURAL_KEYS[species])
        if structural:
            structural_weight = min(6.0, 2.0 * len(structural))
            score += structural_weight
            evidence.append({"kind": "structural_keys", "keys": structural, "weight": structural_weight})

        if species == "ANT" and stats["sequence_items"] >= 16:
            score += 2.0
            evidence.append({"kind": "large_candidate_surface", "items": stats["sequence_items"], "weight": 2.0})
        if species == "MOLE" and stats["numeric_count"] >= 8:
            score += 1.0
            evidence.append({"kind": "numeric_density", "count": stats["numeric_count"], "weight": 1.0})

        rows.append({"species": species, "score": score, "evidence": evidence})

    ranked = sorted(rows, key=lambda row: (-row["score"], SPECIALISTS.index(row["species"])))
    top_score = ranked[0]["score"] if ranked else 0.0
    threshold = max(floor, top_score * cutoff)
    selected = [row for row in ranked if row["score"] >= threshold and row["score"] > 0][:limit]
    route_mask = [row["species"] for row in selected]

    commitment_core = {
        "schema": ROUTER_SCHEMA,
        "payload": body,
        "max_species": limit,
        "min_score": floor,
        "relative_cutoff": cutoff,
        "ranked": [{"species": row["species"], "score": row["score"]} for row in ranked],
        "route_mask": route_mask,
    }
    route_commitment = hashlib.blake2b(
        ROUTE_DOMAIN + _canonical(commitment_core), digest_size=32
    ).hexdigest()

    return {
        "schema": ROUTER_SCHEMA,
        "version": ROUTER_VERSION,
        "mode": ROUTER_MODE,
        "status": "ROUTE_READY" if route_mask else "NO_CONFIDENT_ROUTE",
        "route_mask": route_mask,
        "threshold": threshold,
        "scores": ranked,
        "payload_stats": stats,
        "route_commitment": route_commitment,
        "authority": _authority(),
    }


def auto_fanout(
    broker: WorkerBroker,
    payload: Mapping[str, Any],
    *,
    request_id: str | None = None,
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    """Route and enqueue a payload only when OCTOPUS has positive evidence."""
    decision = route(
        payload,
        max_species=max_species,
        min_score=min_score,
        relative_cutoff=relative_cutoff,
    )
    if not decision["route_mask"]:
        return {
            **decision,
            "status": "NO_CONFIDENT_ROUTE_NOT_QUEUED",
            "tasks": [],
        }

    queued = fanout(
        broker,
        payload,
        decision["route_mask"],
        request_id=request_id,
        route_context={
            "router_schema": ROUTER_SCHEMA,
            "router_version": ROUTER_VERSION,
            "route_commitment": decision["route_commitment"],
            "route_mask": decision["route_mask"],
        },
    )
    return {
        "schema": ROUTER_SCHEMA,
        "version": ROUTER_VERSION,
        "mode": ROUTER_MODE,
        "status": "AUTO_FANOUT_QUEUED",
        "route_mask": decision["route_mask"],
        "route_commitment": decision["route_commitment"],
        "scores": decision["scores"],
        "fanout": queued,
        "authority": _authority(),
    }
