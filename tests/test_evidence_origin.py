from __future__ import annotations

from gremlin_mcp.evidence_kind import EMPIRICAL, PRIMARY_EXPERIMENT
from gremlin_mcp.evidence_origin import (
    DATASET,
    EXPERIMENT,
    ORIGIN_POLICY_INSUFFICIENT,
    ORIGIN_POLICY_SUFFICIENT,
    ORIGIN_UNKNOWN_FAIL_CLOSED,
    PRIMARY_GENERATION,
    REANALYSIS,
    assess_evidence_origin_lineage,
    build_evidence_origin_assignment,
    verify_evidence_origin_assignment,
)
from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT
from gremlin_mcp.research_provenance import source_receipt_commitment


def _receipt(source_id: str) -> dict:
    text = f"Evidence for {source_id}."
    receipt = {
        "source_id": source_id,
        "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        "content_commitment": f"content:{source_id}:v1",
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    receipt["source_receipt_commitment"] = source_receipt_commitment(receipt)
    return receipt


def _kind(source_id: str) -> dict:
    return {"source_id": source_id, "evidence_kind": PRIMARY_EXPERIMENT}


def _guard(source_id: str, family: str, stance: str = SUPPORT) -> dict:
    return {
        "evidence_id": source_id,
        "source_family": family,
        "stance": stance,
        "payload_commitment": f"payload:{source_id}",
    }


def _origin(receipt, origin_id: str | None, *, kind=EXPERIMENT, usage=PRIMARY_GENERATION):
    refs = None if origin_id is None else [{"origin_id": origin_id, "origin_kind": kind, "usage": usage}]
    return build_evidence_origin_assignment(
        source_receipt=receipt,
        origin_refs=refs,
        producer_id="fixture-origin-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_ORIGIN_ASSIGNMENT",
    )


def test_origin_assignment_is_bound_to_exact_content_commitment():
    receipt = _receipt("a")
    assignment = _origin(receipt, "experiment:A")
    assert verify_evidence_origin_assignment(assignment, source_receipts=[receipt])["valid"] is True
    tampered = dict(assignment)
    tampered["content_commitment"] = "tampered"
    validation = verify_evidence_origin_assignment(tampered, source_receipts=[receipt])
    assert validation["valid"] is False
    assert "CONTENT_COMMITMENT_MISMATCH" in validation["errors"]
    assert "ASSIGNMENT_COMMITMENT_MISMATCH" in validation["errors"]


def test_two_direct_sources_reusing_same_dataset_form_one_lineage_group():
    a, b = _receipt("a"), _receipt("b")
    policy = assess_evidence_origin_lineage(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        evidence_kind_assignments=[_kind("a"), _kind("b")],
        origin_assignments=[
            _origin(a, "dataset:shared", kind=DATASET, usage=REANALYSIS),
            _origin(b, "dataset:shared", kind=DATASET, usage=REANALYSIS),
        ],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    assert policy["state"] == ORIGIN_POLICY_INSUFFICIENT
    assert policy["origin_lineage_group_count"] == 1
    assert policy["origin_lineage_groups"][0]["source_ids"] == ["a", "b"]


def test_two_distinct_direct_origins_satisfy_two_group_policy():
    a, b = _receipt("a"), _receipt("b")
    policy = assess_evidence_origin_lineage(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        evidence_kind_assignments=[_kind("a"), _kind("b")],
        origin_assignments=[_origin(a, "experiment:A"), _origin(b, "experiment:B")],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    assert policy["state"] == ORIGIN_POLICY_SUFFICIENT
    assert policy["origin_lineage_group_count"] == 2
    assert policy["policy_satisfied"] is True


def test_multi_origin_bridge_collapses_connected_lineage_components():
    a, b, c = _receipt("a"), _receipt("b"), _receipt("c")
    c_assignment = build_evidence_origin_assignment(
        source_receipt=c,
        origin_refs=[
            {"origin_id": "experiment:X", "origin_kind": EXPERIMENT, "usage": REANALYSIS},
            {"origin_id": "experiment:Y", "origin_kind": EXPERIMENT, "usage": REANALYSIS},
        ],
        producer_id="fixture-origin-producer",
        producer_version="0.1.0",
        mode="FIXTURE_ONLY_EXPLICIT_ORIGIN_ASSIGNMENT",
    )
    policy = assess_evidence_origin_lineage(
        [_guard("a", "fam-a"), _guard("b", "fam-b"), _guard("c", "fam-c")],
        evidence_kind_assignments=[_kind("a"), _kind("b"), _kind("c")],
        origin_assignments=[_origin(a, "experiment:X"), _origin(b, "experiment:Y"), c_assignment],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    assert policy["state"] == ORIGIN_POLICY_INSUFFICIENT
    assert policy["origin_lineage_group_count"] == 1
    assert policy["origin_lineage_groups"][0]["source_ids"] == ["a", "b", "c"]


def test_unknown_origin_never_counts_as_independent_lineage():
    a, b = _receipt("a"), _receipt("b")
    policy = assess_evidence_origin_lineage(
        [_guard("a", "fam-a"), _guard("b", "fam-b")],
        evidence_kind_assignments=[_kind("a"), _kind("b")],
        origin_assignments=[_origin(a, "experiment:A"), _origin(b, None)],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    assert policy["state"] == ORIGIN_UNKNOWN_FAIL_CLOSED
    assert policy["unknown_origin_source_ids"] == ["b"]
    assert policy["policy_satisfied"] is False


def test_stance_conflict_defers_to_hound_before_origin_counting():
    a, b = _receipt("a"), _receipt("b")
    policy = assess_evidence_origin_lineage(
        [_guard("a", "fam-a", SUPPORT), _guard("b", "fam-b", CONTRADICT)],
        evidence_kind_assignments=[_kind("a"), _kind("b")],
        origin_assignments=[_origin(a, "experiment:A"), _origin(b, "experiment:B")],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    assert policy["conflict_present"] is True
    assert policy["policy_satisfied"] is None
    assert "DEFER_TO_HOUND" in policy["state"]
