from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping

from gremlin_mcp.pipeline import SPECIALISTS, fanout
from gremlin_mcp.workers import WorkerBroker

ROUTER_SCHEMA = "GREMLIN_MCP_OCTOPUS_ROUTER_V0_6"
ROUTER_VERSION = "0.6.0"
ROUTER_MODE = "DETERMINISTIC_AUDITABLE_SEMANTIC_ROUTER"
SEMANTIC_PROFILE = "OCTOPUS_LEXICAL_OOD_PROFILE_V0_6"
ROUTE_DOMAIN = b"GREMLIN-MCP-OCTOPUS-ROUTE/v0.6\x00"


@dataclass(frozen=True)
class Cue:
    term: str
    weight: float


# v0.6 keeps the router transparent and deterministic while widening the
# semantic surface beyond the frozen in-distribution vocabulary. Generic cues
# are deliberately weak; specialist-specific phrases and stems carry more
# weight. Single-token matches are token-aware, not raw substrings.
CUES: dict[str, tuple[Cue, ...]] = {
    "SPIDER": (
        Cue("relation", 3.0), Cue("relationship", 3.0), Cue("dependency", 3.0),
        Cue("dependencies", 3.0), Cue("graph", 3.0), Cue("edge", 1.5), Cue("node", 1.5),
        Cue("link", 1.5), Cue("network", 1.5), Cue("isomorphism", 4.0),
        Cue("mapping", 1.5), Cue("topology", 3.0), Cue("bridge", 1.5),
        Cue("connect", 1.5), Cue("structure", 1.5), Cue("structural connection", 3.0),
        Cue("structural connections", 3.0), Cue("fit together", 3.0),
        Cue("interconnection", 3.0), Cue("interconnections", 3.0),
        Cue("association", 2.0), Cue("associations", 2.0), Cue("trace links", 3.0),
        Cue("powiaz", 3.0), Cue("zalezn", 3.0), Cue("relacj", 3.0),
        Cue("polaczen", 3.0), Cue("siec", 1.5), Cue("mapuj", 2.5), Cue("struktura", 1.5),
    ),
    "RAVEN": (
        Cue("memory", 4.0), Cue("recall", 4.0), Cue("remember", 3.0),
        Cue("previous", 1.0), Cue("prior", 1.0), Cue("history", 3.0), Cue("archive", 3.0),
        Cue("earlier", 1.0), Cue("similar", 1.0), Cue("precedent", 3.0), Cue("retrieve", 3.0),
        Cue("past work", 3.0), Cue("earlier work", 3.0), Cue("retrieve context", 4.0),
        Cue("bring back context", 4.0), Cue("used before", 3.0),
        Cue("pamiec", 4.0), Cue("wczesn", 1.0), Cue("poprzed", 1.0),
        Cue("histori", 3.0), Cue("archiw", 3.0), Cue("przywol", 3.0), Cue("kontekst", 1.5),
    ),
    "HOUND": (
        Cue("contradiction", 4.0), Cue("inconsistent", 4.0), Cue("inconsistency", 4.0),
        Cue("inconsistencies", 4.0), Cue("anomaly", 4.0), Cue("error", 3.0),
        Cue("bug", 3.0), Cue("fail", 3.0), Cue("failure", 3.0), Cue("mismatch", 4.0),
        Cue("falsify", 4.0), Cue("falsification", 4.0), Cue("test", 2.0),
        Cue("verify", 2.0), Cue("validate", 2.0), Cue("regression", 3.0), Cue("debug", 3.0),
        Cue("discrepancy", 4.0), Cue("challenge assumptions", 4.0), Cue("stress check", 4.0),
        Cue("stress-check", 4.0), Cue("sanity check", 3.0), Cue("look for problems", 3.0),
        Cue("spot issues", 3.0), Cue("sprzecz", 4.0), Cue("blad", 3.0), Cue("testuj", 2.0),
        Cue("sprawdz", 2.0), Cue("niezgodn", 4.0), Cue("anomali", 4.0),
        Cue("weryfik", 2.0), Cue("walid", 2.0),
    ),
    "MOLE": (
        Cue("derive", 4.0), Cue("derivation", 4.0), Cue("proof", 4.0), Cue("equation", 3.0),
        Cue("formula", 3.0), Cue("solve", 3.0), Cue("mechanism", 3.0), Cue("theorem", 3.0),
        Cue("calculate", 2.0), Cue("compute", 2.0), Cue("local", 0.5), Cue("deep", 0.5),
        Cue("inspect", 1.5), Cue("deduce", 4.0), Cue("infer", 3.0), Cue("work out", 4.0),
        Cue("show the math", 4.0), Cue("mathematics", 2.0), Cue("expression", 2.0),
        Cue("obtain expression", 4.0), Cue("wyprowadz", 4.0), Cue("rownan", 3.0),
        Cue("oblicz", 2.0), Cue("dowod", 4.0), Cue("wzor", 3.0), Cue("policz", 2.0),
        Cue("rozwiaz", 3.0), Cue("mechanizm", 3.0),
    ),
    "OWL": (
        Cue("audit", 4.0), Cue("evidence", 4.0), Cue("source", 3.0), Cue("citation", 3.0),
        Cue("provenance", 4.0), Cue("claim", 2.0), Cue("confidence", 3.0), Cue("epistemic", 4.0),
        Cue("validity", 3.0), Cue("status", 0.5), Cue("review", 1.5), Cue("methodology", 2.0),
        Cue("quality", 1.5), Cue("verify evidence", 4.0), Cue("literature", 3.0),
        Cue("references", 3.0), Cue("supporting sources", 4.0), Cue("backed by sources", 4.0),
        Cue("audyt", 4.0), Cue("zrodl", 3.0), Cue("dowody", 3.0), Cue("cytow", 3.0),
        Cue("literatur", 3.0), Cue("metodolog", 2.0), Cue("wiarygodn", 3.0),
    ),
    "ANT": (
        Cue("enumerate", 4.0), Cue("combination", 4.0), Cue("combinations", 4.0),
        Cue("permutation", 4.0), Cue("search space", 3.0), Cue("grid", 3.0), Cue("sweep", 3.0),
        Cue("brute force", 4.0), Cue("candidate set", 1.5), Cue("variants", 2.0),
        Cue("alternatives", 2.0), Cue("all options", 4.0), Cue("possible configurations", 4.0),
        Cue("alternative candidates", 3.0), Cue("search possibilities", 3.0),
        Cue("enumeruj", 4.0), Cue("kombinac", 4.0), Cue("wariant", 2.0),
        Cue("przeszuk", 3.0), Cue("mozliw", 2.0), Cue("konfigurac", 3.0),
    ),
    "MANTIS": (
        Cue("duplicate", 4.0), Cue("deduplicate", 4.0), Cue("redundant", 4.0),
        Cue("prune", 4.0), Cue("dead branch", 4.0), Cue("obsolete", 3.0), Cue("cleanup", 3.0),
        Cue("simplify", 1.5), Cue("merge duplicate", 4.0), Cue("overlap", 2.0),
        Cue("clean up", 3.0), Cue("remove repeats", 4.0), Cue("repeated branches", 3.0),
        Cue("collapse duplicates", 4.0), Cue("trim branches", 3.0),
        Cue("equivalent candidates", 2.0), Cue("duplik", 4.0), Cue("usun", 2.0),
        Cue("przytn", 3.0), Cue("redund", 4.0), Cue("powtorz", 3.0), Cue("zbedn", 2.0),
    ),
}

