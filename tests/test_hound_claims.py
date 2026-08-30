from __future__ import annotations

from gremlin_mcp.claim_proposition import AFFIRM, ASSERTED, NEGATE, build_proposition
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.hound_claims import hound_claim_audit
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import build_classification


def _receipt(source_id: str, excerpt: str) -> dict[str, object]:
    evidence_text = f"Source {source_id}. {excerpt}"
    receipt: dict[str, object] = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(evidence_text),
        "evidence_text": evidence_text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _classification(receipt, excerpt):
    return build_classification(
        claim_id="claim-1",
        source_receipt=receipt,
        source_family="producer-declared-untrusted",
        excerpt=excerpt,
        stance=SUPPORT,
        confidence=0.9,
        producer_id="fixture-producer",
        producer_version="0.1",
        model_id=None,
        mode="FIXTURE_ONLY_NO_SEMANTIC_INFERENCE",
    )


def _frame(source_id: str, excerpt: str, polarity: str):
    receipt = _receipt(source_id, excerpt)
    classification = _classification(receipt, excerpt)
    frame = build_proposition(
        classification=classification,
        claim_id="claim-1",
        source_receipts=[receipt],
        subject="information",
        predicate="DESCRIBES",
        object="geometry",
        polarity=polarity,
        modality=ASSERTED,
        extraction_mode="FIXTURE_EXPLICIT_TYPED_SPO",
    )
    return receipt, frame


def _citation(source_id, *, title, url, doi=None):
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": title,
        "url": url,
        "doi": doi,
        "published": "2026-08-30",
    }


def test_same_arxiv_work_versions_are_intra_family_conflict_not_independent_conflict():
    _, a = _frame("v1", "Information describes geometry.", AFFIRM)
    _, b = _frame("v2", "Information does not describe geometry.", NEGATE)
    title = "Information Geometry and Entropy Relations in Quantum Gravity"
    citations = [
        _citation("v1", title=title, url="https://arxiv.org/abs/2608.54321v1"),
        _citation("v2", title=title, url="https://arxiv.org/abs/2608.54321v2"),
    ]
    audit = hound_claim_audit([a, b], citations=citations)
    assert audit["status"] == "INTRA_FAMILY_VERSION_OR_SOURCE_CONFLICT_CANDIDATES_PRESENT"
    assert audit["cross_family_conflict_candidate_count"] == 0
    assert audit["intra_family_conflict_candidate_count"] == 1
    conflict = audit["conflict_candidates"][0]
    assert conflict["same_provenance_family"] is True
    assert conflict["truth_resolution"] == "UNRESOLVED"


def test_distinct_doi_families_produce_cross_family_conflict_candidate_without_truth_resolution():
    _, a = _frame("doi-a", "Information describes geometry.", AFFIRM)
    _, b = _frame("doi-b", "Information does not describe geometry.", NEGATE)
    citations = [
        _citation("doi-a", title="Work A On Information Geometry", url="https://doi.org/10.1000/a", doi="10.1000/a"),
        _citation("doi-b", title="Work B On Information Geometry", url="https://doi.org/10.1000/b", doi="10.1000/b"),
    ]
    audit = hound_claim_audit([a, b], citations=citations)
    assert audit["status"] == "CROSS_FAMILY_LOGICAL_CONFLICT_CANDIDATES_PRESENT"
    assert audit["cross_family_conflict_candidate_count"] == 1
    assert audit["intra_family_conflict_candidate_count"] == 0
    conflict = audit["conflict_candidates"][0]
    assert conflict["same_provenance_family"] is False
    assert conflict["hound_classification"] == "CROSS_FAMILY_EXACT_FRAME_POLARITY_CONFLICT_CANDIDATE"
    assert audit["truth_resolution"] == "UNRESOLVED"
    assert audit["authority"]["canon_allowed"] is False


def test_missing_proposition_source_in_citations_fails_closed():
    _, a = _frame("src-a", "Information describes geometry.", AFFIRM)
    audit = hound_claim_audit(
        [a],
        citations=[_citation("other", title="Other Source With Enough Title", url="https://example.org/other")],
    )
    assert audit["status"] == "PROPOSITION_SOURCE_FAMILY_BINDING_FAILED"
    assert audit["missing_source_ids"] == ["src-a"]
    assert audit["conflict_candidates"] == []


def test_tampered_proposition_set_fails_closed_before_family_conflict_logic():
    _, a = _frame("src-a", "Information describes geometry.", AFFIRM)
    a["polarity"] = NEGATE
    citations = [_citation("src-a", title="A Source About Information Geometry", url="https://example.org/a")]
    audit = hound_claim_audit([a], citations=citations)
    assert audit["status"] == "INVALID_PROPOSITION_SET_FAIL_CLOSED"
    assert audit["cross_family_conflict_candidate_count"] == 0
    assert audit["conflict_candidates"] == []
