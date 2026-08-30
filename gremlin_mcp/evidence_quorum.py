from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT

SCHEMA = "GREMLIN_EVIDENCE_FAMILY_QUORUM_V0_1"
VERSION = "0.1.0"

QUORUM_SUFFICIENT = "FAMILY_QUORUM_SUFFICIENT"
QUORUM_INSUFFICIENT = "FAMILY_QUORUM_INSUFFICIENT"
CONFLICT_DEFER_TO_HOUND = "FAMILY_CONFLICT_DEFER_TO_HOUND"
NO_RESOLVED_EVIDENCE = "NO_RESOLVED_EVIDENCE"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _family_set(rows: Iterable[Mapping[str, Any]], stance: str) -> set[str]:
    out: set[str] = set()
    for row in rows:
        if str(row.get("stance") or "").strip().upper() != stance:
            continue
        family = str(row.get("source_family") or "").strip()
        if not family:
            raise ValueError("every resolved evidence row must contain source_family")
        out.add(family)
    return out


def assess_family_quorum(
    evidence: Iterable[Mapping[str, Any]],
    *,
    min_unipolar_families: int = 2,
) -> dict[str, Any]:
    """Assess provenance-family diversity without treating it as independence proof.

    The quorum applies only to unipolar evidence. Mixed SUPPORT/CONTRADICT evidence is
    always delegated to the contradiction/HOUND gate; family counts cannot vote away a
    contradiction.
    """
    minimum = int(min_unipolar_families)
    if not 1 <= minimum <= 8:
        raise ValueError("min_unipolar_families must be in [1, 8]")

    rows = [dict(row) for row in evidence]
    resolved = [
        row
        for row in rows
        if str(row.get("stance") or "").strip().upper() in {SUPPORT, CONTRADICT}
    ]
    support_families = _family_set(resolved, SUPPORT)
    contradict_families = _family_set(resolved, CONTRADICT)
    conflict = bool(support_families and contradict_families)

    if conflict:
        state = CONFLICT_DEFER_TO_HOUND
        applicable = False
        satisfied = None
        candidate_stance = None
    elif support_families:
        state = QUORUM_SUFFICIENT if len(support_families) >= minimum else QUORUM_INSUFFICIENT
        applicable = True
        satisfied = len(support_families) >= minimum
        candidate_stance = SUPPORT
    elif contradict_families:
        state = QUORUM_SUFFICIENT if len(contradict_families) >= minimum else QUORUM_INSUFFICIENT
        applicable = True
        satisfied = len(contradict_families) >= minimum
        candidate_stance = CONTRADICT
    else:
        state = NO_RESOLVED_EVIDENCE
        applicable = True
        satisfied = False
        candidate_stance = None

    core = {
        "state": state,
        "candidate_stance": candidate_stance,
        "minimum_unipolar_provenance_families": minimum,
        "support_family_count": len(support_families),
        "contradict_family_count": len(contradict_families),
        "support_families": sorted(support_families),
        "contradict_families": sorted(contradict_families),
        "conflict_present": conflict,
        "quorum_gate_applicable": applicable,
        "quorum_satisfied": satisfied,
        "family_semantics": "PROVENANCE_DIVERSITY_HEURISTIC_NOT_INDEPENDENCE_PROOF",
        "conflict_policy": "SUPPORT_CONTRADICT_CONFLICT_ALWAYS_DEFERRED_TO_HOUND_NOT_MAJORITY_VOTE",
        "confidence_policy": "CONFIDENCE_METADATA_DOES_NOT_SUBSTITUTE_FOR_FAMILY_DIVERSITY",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "quorum_commitment": _commit(b"GREMLIN-EVIDENCE-FAMILY-QUORUM/v0.1", core),
        "authority": _authority(),
    }
