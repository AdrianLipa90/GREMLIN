import copy

import pytest

from tools.gremlin_epistemic_bundle_v06 import (
    EpistemicBundleError,
    build_belzebub_survival_evidence_v06,
    build_confidence_declaration_v06,
    build_epistemic_support_bundle_v06,
    build_evidence_item_v06,
    build_kaku_epistemic_binding_v06,
    validate_confidence_declaration_v06,
    validate_epistemic_support_bundle_v06,
    validate_evidence_item_v06,
    validate_kaku_epistemic_binding_v06,
)
from tools.gremlin_phasenav_compiler_v01 import CANDIDATE_SCHEMA


def candidate():
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-epi-001",
        "status": "SURVIVED_AUDIT",
        "audit": {
            "belzebub_result": "SURVIVED",
            "attempted_falsifiers": ["gcd-normalization", "single-character-collapse"],
        },
        "relations": [
            {"kind": "phase_lock", "a": 0, "b": 1, "gain": 1.0, "source_ref": "rel:lock"}
        ],
    }


def evidence(eid="ev-1"):
    return build_evidence_item_v06(
        evidence_id=eid,
        source_ref=f"receipt://{eid}",
        source_commitment="11" * 32,
        evidence_role="REFERENCE_CONFORMANCE",
        relation_to_claim="BEARS_ON",
        epistemic_status="OBSERVED_TEST_RESULT",
        framework_ref="framework://reference-conformance-v1",
    )


def confidence():
    return build_confidence_declaration_v06(
        value=0.82,
        confidence_kind="RELIABILITY",
        estimator_ref="estimator://declared-reliability-v1",
        source_ref="receipt://confidence-001",
        source_family="EVIDENCE_RELIABILITY",
        epistemic_status="DECLARED_CANDIDATE",
    )


def bundle(**overrides):
    data = dict(
        claim_id="claim-001",
        claim_commitment="22" * 32,
        proposition_commitment="33" * 32,
        inference_framework_commitment="44" * 32,
        evidence_items=[evidence()],
        confidence=confidence(),
    )
    data.update(overrides)
    return build_epistemic_support_bundle_v06(**data)


def test_evidence_item_has_no_numeric_weight_or_support_scalar():
    item = evidence()
    assert validate_evidence_item_v06(item)
    assert item["numeric_weight_present"] is False
    assert item["epistemic_support_scalar_present"] is False
    assert item["vector_bound"] is False
    assert item["execution_admitted"] is False


def test_belzebub_survival_becomes_falsification_evidence_without_score():
    item = build_belzebub_survival_evidence_v06(
        candidate(), framework_ref="framework://belzebub-v0.6"
    )
    assert validate_evidence_item_v06(item)
    assert item["evidence_role"] == "FALSIFICATION_SURVIVAL"
    assert item["relation_to_claim"] == "BEARS_ON"
    assert item["epistemic_status"] == "SURVIVED_AUDIT"
    assert item["numeric_weight_present"] is False
    assert item["epistemic_support_scalar_present"] is False


def test_rejected_belzebub_candidate_cannot_be_bound_as_survival_evidence():
    c = candidate()
    c["status"] = "REJECTED"
    c["audit"]["belzebub_result"] = "REJECTED"
    with pytest.raises(EpistemicBundleError, match="SURVIVED_AUDIT"):
        build_belzebub_survival_evidence_v06(c, framework_ref="framework://belzebub")


def test_confidence_is_separate_antecedent_and_not_epistemic_support():
    record = confidence()
    assert validate_confidence_declaration_v06(record)
    assert record["semantic_term_id"] == "CLX2-SEM-023"
    assert record["epistemic_support_scalar_present"] is False
    assert record["vector_bound"] is False


def test_affect_inference_confidence_cannot_enter_epistemic_confidence_lane():
    with pytest.raises(EpistemicBundleError, match="separate semantic lane"):
        build_confidence_declaration_v06(
            value=0.9,
            confidence_kind="RELIABILITY",
            estimator_ref="affect://detector-confidence",
            source_ref="affect://receipt/001",
            source_family="AFFECT_INFERENCE",
            epistemic_status="AFFECT_INFERENCE_CONFIDENCE",
        )


def test_bundle_binds_claim_proposition_evidence_framework_and_confidence():
    record = bundle()
    assert validate_epistemic_support_bundle_v06(record)
    assert record["claim"]["semantic_term_id"] == "CLX2-SEM-020"
    assert record["proposition"]["semantic_term_id"] == "CLX2-SEM-021"
    assert record["confidence"]["semantic_term_id"] == "CLX2-SEM-023"
    assert len(record["evidence"]) == 1
    assert record["dictionary_promotion_gate"]["function"] == "promotion_requires_evidence"
    assert record["scalarization"] == {
        "status": "UNRESOLVED",
        "epistemic_support_scalar_present": False,
        "numeric_evidence_weights_present": False,
    }
    assert record["phase_similarity_promoted"] is False
    assert record["affect_confidence_promoted"] is False
    assert record["vector_bound"] is False


def test_bundle_can_preserve_unresolved_confidence_explicitly():
    record = bundle(confidence=None)
    assert validate_epistemic_support_bundle_v06(record)
    assert record["confidence"] == {
        "status": "UNRESOLVED",
        "semantic_term_id": "CLX2-SEM-023",
    }
    assert record["scalarization"]["status"] == "UNRESOLVED"


def test_evidence_lineage_is_canonical_ordered():
    record = bundle(evidence_items=[evidence("z"), evidence("a"), evidence("m")])
    assert [x["evidence_id"] for x in record["evidence"]] == ["a", "m", "z"]
    assert validate_epistemic_support_bundle_v06(record)


def test_duplicate_evidence_ids_fail_closed():
    with pytest.raises(EpistemicBundleError, match="duplicate evidence_id"):
        bundle(evidence_items=[evidence("same"), evidence("same")])


def test_empty_evidence_fails_closed():
    with pytest.raises(EpistemicBundleError, match="at least one evidence item"):
        bundle(evidence_items=[])


def test_scalarization_promotion_tamper_is_rejected():
    record = bundle()
    tampered = copy.deepcopy(record)
    tampered["scalarization"] = {
        "status": "COMPLETE",
        "epistemic_support_scalar_present": True,
        "numeric_evidence_weights_present": True,
    }
    with pytest.raises(EpistemicBundleError, match="scalarization frontier mismatch"):
        validate_epistemic_support_bundle_v06(tampered)


def test_dictionary_promotion_gate_pin_is_fail_closed():
    record = bundle()
    record["dictionary_promotion_gate"]["blob_sha"] = "00" * 20
    with pytest.raises(EpistemicBundleError, match="promotion gate pin mismatch"):
        validate_epistemic_support_bundle_v06(record)


def test_kaku_epistemic_binding_keeps_vector_gate_closed():
    binding = build_kaku_epistemic_binding_v06(kaku_id="kaku-epi-001", bundle=bundle())
    assert validate_kaku_epistemic_binding_v06(binding)
    assert binding["antecedents_bound"] is True
    assert binding["epistemic_support_scalar_present"] is False
    assert binding["scalarization_status"] == "UNRESOLVED"
    assert binding["vector_synthesis_allowed"] is False
    assert binding["vector_bound"] is False
    assert binding["execution_admitted"] is False
    assert binding["canon_allowed"] is False
