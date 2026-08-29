import gremlin_mcp.guarded_research as guarded
from gremlin_mcp.evidence_robustness import (
    CONTRADICT,
    CONTRADICTION_DETECTED_UNRESOLVED,
    RECONCILED_CANDIDATE,
    SUPPORT,
    build_evidence_bundle,
    build_hound_receipt,
    excerpt_commitment,
)


def _text(source_id: str) -> str:
    return f"Fixture source {source_id} This exact passage belongs to source {source_id}."


def _content(source_id: str) -> str:
    return f"content:{source_id}:v1"


def _citation(source_id: str):
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": f"Fixture source {source_id}",
        "url": f"https://example.org/{source_id}",
        "doi": None,
        "published": "2026-08-30",
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": _content(source_id),
    }


def _source_receipt(source_id: str):
    return {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": _content(source_id),
        "content_length_chars": len(_text(source_id)),
        "evidence_text": _text(source_id),
        "source_receipt_commitment": f"receipt:{source_id}",
    }


def _base_execution():
    ids = ["a", "b", "noise"]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"candidate": {"species": "BELZEBUB", "answer": "candidate"}},
        "citations": [_citation(sid) for sid in ids],
        "source_receipts": [_source_receipt(sid) for sid in ids],
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _evidence(eid, family, stance, credibility):
    excerpt = f"This exact passage belongs to source {eid}."
    excerpt_hash = excerpt_commitment(excerpt)
    return {
        "evidence_id": eid,
        "source_family": family,
        "stance": stance,
        "content_commitment": _content(eid),
        "excerpt": excerpt,
        "excerpt_commitment": excerpt_hash,
        "payload_commitment": excerpt_hash,
        "credibility": credibility,
    }


def _conflict():
    return [
        _evidence("a", "family-a", SUPPORT, 0.74),
        _evidence("b", "family-b", SUPPORT, 0.78),
        _evidence("noise", "authority-looking", CONTRADICT, 0.99),
    ]


def test_conflict_quarantines_existing_belzebub_synthesis():
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-x", claim_evidence=_conflict())
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    guard = result["claim_evidence_guard"]
    assert guard["synthesis_authorized"] is False
    assert guard["assessment"]["candidate_stance"] is None
    assert guard["source_binding"]["valid"] is True
    assert guard["content_binding"]["valid"] is True


def test_valid_exact_bundle_hound_receipt_releases_only_reconciled_candidate():
    rows = _conflict()
    bundle = build_evidence_bundle(claim_id="claim-y", evidence=rows)
    receipt = build_hound_receipt(
        evidence_bundle_commitment=bundle["evidence_bundle_commitment"],
        verdict=SUPPORT,
        rationale_codes=["CONFLICT_AUDITED", "INDEPENDENT_SUPPORT_CHAINS"],
    )
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-y", claim_evidence=rows, hound_receipt=receipt)
    assert result["synthesis"] is not None
    assert result["quarantined_synthesis"] is None
    guard = result["claim_evidence_guard"]
    assert guard["assessment"]["state"] == RECONCILED_CANDIDATE
    assert guard["synthesis_authorized"] is True
    assert guard["content_binding"]["valid"] is True
    assert result["authority"]["canon_allowed"] is False


def test_wrong_bundle_receipt_does_not_release_quarantine():
    rows = _conflict()
    other = build_evidence_bundle(claim_id="other", evidence=[_evidence("other-a", "other-family", SUPPORT, 0.7)])
    receipt = build_hound_receipt(evidence_bundle_commitment=other["evidence_bundle_commitment"], verdict=CONTRADICT, rationale_codes=["WRONG_BUNDLE"])
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-z", claim_evidence=rows, hound_receipt=receipt)
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert "BUNDLE_COMMITMENT_MISMATCH" in result["claim_evidence_guard"]["assessment"]["hound_receipt_errors"]


def test_unknown_evidence_source_id_quarantines_before_content_or_semantic_assessment():
    rows = _conflict() + [_evidence("not-in-execution", "foreign", SUPPORT, 0.8)]
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-source-binding", claim_evidence=rows)
    guard = result["claim_evidence_guard"]
    assert result["status"] == guarded.SOURCE_BINDING_FAILED
    assert result["synthesis"] is None
    assert guard["assessment"] is None
    assert guard["content_binding"] is None
    assert guard["source_binding"]["unknown_evidence_source_ids"] == ["not-in-execution"]


def test_wrong_content_commitment_quarantines_before_semantic_assessment():
    rows = _conflict()
    rows[0]["content_commitment"] = "wrong-content"
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-content", claim_evidence=rows)
    guard = result["claim_evidence_guard"]
    assert result["status"] == guarded.CONTENT_BINDING_FAILED
    assert guard["assessment"] is None
    assert guard["content_binding"]["valid"] is False
    assert {e["code"] for e in guard["content_binding"]["errors"]} >= {"CONTENT_COMMITMENT_MISMATCH"}


def test_excerpt_outside_exact_execution_content_is_rejected():
    rows = _conflict()
    forged = "A fabricated passage that is absent from the execution source."
    rows[1]["excerpt"] = forged
    rows[1]["excerpt_commitment"] = excerpt_commitment(forged)
    rows[1]["payload_commitment"] = rows[1]["excerpt_commitment"]
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-excerpt", claim_evidence=rows)
    assert result["status"] == guarded.CONTENT_BINDING_FAILED
    codes = {e["code"] for e in result["claim_evidence_guard"]["content_binding"]["errors"]}
    assert "EXCERPT_NOT_IN_EXECUTION_CONTENT" in codes


def test_excerpt_tamper_after_commitment_is_rejected():
    rows = _conflict()
    rows[2]["excerpt"] = rows[2]["excerpt"] + " tampered"
    result = guarded.apply_claim_evidence_guard(_base_execution(), claim_id="claim-tamper", claim_evidence=rows)
    assert result["status"] == guarded.CONTENT_BINDING_FAILED
    codes = {e["code"] for e in result["claim_evidence_guard"]["content_binding"]["errors"]}
    assert "EXCERPT_COMMITMENT_MISMATCH" in codes
    assert "PAYLOAD_NOT_BOUND_TO_EXCERPT" in codes


def test_no_typed_evidence_does_not_invent_semantic_stances(monkeypatch):
    monkeypatch.setattr(guarded, "execute_research", lambda *args, **kwargs: _base_execution())
    result = guarded.execute_guarded_research("test query", claim_evidence=None)
    guard = result["claim_evidence_guard"]
    assert guard["status"] == "NO_TYPED_CLAIM_EVIDENCE"
    assert guard["semantic_contradiction_test_completed"] is False
    assert guard["source_binding"]["citation_count"] == 3
    assert guard["content_binding"]["completed"] is False
    assert "NOT_AUTOMATICALLY_CLASSIFIED" in guard["reason"]


def test_live_wrapper_quarantines_conflicting_typed_evidence_without_network(monkeypatch):
    monkeypatch.setattr(guarded, "execute_research", lambda *args, **kwargs: _base_execution())
    result = guarded.execute_guarded_research("test query", claim_id="claim-live-wrapper", claim_evidence=_conflict())
    assert result["status"] == CONTRADICTION_DETECTED_UNRESOLVED
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    assert result["claim_evidence_guard"]["content_binding"]["valid"] is True
