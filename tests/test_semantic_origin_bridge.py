from __future__ import annotations

from gremlin_mcp.evidence_kind import EMPIRICAL, PRIMARY_EXPERIMENT, build_evidence_kind_assignment
from gremlin_mcp.evidence_origin import (
    DATASET,
    EXPERIMENT,
    PRIMARY_GENERATION,
    REANALYSIS,
    build_evidence_origin_assignment,
)
from gremlin_mcp.evidence_robustness import SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment
from gremlin_mcp.semantic_evidence import FixtureAssignment, FixtureSemanticEvidenceProducer, run_producer
from gremlin_mcp.semantic_origin_bridge import (
    SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE,
    SEMANTIC_EVIDENCE_ORIGIN_POLICY_INSUFFICIENT,
    apply_semantic_producer_output_with_origin_lineage,
)


def _receipt(source_id: str, sentence: str) -> dict:
    text = f"Source {source_id}. {sentence}"
    receipt = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _execution():
    receipts = [
        _receipt("src-a", "Direct experiment A supports the claim."),
        _receipt("src-b", "Direct experiment B supports the claim."),
    ]
    citations = [
        {
            "source_id": "src-a",
            "provider": "fixture",
            "title": "Primary work alpha",
            "url": "https://alpha.example.org/a",
            "doi": "10.1000/alpha",
            "published": "2026-08-30",
            "content_basis": receipts[0]["content_basis"],
            "content_commitment": receipts[0]["content_commitment"],
        },
        {
            "source_id": "src-b",
            "provider": "fixture",
            "title": "Primary work beta",
            "url": "https://beta.example.org/b",
            "doi": "10.2000/beta",
            "published": "2026-08-30",
            "content_basis": receipts[1]["content_basis"],
            "content_commitment": receipts[1]["content_commitment"],
        },
    ]
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "version": "0.1.2",
        "query": "test query",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "synthesis": {"state": "DONE", "species": "BELZEBUB", "result": {"answer": "candidate"}},
        "citations": citations,
        "source_receipts": receipts,
        "authority": {"production_runtime_write": False, "execution_admitted": False, "canon_allowed": False},
    }


def _semantic_output(execution, claim_id):
    producer = FixtureSemanticEvidenceProducer(
        [
            FixtureAssignment("src-a", "untrusted-a", "Direct experiment A supports the claim.", SUPPORT, 0.95),
            FixtureAssignment("src-b", "untrusted-b", "Direct experiment B supports the claim.", SUPPORT, 0.95),
        ]
    )
    return run_producer(producer, claim_id=claim_id, source_receipts=execution["source_receipts"])


def _kind_assignments(execution):
    return [
        build_evidence_kind_assignment(
            source_receipt=receipt,
            evidence_kind=PRIMARY_EXPERIMENT,
            producer_id="fixture-kind-producer",
            producer_version="0.1.0",
            mode="FIXTURE_ONLY_EXPLICIT_KIND_ASSIGNMENT",
        )
        for receipt in execution["source_receipts"]
    ]


def _origin(receipt, origin_id, *, kind=EXPERIMENT, usage=PRIMARY_GENERATION):
    return build_evidence_origin_assignment(
        source_receipt=receipt,
        origin_refs=[{"origin_id": origin_id, "origin_kind": kind, "usage": usage}],
        producer_id="fixture-origin-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_ORIGIN_ASSIGNMENT",
    )


def test_two_distinct_papers_reusing_same_dataset_are_quarantined_as_one_origin_lineage():
    execution = _execution()
    result = apply_semantic_producer_output_with_origin_lineage(
        execution,
        producer_output=_semantic_output(execution, "claim-origin-a"),
        evidence_kind_assignments=_kind_assignments(execution),
        evidence_origin_assignments=[
            _origin(execution["source_receipts"][0], "dataset:shared", kind=DATASET, usage=REANALYSIS),
            _origin(execution["source_receipts"][1], "dataset:shared", kind=DATASET, usage=REANALYSIS),
        ],
        claim_mode=EMPIRICAL,
    )
    assert result["status"] == SEMANTIC_EVIDENCE_ORIGIN_POLICY_INSUFFICIENT
    assert result["synthesis"] is None
    assert result["quarantined_synthesis"] is not None
    semantic = result["semantic_evidence"]
    assert semantic["family_quorum"]["quorum_satisfied"] is True
    assert semantic["evidence_kind_policy"]["policy_satisfied"] is True
    assert semantic["evidence_origin_policy"]["origin_lineage_group_count"] == 1


def test_two_distinct_direct_origins_keep_candidate_synthesis():
    execution = _execution()
    result = apply_semantic_producer_output_with_origin_lineage(
        execution,
        producer_output=_semantic_output(execution, "claim-origin-b"),
        evidence_kind_assignments=_kind_assignments(execution),
        evidence_origin_assignments=[
            _origin(execution["source_receipts"][0], "experiment:A"),
            _origin(execution["source_receipts"][1], "experiment:B"),
        ],
        claim_mode=EMPIRICAL,
    )
    assert result["synthesis"] is not None
    policy = result["semantic_evidence"]["evidence_origin_policy"]
    assert policy["origin_lineage_group_count"] == 2
    assert policy["policy_satisfied"] is True
    assert result["authority"]["canon_allowed"] is False


def test_missing_origin_assignment_for_direct_source_quarantines():
    execution = _execution()
    result = apply_semantic_producer_output_with_origin_lineage(
        execution,
        producer_output=_semantic_output(execution, "claim-origin-c"),
        evidence_kind_assignments=_kind_assignments(execution),
        evidence_origin_assignments=[
            _origin(execution["source_receipts"][0], "experiment:A"),
        ],
        claim_mode=EMPIRICAL,
    )
    assert result["status"] == SEMANTIC_EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE
    assert result["synthesis"] is None
    assert result["semantic_evidence"]["evidence_origin_policy"]["missing_origin_source_ids"] == ["src-b"]
