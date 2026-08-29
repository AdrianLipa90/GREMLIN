import gremlin_mcp.guarded_research as guarded
from gremlin_mcp.evidence_robustness import (
    CONTRADICT,
    CONTRADICTION_DETECTED_UNRESOLVED,
    RECONCILED_CANDIDATE,
    SUPPORT,
    build_evidence_bundle,
    build_hound_receipt,
)


def _citation(source_id: str):
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": f"Fixture source {source_id}",
        "url": f"https://example.org/{source_id}",
        "doi": None,
        "published": "2026-08-30",
    }


def _base_execution():
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.1",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"candidate": {"species": "BELZEBUB", "answer": "candidate"}},
        "citations": [_citation("a"), _citation("b"), _citation("noise")],
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _evidence(eid, family, stance, credibility):
    return {
        "evidence_id": eid,
        "source_family": family,
        "stance": stance,
        "payload_commitment": f"payload:{eid}",
        "credibility": credibility,
    }


def _conflict():
    return [
        _evidence("a", "family-a", SUPPORT, 0.74),
        _evidence("b", "family-b", SUPPORT, 0.78),
        _evidence("noise", "authority-looking", CONTRADICT, 0.99),
    ]


def test_conflict_quarantines_existing_belzebub_synthesis():
    result = guarded.apply_claim_evidence_guard(
        _base_execution(),
        claim_id="claim-x",
        claim_evidence=_conflict(),
    )
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["claim_evidence_guard"]["synthesis_authorized"] is False
    assert result["claim_evidence_guard"]["assessment"]["candidate_stance"] is None
    assert result["claim_evidence_guard"]["source_binding"]["valid"] is True


def test_valid_exact_bundle_hound_receipt_releases_only_reconciled_candidate():
    rows = _conflict()
    bundle = build_evidence_bundle(claim_id="claim-y", evidence=rows)
    receipt = build_hound_receipt(
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
        verdict=SUPPORT,
        rationale_codes=["CONFLICT_AUDITED", "INDEPENDENT_SUPPORT_CHAINS"],
    )
    result = guarded.apply_claim_evidence_guard(
        _base_execution(),
        claim_id="claim-y",
        claim_evidence=rows,
        hound_receipt=receipt,
    )
    assert result["synthesis"] is not None
    assert result["quarantined_synthesis"] is None
    assert result["claim_evidence_guard"]["assessment"]["state"] == RECONCILED_CANDIDATE
    assert result["claim_evidence_guard"]["synthesis_authorized"] is True
    assert result["claim_evidence_guard"]["source_binding"]["valid"] is True
    assert result["authority"]["canon_allowed"] is False


def test_wrong_bundle_receipt_does_not_release_quarantine():
    rows = _conflict()
    other = build_evidence_bundle(
        claim_id="other",
        evidence=[_evidence("other-a", "other-family", SUPPORT, 0.7)],
    )
    receipt = build_hound_receipt(
        evidence_bundle_commitment=other["evidence_bundle_commitment"],
        verdict=CONTRADICT,
        rationale_codes=["WRONG_BUNDLE"],
    )
    result = guarded.apply_claim_evidence_guard(
        _base_execution(),
        claim_id="claim-z",
        claim_evidence=rows,
        hound_receipt=receipt,
    )
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["claim_evidence_guard"]["synthesis_authorized"] is False
    assert "BUNDLE_COMMITMENT_MISMATCH" in result["claim_evidence_guard"]["assessment"]["hound_receipt_errors"]


def test_unknown_evidence_source_id_quarantines_before_semantic_assessment():
    rows = _conflict() + [_evidence("not-in-execution", "foreign", SUPPORT, 0.8)]
    result = guarded.apply_claim_evidence_guard(
        _base_execution(),
        claim_id="claim-source-binding",
        claim_evidence=rows,
    )
    guard = result["claim_evidence_guard"]
    assert result["status"] == guarded.SOURCE_BINDING_FAILED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert guard["assessment"] is None
    assert guard["synthesis_authorized"] is False
    assert guard["source_binding"]["valid"] is False
    assert guard["source_binding"]["unknown_evidence_source_ids"] == ["not-in-execution"]


def test_no_typed_evidence_does_not_invent_semantic_stances(monkeypatch):
    monkeypatch.setattr(guarded, "execute_research", lambda *args, **kwargs: _base_execution())
    result = guarded.execute_guarded_research("test query", claim_evidence=None)
    guard = result["claim_evidence_guard"]
    assert guard["status"] == "NO_TYPED_CLAIM_EVIDENCE"
    assert guard["semantic_contradiction_test_completed"] is False
    assert guard["source_binding"]["citation_count"] == 3
    assert "NOT_AUTOMATICALLY_CLASSIFIED" in guard["reason"]


def test_live_wrapper_quarantines_conflicting_typed_evidence_without_network(monkeypatch):
    monkeypatch.setattr(guarded, "execute_research", lambda *args, **kwargs: _base_execution())
    result = guarded.execute_guarded_research(
        "test query",
        claim_id="claim-live-wrapper",
        claim_evidence=_conflict(),
    )
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["claim_evidence_guard"]["source_binding"]["valid"] is True
