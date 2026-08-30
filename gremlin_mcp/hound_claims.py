from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.claim_proposition import scan_proposition_conflicts, verify_proposition
from gremlin_mcp.source_family import derive_source_families

SCHEMA = "GREMLIN_HOUND_CLAIM_AUDIT_V0_1"
VERSION = "0.1.0"


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


def hound_claim_audit(
    propositions: Iterable[Mapping[str, Any]],
    *,
    citations: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Audit exact proposition conflicts against canonical source-family provenance.

    This function identifies candidate logical conflicts. It never resolves which proposition is
    true, never treats source-family separation as proof of independence, and never promotes a
    candidate to canon or execution authority.
    """
    frames = [dict(row) for row in propositions]
    validations = [verify_proposition(row) for row in frames]
    invalid = [
        {"index": index, "errors": validation["errors"]}
        for index, validation in enumerate(validations)
        if not validation["valid"]
    ]
    if invalid:
        core = {
            "status": "INVALID_PROPOSITION_SET_FAIL_CLOSED",
            "invalid": invalid,
            "frame_count": len(frames),
            "cross_family_conflict_candidate_count": 0,
            "intra_family_conflict_candidate_count": 0,
            "conflict_candidates": [],
            "authority": _authority(),
        }
        return {
            "schema": SCHEMA,
            "version": VERSION,
            **core,
            "hound_claim_audit_commitment": _commit(b"GREMLIN-HOUND-CLAIM-AUDIT/v0.1", core),
        }

    family_receipt = derive_source_families(citations)
    families = family_receipt["families_by_source_id"]
    missing_sources = sorted(
        {
            str(frame.get("source_id") or "").strip()
            for frame in frames
            if str(frame.get("source_id") or "").strip() not in families
        }
    )
    if missing_sources:
        core = {
            "status": "PROPOSITION_SOURCE_FAMILY_BINDING_FAILED",
            "missing_source_ids": missing_sources,
            "frame_count": len(frames),
            "family_set_commitment": family_receipt["family_set_commitment"],
            "cross_family_conflict_candidate_count": 0,
            "intra_family_conflict_candidate_count": 0,
            "conflict_candidates": [],
            "authority": _authority(),
        }
        return {
            "schema": SCHEMA,
            "version": VERSION,
            **core,
            "hound_claim_audit_commitment": _commit(b"GREMLIN-HOUND-CLAIM-AUDIT/v0.1", core),
        }

    scan = scan_proposition_conflicts(frames)
    typed_conflicts: list[dict[str, Any]] = []
    cross_family = 0
    intra_family = 0
    for conflict in scan["conflict_candidates"]:
        left_source = conflict["left_source_id"]
        right_source = conflict["right_source_id"]
        left_family = families[left_source]["family_id"]
        right_family = families[right_source]["family_id"]
        same_family = left_family == right_family
        classification = (
            "INTRA_FAMILY_EXACT_FRAME_POLARITY_CONFLICT_CANDIDATE"
            if same_family
            else "CROSS_FAMILY_EXACT_FRAME_POLARITY_CONFLICT_CANDIDATE"
        )
        if same_family:
            intra_family += 1
        else:
            cross_family += 1
        typed_conflicts.append(
            {
                **conflict,
                "left_family_id": left_family,
                "right_family_id": right_family,
                "same_provenance_family": same_family,
                "hound_classification": classification,
                "truth_resolution": "UNRESOLVED",
            }
        )

    if cross_family:
        status = "CROSS_FAMILY_LOGICAL_CONFLICT_CANDIDATES_PRESENT"
    elif intra_family:
        status = "INTRA_FAMILY_VERSION_OR_SOURCE_CONFLICT_CANDIDATES_PRESENT"
    else:
        status = "NO_DIRECT_EXACT_FRAME_CONFLICT_CANDIDATES"

    core = {
        "status": status,
        "frame_count": len(frames),
        "family_set_commitment": family_receipt["family_set_commitment"],
        "proposition_scan_commitment": scan["scan_commitment"],
        "cross_family_conflict_candidate_count": cross_family,
        "intra_family_conflict_candidate_count": intra_family,
        "conflict_candidates": typed_conflicts,
        "family_receipt": family_receipt,
        "truth_resolution": "UNRESOLVED",
        "source_family_independence_status": family_receipt["independence_status"],
        "policy": "EXACT_PROPOSITION_CONFLICT_PLUS_CANONICAL_PROVENANCE_FAMILY_NO_TRUTH_RESOLUTION",
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "hound_claim_audit_commitment": _commit(b"GREMLIN-HOUND-CLAIM-AUDIT/v0.1", core),
    }
