from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from gremlin_mcp.evidence_quorum import QUORUM_INSUFFICIENT, assess_family_quorum
from gremlin_mcp.semantic_bridge import apply_semantic_producer_output

SCHEMA = "GREMLIN_SEMANTIC_FAMILY_QUORUM_BRIDGE_V0_1"
VERSION = "0.1.0"
SEMANTIC_FAMILY_QUORUM_INSUFFICIENT = "SEMANTIC_EVIDENCE_FAMILY_QUORUM_INSUFFICIENT"
SEMANTIC_FAMILY_QUORUM_BINDING_INVALID = "SEMANTIC_EVIDENCE_FAMILY_QUORUM_BINDING_INVALID"


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
        raise ValueError("semantic quorum bridge data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _authority() -> dict[str, bool]:
    return {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False}


def _strict_minimum(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("min_unipolar_families must be an integer in [1, 8]")
    if not 1 <= value <= 8:
        raise ValueError("min_unipolar_families must be in [1, 8]")
    return value


def _attach_quorum(result: Mapping[str, Any], quorum: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(result)
    semantic_raw = out.get("semantic_evidence")
    if not isinstance(semantic_raw, Mapping):
        raise ValueError("semantic_evidence must be an object before quorum attachment")
    semantic = dict(semantic_raw)
    semantic["family_quorum"] = dict(quorum)
    out["semantic_evidence"] = semantic
    out["authority"] = _authority()
    out["semantic_quorum_execution_commitment"] = _commit(
        b"GREMLIN-SEMANTIC-FAMILY-QUORUM-EXECUTION/v0.1",
        {key: value for key, value in out.items() if key != "semantic_quorum_execution_commitment"},
    )
    return out


def _quarantine_binding(result: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    out = dict(result)
    out["quarantined_synthesis"] = out.get("synthesis")
    out["synthesis"] = None
    out["status"] = SEMANTIC_FAMILY_QUORUM_BINDING_INVALID
    semantic_raw = out.get("semantic_evidence")
    semantic = dict(semantic_raw) if isinstance(semantic_raw, Mapping) else {}
    semantic["family_quorum"] = None
    semantic["synthesis_authorized"] = False
    semantic["quarantine_reason"] = reason
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
    """Apply semantic validation, then require provenance-family diversity.

    A synthesis-producing path is never allowed to bypass this strict gate merely because
    provenance-family binding is missing or malformed. Earlier fail-closed decisions remain
    preserved without attempting to re-authorize synthesis.
    """
    minimum = _strict_minimum(min_unipolar_families)
    base = apply_semantic_producer_output(
        execution,
        producer_output=producer_output,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
    )
    if not isinstance(base, Mapping):
        raise ValueError("semantic bridge result must be an object")

    semantic_raw = base.get("semantic_evidence")
    if not isinstance(semantic_raw, Mapping):
        if base.get("synthesis") is None:
            return dict(base)
        return _quarantine_binding(
            base,
            reason="SEMANTIC_EVIDENCE_OBJECT_REQUIRED_BEFORE_STRICT_FAMILY_QUORUM",
        )

    family_binding = semantic_raw.get("provenance_families")
    if not isinstance(family_binding, Mapping):
        if base.get("synthesis") is None:
            return dict(base)
        return _quarantine_binding(
            base,
            reason="DETERMINISTIC_PROVENANCE_FAMILY_BINDING_REQUIRED_BEFORE_STRICT_FAMILY_QUORUM",
        )

    guard_evidence = family_binding.get("guard_evidence")
    if not isinstance(guard_evidence, list):
        if base.get("synthesis") is None:
            return dict(base)
        return _quarantine_binding(
            base,
            reason="FAMILY_BOUND_GUARD_EVIDENCE_REQUIRED_BEFORE_STRICT_FAMILY_QUORUM",
        )

    quorum = assess_family_quorum(
        guard_evidence,
        min_unipolar_families=minimum,
    )

    if quorum["conflict_present"]:
        return _attach_quorum(base, quorum)

    if base.get("synthesis") is None:
        return _attach_quorum(base, quorum)

    if quorum["state"] == QUORUM_INSUFFICIENT:
        out = dict(base)
        out["quarantined_synthesis"] = out.get("synthesis")
        out["synthesis"] = None
        out["status"] = SEMANTIC_FAMILY_QUORUM_INSUFFICIENT
        semantic = dict(semantic_raw)
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