# Prefix matching is token-prefix matching, never arbitrary substring matching.
# This covers normal inflection/plurals and Polish stems while blocking traps
# such as "contest" -> "test".
PREFIX_CUES = frozenset({
    "relation", "relationship", "dependency", "contradiction", "inconsistent",
    "anomaly", "error", "fail", "failure", "mismatch", "falsify", "falsification",
    "regression", "derive", "derivation", "equation", "formula", "calculate", "compute",
    "source", "citation", "claim", "reference", "combination", "permutation", "variants",
    "duplicate", "redundant", "obsolete", "overlap",
    "powiaz", "zalezn", "relacj", "polaczen", "mapuj",
    "pamiec", "wczesn", "poprzed", "histori", "archiw", "przywol",
    "sprzecz", "blad", "testuj", "sprawdz", "niezgodn", "anomali", "weryfik", "walid",
    "wyprowadz", "rownan", "oblicz", "dowod", "wzor", "policz", "rozwiaz", "mechanizm",
    "zrodl", "cytow", "literatur", "metodolog", "wiarygodn",
    "enumeruj", "kombinac", "wariant", "przeszuk", "mozliw", "konfigurac",
    "duplik", "usun", "przytn", "redund", "powtorz", "zbedn",
})

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


def _tokenize(text: str) -> tuple[str, ...]:
    # Semantic matching strips punctuation instead of allowing punctuation to
    # cling to the final token (e.g. "inconsistencies." now matches correctly).
    return tuple(re.findall(r"[a-z0-9_]+", text))


def _phrase_matches(phrase: str, tokens: tuple[str, ...]) -> bool:
    parts = tuple(_tokenize(phrase))
    if not parts or len(parts) > len(tokens):
        return False
    width = len(parts)
    return any(tokens[i:i + width] == parts for i in range(len(tokens) - width + 1))


def _matches(cue: str, tokens: tuple[str, ...], token_set: frozenset[str]) -> bool:
    normalized = _normalize_text(cue)
    if " " in normalized:
        return _phrase_matches(normalized, tokens)
    if normalized in PREFIX_CUES:
        return any(token.startswith(normalized) for token in token_set)
    return normalized in token_set


def route(
    payload: Mapping[str, Any],
    *,
    max_species: int = 4,
    min_score: float = 2.0,
    relative_cutoff: float = 0.45,
) -> dict[str, Any]:
    """Produce an auditable OCTOPUS route mask from JSON payload semantics.

    v0.6 uses Unicode-normalized token/prefix/phrase evidence. It does not use
    an LLM or embeddings. A route is emitted only when positive lexical or
    structural evidence crosses the configured threshold; otherwise it fails
    closed with `NO_CONFIDENT_ROUTE`.
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
    token_set = frozenset(tokens)
    keyset = frozenset(keys)

    rows: list[dict[str, Any]] = []
    for species in SPECIALISTS:
        score = 0.0
        evidence: list[dict[str, Any]] = []
        for cue in CUES[species]:
            if _matches(cue.term, tokens, token_set):
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
        "version": ROUTER_VERSION,
        "semantic_profile": SEMANTIC_PROFILE,
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
        "semantic_profile": SEMANTIC_PROFILE,
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
            "semantic_profile": SEMANTIC_PROFILE,
            "route_commitment": decision["route_commitment"],
            "route_mask": decision["route_mask"],
        },
    )
    return {
        "schema": ROUTER_SCHEMA,
        "version": ROUTER_VERSION,
        "mode": ROUTER_MODE,
        "semantic_profile": SEMANTIC_PROFILE,
        "status": "AUTO_FANOUT_QUEUED",
        "route_mask": decision["route_mask"],
        "route_commitment": decision["route_commitment"],
        "scores": decision["scores"],
        "fanout": queued,
        "authority": _authority(),
    }
