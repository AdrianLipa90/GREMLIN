from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from gremlin_mcp.evidence_quorum import QUORUM_INSUFFICIENT, assess_family_quorum
from gremlin_mcp.semantic_bridge import apply_semantic_producer_output

SCHEMA = "GREMLIN_SEMANTIC_FAMILY_QUORUM_BRIDGE_V0_1"
VERSION = "0.1.0"
SEMANTIC_FAMILY_QUORUM_INSUFFICIENT = "SEMANTIC_EVIDENCE_FAMILY_QUORUM_INSUFFICIENT"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _attach_quorum(result: Mapping[str, Any], quorum: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(result)
    semantic = dict(out.get("semantic_evidence") or {})
    semantic["family_quorum"] = dict(quorum)
    out["semantic_evidence"] = semantic
    out["authority"] = _authority()
    out["semantic_quorum_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-FAMILY-QUORUM-EXECUTION/v0.1",
        {key: value for key, value in out.items() if key != "semantic_quorum_execution_commitment"},
    )
    return out


def apply_semantic_producer_output_with_quorum(
    execution: Mapping[str, Any],
    *,
    producer_output: Mapping[str, Any],
    hound_receipt: Mapping[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
) -> dict[str, Any]:
    """Apply the normal semantic guard, then require provenance-family diversity.

    Existing semantic-bridge behavior is preserved. This strict bridge adds a post-guard
    family-diversity gate for unipolar evidence only. Mixed SUPPORT/CONTRADICT evidence
    remains governed by the HOUND contradiction gate and is never resolved by majority.
    """
    base = apply_semantic_producer_output(
        execution,
        producer_output=producer_output,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
    )

    semantic = dict(base.get("semantic_evidence") or {})
    family_binding = semantic.get("provenance_families")
    if not isinstance(family_binding, Mapping):
        return base
    guard_evidence = family_binding.get("guard_evidence")
    if not isinstance(guard_evidence, list):
        return base

    quorum = assess_family_quorum(
        guard_evidence,
        min_unipolar_families=min_unipolar_families,
    )

    # Contradictions are handled by HOUND. Quorum must not override or vote them away.
    if quorum["conflict_present"]:
        return _attach_quorum(base, quorum)

    # If an earlier semantic/source/content gate already quarantined the result, preserve it.
    if base.get("synthesis") is None:
        return _attach_quorum(base, quorum)

    if quorum["state"] == QUORUM_INSUFFICIENT:
        out = dict(base)
        out["quarantined_synthesis"] = out.get("synthesis")
        out["synthesis"] = None
        out["status"] = SEMANTIC_FAMILY_QUORUM_INSUFFICIENT
        semantic = dict(out.get("semantic_evidence") or {})
        semantic["family_quorum"] = dict(quorum)
        semantic["synthesis_authorized"] = False
        semantic["quarantine_reason"] = "UNIPOLAR_SEMANTIC_CANDIDATE_REQUIRES_MINIMUM_PROVENANCE_FAMILY_DIVERSITY"
        out["semantic_evidence"] = semantic
        out["authority"] = _authority()
        out["semantic_quorum_execution_commitment"] = _commit(
            b"GREMLIN-SEMANTIC-FAMILY-QUORUM-EXECUTION/v0.1",
            {key: value for key, value in out.items() if key != "semantic_quorum_execution_commitment"},
        )
        return out

    return _attach_quorum(base, quorum)
