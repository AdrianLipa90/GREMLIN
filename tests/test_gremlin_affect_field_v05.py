import copy
import hashlib

import pytest

from tools.gremlin_affect_field_v05 import (
    AffectFieldError,
    build_kaku_affect_binding_v05,
    build_rifc_affect_field_receipt_v05,
    validate_kaku_affect_binding_v05,
    validate_rifc_affect_field_receipt_v05,
)
from tools.gremlin_scalar_source_delta_v05 import (
    build_scalar_source_delta_v05,
    validate_scalar_source_delta_v05,
)
from tools.gremlin_scalar_source_registry_v03 import build_scalar_source_registry_v03


def estimate(**overrides):
    payload = {
        "affect": {
            "valence": 0.62,
            "arousal": 0.31,
            "urgency": 0.14,
            "threat_relevance": 0.02,
            "attachment_relevance": 0.08,
            "reward_relevance": 0.71,
        },
        "confidence": 0.73,
        "surface_labels": ["preference-reward-salient", "positive-activated"],
        "evidence": [
            {
                "cue": "lubię",
                "start": 7,
                "end": 12,
                "contributions": {"valence": 0.7, "reward": 0.9},
                "kind": "lexical",
            },
            {
                "cue": "!",
                "start": 0,
                "end": 0,
                "contributions": {"arousal": 0.12, "urgency": 0.05},
                "kind": "punctuation",
            },
        ],
        "text_sha256": hashlib.sha256("Bardzo lubię ten kierunek!".encode()).hexdigest(),
        "method": "transparent_lexical_surface_v1",
        "truth_authority": False,
        "semantic_authority": False,
        "diagnostic_authority": False,
        "modulation_authority": False,
    }
    payload.update(overrides)
    return payload


def test_full_rifc_affect_field_is_receipted_without_phase36():
    receipt = build_rifc_affect_field_receipt_v05(estimate())
    assert validate_rifc_affect_field_receipt_v05(receipt)
    assert set(receipt["affect_field"]) == {
        "valence",
        "arousal",
        "urgency",
        "threat_relevance",
        "attachment_relevance",
        "reward_relevance",
    }
    assert receipt["phase36_embedding_present"] is False
    assert receipt["collapsed_affect_scalar_present"] is False
    assert receipt["truth_authority"] is False
    assert receipt["execution_admitted"] is False
    assert receipt["canon_allowed"] is False


def test_raw_text_and_raw_cues_are_removed_from_persistent_receipt():
    upstream = estimate()
    receipt = build_rifc_affect_field_receipt_v05(upstream)
    assert receipt["privacy"] == {
        "raw_text_persisted": False,
        "raw_cues_persisted": False,
        "cue_hashes_persisted": True,
    }
    serialized = repr(receipt)
    assert "Bardzo lubię ten kierunek!" not in serialized
    assert "lubię" not in serialized
    assert receipt["evidence"][0]["cue_sha256"] == hashlib.sha256("lubię".encode()).hexdigest()


def test_upstream_authority_escalation_is_rejected():
    for key in ("truth_authority", "semantic_authority", "diagnostic_authority", "modulation_authority"):
        payload = estimate()
        payload[key] = True
        with pytest.raises(AffectFieldError, match="authority boundary violated"):
            build_rifc_affect_field_receipt_v05(payload)


def test_low_evidence_stays_explicit_unknown():
    payload = estimate(
        affect={
            "valence": 0.0,
            "arousal": 0.0,
            "urgency": 0.0,
            "threat_relevance": 0.0,
            "attachment_relevance": 0.0,
            "reward_relevance": 0.0,
        },
        confidence=0.0,
        surface_labels=["insufficient-evidence"],
        evidence=[],
    )
    receipt = build_rifc_affect_field_receipt_v05(payload)
    assert validate_rifc_affect_field_receipt_v05(receipt)
    assert receipt["surface_labels"] == ["insufficient-evidence"]
    assert float.fromhex(receipt["inference_confidence"]["value_f64_hex"]) == 0.0


def test_low_confidence_cannot_be_relabelled_as_positive_affect_evidence():
    payload = estimate(confidence=0.1, surface_labels=["positive-valence"])
    with pytest.raises(AffectFieldError, match="insufficient-evidence"):
        build_rifc_affect_field_receipt_v05(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("valence", -1.1),
        ("valence", 1.1),
        ("arousal", -0.01),
        ("urgency", 1.01),
        ("threat_relevance", -0.1),
        ("attachment_relevance", 1.1),
        ("reward_relevance", 1.1),
    ],
)
def test_affect_field_domains_fail_closed(field, value):
    payload = estimate()
    payload["affect"][field] = value
    with pytest.raises(AffectFieldError, match="outside"):
        build_rifc_affect_field_receipt_v05(payload)


def test_ciel_vad_is_preserved_as_compatibility_subset_only():
    receipt = build_rifc_affect_field_receipt_v05(estimate())
    compat = receipt["compatibility"]
    assert compat["ciel_vad_v0_4_overlap"] == ["valence", "arousal"]
    assert compat["ciel_vad_v0_4_dominance_semantic_mapping"] == "UNRESOLVED"
    assert compat["ciel_vad_v0_4_confidence_role"] == "INFERENCE_CONFIDENCE_COMPATIBILITY_ONLY"


def test_producer_pin_is_exact_and_tamper_fails():
    receipt = build_rifc_affect_field_receipt_v05(estimate())
    tampered = copy.deepcopy(receipt)
    tampered["producer"]["commit"] = "0" * 40
    with pytest.raises(AffectFieldError, match="producer pin mismatch"):
        validate_rifc_affect_field_receipt_v05(tampered)


def test_kaku_affect_binding_keeps_scalar_envelope_open():
    receipt = build_rifc_affect_field_receipt_v05(estimate())
    binding = build_kaku_affect_binding_v05(kaku_id="kaku-001", affect_receipt=receipt)
    assert validate_kaku_affect_binding_v05(binding)
    assert binding["scalar_envelope_complete"] is False
    assert binding["remaining_kaku_scalar_families"] == [
        "valuation",
        "intention_alignment",
        "epistemic_support",
    ]
    assert binding["radical_admission_required"] is True
    assert binding["vector_synthesis_allowed"] is False
    assert binding["vector_bound"] is False


def test_source_delta_closes_affect_candidate_only_and_leaves_other_frontiers_open():
    base = build_scalar_source_registry_v03()
    delta = build_scalar_source_delta_v05(base)
    assert validate_scalar_source_delta_v05(delta, base)
    assert delta["updates"]["affect"]["readiness"] == "DETERMINISTIC_INPUT_CONDITIONED_PRODUCER_CANDIDATE"
    assert delta["readiness"]["affect_source_closed_for_candidate_inference"] is True
    assert delta["updates"]["valuation"]["producer_status"] == "UNRESOLVED"
    assert delta["updates"]["epistemic_support"]["producer_status"] == "UNRESOLVED"
    assert delta["readiness"]["kaku_pre_vector_complete"] is False
    assert delta["readiness"]["vector_synthesis_globally_ready"] is False


def test_affect_confidence_cannot_be_promoted_to_epistemic_support_by_policy():
    delta = build_scalar_source_delta_v05(build_scalar_source_registry_v03())
    assert delta["rules"]["affect_confidence_is_epistemic_support"] is False
    assert delta["rules"]["phase_similarity_promotes_epistemic_status"] is False
