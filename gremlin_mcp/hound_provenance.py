from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.source_family import derive_source_families

SCHEMA = "GREMLIN_HOUND_PROVENANCE_AUDIT_V0_1"
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


def hound_provenance_audit(citations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return HOUND's duplicate/version topology using the canonical source-family derivation.

    This audit deliberately reuses `derive_source_families`; HOUND does not maintain a second
    title-only duplicate detector. Family membership is conservative provenance clustering and is
    not proof of editorial, causal, or experimental independence.
    """
    rows = [dict(row) for row in citations]
    family_receipt = derive_source_families(rows)

    duplicate_or_version_clusters = [
        {
            "family_id": family_id,
            "source_ids": list(source_ids),
            "family_identity": family_receipt["family_identities"].get(family_id),
            "classification": "SAME_WORK_OR_VERSION_PROVENANCE_CLUSTER_NOT_ASSUMED_CONTRADICTION",
        }
        for family_id, source_ids in family_receipt["clusters"].items()
        if len(source_ids) > 1
    ]

    core = {
        "family_set_commitment": family_receipt["family_set_commitment"],
        "source_count": family_receipt["source_count"],
        "family_count": family_receipt["family_count"],
        "collapsed_duplicate_or_version_count": family_receipt["collapsed_duplicate_or_version_count"],
        "duplicate_or_version_clusters": duplicate_or_version_clusters,
        "ambiguous_title_bridges": list(family_receipt.get("ambiguous_title_bridges") or []),
        "merge_receipts": list(family_receipt.get("merge_receipts") or []),
        "independence_status": family_receipt["independence_status"],
        "policy": "HOUND_USES_CANONICAL_SOURCE_FAMILY_TOPOLOGY",
        "contradiction_inference_from_family_topology": False,
        "authority": _authority(),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "hound_provenance_commitment": _commit(b"GREMLIN-HOUND-PROVENANCE/v0.1", core),
    }
