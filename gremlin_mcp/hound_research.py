from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from gremlin_mcp.hound_provenance import hound_provenance_audit
from gremlin_mcp.research_executor import execute_research

SCHEMA = "GREMLIN_HOUND_RESEARCH_BINDING_V0_1"
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


def attach_hound_provenance(execution: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a committed HOUND provenance receipt without mutating worker result commitments."""
    base = dict(execution)
    citations = list(base.get("citations") or [])
    if not citations:
        audit = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "NO_CITATIONS_FAIL_CLOSED",
            "source_count": 0,
            "family_count": 0,
            "duplicate_or_version_clusters": [],
            "ambiguous_title_bridges": [],
            "authority": _authority(),
        }
        audit["hound_research_binding_commitment"] = _commit(
            b"GREMLIN-HOUND-RESEARCH-BINDING/v0.1", audit
        )
        base["hound_provenance"] = audit
        return base

    provenance = hound_provenance_audit(citations)
    binding_core = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "BOUND_TO_EXECUTION_CITATIONS",
        "execution_commitment": base.get("execution_commitment"),
        "citation_source_ids": sorted(
            str(row.get("source_id") or "").strip()
            for row in citations
            if str(row.get("source_id") or "").strip()
        ),
        "family_set_commitment": provenance["family_set_commitment"],
        "hound_provenance_commitment": provenance["hound_provenance_commitment"],
        "provenance_audit": provenance,
        "worker_result_mutation": False,
        "contradiction_inference_from_family_topology": False,
        "authority": _authority(),
    }
    binding_core["hound_research_binding_commitment"] = _commit(
        b"GREMLIN-HOUND-RESEARCH-BINDING/v0.1", binding_core
    )
    base["hound_provenance"] = binding_core
    base["hound_bound_execution_commitment"] = _commit(
        b"GREMLIN-HOUND-BOUND-EXECUTION/v0.1",
        {key: value for key, value in base.items() if key != "hound_bound_execution_commitment"},
    )
    return base


def execute_research_with_hound_provenance(
    query: str,
    *,
    providers: Sequence[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    execution = execute_research(
        query,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    return attach_hound_provenance(execution)
