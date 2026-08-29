from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.evidence_robustness import (
    CONTRADICTION_DETECTED_UNRESOLVED,
    build_evidence_bundle,
    assess_evidence_bundle,
)
from gremlin_mcp.research_executor import execute_research

SCHEMA = "GREMLIN_GUARDED_RESEARCH_V0_1"
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


def apply_claim_evidence_guard(
    execution: Mapping[str, Any],
    *,
    claim_id: str,
    claim_evidence: Iterable[Mapping[str, Any]],
    hound_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind typed claim evidence to one research execution and quarantine synthesis on conflict.

    `claim_evidence` is caller- or pipeline-supplied untrusted evidence. This function does not
    infer semantic SUPPORT/CONTRADICT labels from metadata and does not promote evidence to truth.
    """
    bundle = build_evidence_bundle(claim_id=claim_id, evidence=claim_evidence)
    assessment = assess_evidence_bundle(bundle, hound_receipt=hound_receipt)

    base = dict(execution)
    original_synthesis = base.get("synthesis")
    unresolved = assessment["state"] == CONTRADICTION_DETECTED_UNRESOLVED

    if unresolved:
        base["quarantined_synthesis"] = original_synthesis
        base["synthesis"] = None
        base["status"] = CONTRADICTION_DETECTED_UNRESOLVED
        synthesis_authorized = False
        quarantine_reason = "TYPED_CLAIM_EVIDENCE_CONFLICT_REQUIRES_BOUND_HOUND_RECEIPT"
    else:
        base["quarantined_synthesis"] = None
        synthesis_authorized = original_synthesis is not None
        quarantine_reason = None

    guard = {
        "schema": SCHEMA,
        "version": VERSION,
        "claim_id": str(claim_id),
        "evidence_bundle": bundle,
        "assessment": assessment,
        "synthesis_authorized": synthesis_authorized,
        "quarantine_reason": quarantine_reason,
        "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
        "semantic_stance_origin": "EXPLICIT_TYPED_INPUT_NOT_INFERRED_FROM_RETRIEVAL_METADATA",
        "authority": _authority(),
    }
    guard["guard_commitment"] = _commit(b"GREMLIN-GUARDED-RESEARCH/v0.1", guard)
    base["claim_evidence_guard"] = guard
    base["authority"] = _authority()
    base["guarded_execution_commitment"] = _commit(
        b"GREMLIN-GUARDED-EXECUTION/v0.1",
        {key: value for key, value in base.items() if key != "guarded_execution_commitment"},
    )
    return base


def execute_guarded_research(
    query: str,
    *,
    claim_id: str | None = None,
    claim_evidence: Iterable[Mapping[str, Any]] | None = None,
    hound_receipt: Mapping[str, Any] | None = None,
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    """Execute live research, then enforce the typed claim-evidence contradiction gate.

    When no typed claim evidence is supplied, the ordinary reference executor result is retained
    and explicitly marked as metadata-only with no completed semantic contradiction test.
    """
    result = execute_research(
        query,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )

    rows = list(claim_evidence or [])
    if not rows:
        base = dict(result)
        guard = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "NO_TYPED_CLAIM_EVIDENCE",
            "semantic_contradiction_test_completed": False,
            "synthesis_authorized": base.get("synthesis") is not None,
            "source_content_authority": "UNTRUSTED_EVIDENCE_ONLY",
            "reason": "RETRIEVAL_METADATA_IS_NOT_AUTOMATICALLY_CLASSIFIED_AS_SUPPORT_OR_CONTRADICTION",
            "authority": _authority(),
        }
        guard["guard_commitment"] = _commit(b"GREMLIN-GUARDED-RESEARCH/v0.1", guard)
        base["claim_evidence_guard"] = guard
        base["guarded_execution_commitment"] = _commit(
            b"GREMLIN-GUARDED-EXECUTION/v0.1",
            {key: value for key, value in base.items() if key != "guarded_execution_commitment"},
        )
        return base

    resolved_claim_id = str(claim_id or f"query:{query}").strip()
    if not resolved_claim_id:
        raise ValueError("claim_id must be non-empty when claim_evidence is supplied")
    return apply_claim_evidence_guard(
        result,
        claim_id=resolved_claim_id,
        claim_evidence=rows,
        hound_receipt=hound_receipt,
    )
