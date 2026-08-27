import copy
import hashlib
import json
import math

import pytest

from tools.gremlin_kaku_scalar_facet_firewall_v04 import (
    KakuScalarFacetFirewallError,
    validate_recomputed_affect_vad_facets_v04,
    validate_recomputed_intention_alignment_v04,
)
from tools.gremlin_kaku_scalar_facets_v04 import (
    AFFECT_DOMAIN,
    ALIGNMENT_DOMAIN,
    KakuScalarFacetError,
    build_affect_vad_facets_v04,
    build_intention_alignment_candidate_v04,
    build_intention_target_phase_v04,
    build_kaku_scalar_facet_envelope_v04,
    validate_affect_vad_facets_v04,
    validate_intention_alignment_candidate_v04,
    validate_kaku_scalar_facet_envelope_v04,
    validate_live_ciel_intention_phase_anchor_v04,
)

OBSERVATION_DOMAIN = b"GREMLIN-SCALAR-OBSERVATION-RECEIPT/v0.2\x00"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def observation_receipt(name, value, scale_id, *, intention_anchor=False):
    if intention_anchor:
        producer = {
            "producer_kind": "CIEL_NOEMA_JSONL_FIELD",
            "source_path": "phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl",
            "source_sha256": "11" * 32,
            "source_size": 100,
            "source_format": "utf8_jsonl",
            "extraction": {
                "selector_key": "name",
                "selector_value": "Intention",
                "field": "geometric_phase_rad",
                "line_number": 2,
                "record_sha256": "22" * 32,
            },
        }
        source_ref = (
            "ciel-noema://phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl"
            "?name=Intention#geometric_phase_rad"
        )
        adapter = "CIEL_INTENTION_PHASE_ANCHOR/v0.4"
    else:
        producer = {
            "producer_kind": "NOEMA_LIVE_F64",
            "source_path": "sensor_raw",
            "source_sha256": "11" * 32,
            "source_size": 288,
            "source_format": "little_endian_float64",
            "extraction": {"reducer": "INDEX", "sample_count": 36, "index": 0},
        }
        source_ref = f"noema-live://sensor_raw#INDEX:0/{name}"
        adapter = f"TEST_{name.upper()}_ADAPTER/v0.4"

    core = {
        "schema": "GREMLIN_SCALAR_OBSERVATION_RECEIPT_V0_2",
        "observation_name": name,
        "value_f64_hex": float(value).hex(),
        "scale_id": scale_id,
        "source_ref": source_ref,
        "epistemic_status": "TEST_FIXTURE_OBSERVATION",
        "semantic_adapter": {"adapter_id": adapter, "status": "CANDIDATE"},
        "producer": producer,
        "live_noema_witness": {
            "root": "/dev/shm/ciel_noema",
            "binding_status": "ACTIVE",
            "tether_status": "ACTIVE",
            "phi_sha256": "33" * 32,
            "tether_status_sha256": "44" * 32,
            "tick_sha256": "55" * 32,
            "live_surface_witness": True,
        },
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "OBSERVATION_ACQUIRED",
    }
    commitment = hashlib.blake2b(OBSERVATION_DOMAIN + canonical(core), digest_size=32).hexdigest()
    return {**core, "observation_receipt_commitment": commitment}


def anchor(phase=0.75):
    return observation_receipt(
        "intention_phase_anchor",
        phase,
        "RADIAN_PHASE/v0.4",
        intention_anchor=True,
    )


def affect():
    return build_affect_vad_facets_v04(
        term="curiosity",
        valence=0.65,
        arousal=0.72,
        dominance=0.18,
        confidence=0.91,
        source_ref="ciel-model://affective_lexicon/curiosity",
        epistemic_status="MODEL_DONOR_BOUND",
    )


def alignment(anchor_phase=0.75, target_phase=1.1):
    return build_intention_alignment_candidate_v04(
        phase_anchor_receipt=anchor(anchor_phase),
        target_phase=build_intention_target_phase_v04(
            target_id="goal-001",
            target_phase_rad=target_phase,
            source_ref="constraint://goal-001",
            epistemic_status="DECLARED_TARGET_CANDIDATE",
        ),
    )


def test_affect_keeps_vad_and_confidence_as_separate_scalars():
    packet = affect()
    assert validate_affect_vad_facets_v04(packet)
    assert validate_recomputed_affect_vad_facets_v04(packet)
    assert set(packet["facets"]) == {"valence", "arousal", "dominance", "confidence"}
    assert packet["collapsed_affect_scalar_present"] is False
    assert packet["vector_bound"] is False
    assert packet["execution_admitted"] is False
    assert packet["canon_allowed"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("valence", 1.01),
        ("valence", -1.01),
        ("arousal", -0.01),
        ("arousal", 1.01),
        ("dominance", 1.01),
        ("confidence", -0.01),
        ("confidence", 1.01),
    ],
)
def test_affect_facet_domains_fail_closed(field, value):
    kwargs = dict(
        term="x",
        valence=0.0,
        arousal=0.5,
        dominance=0.0,
        confidence=0.8,
        source_ref="model://x",
        epistemic_status="CANDIDATE",
    )
    kwargs[field] = value
    with pytest.raises(KakuScalarFacetError, match="outside"):
        build_affect_vad_facets_v04(**kwargs)


def test_affect_phase_is_recomputed_from_facets():
    packet = affect()
    tampered = copy.deepcopy(packet)
    tampered["derived_phase_candidate"]["affective_phase_rad_f64_hex"] = (0.123).hex()
    core = dict(tampered)
    core.pop("affect_facets_commitment")
    tampered["affect_facets_commitment"] = hashlib.blake2b(
        AFFECT_DOMAIN + canonical(core), digest_size=32
    ).hexdigest()
    assert validate_affect_vad_facets_v04(tampered)
    with pytest.raises(KakuScalarFacetFirewallError, match="differs from recomputed"):
        validate_recomputed_affect_vad_facets_v04(tampered)


def test_live_ciel_intention_anchor_requires_exact_selector_and_field():
    receipt = anchor()
    assert validate_live_ciel_intention_phase_anchor_v04(receipt)
    receipt["producer"]["extraction"]["field"] = "coherence_R"
    core = dict(receipt)
    core.pop("observation_receipt_commitment")
    receipt["observation_receipt_commitment"] = hashlib.blake2b(
        OBSERVATION_DOMAIN + canonical(core), digest_size=32
    ).hexdigest()
    with pytest.raises(KakuScalarFacetError, match="extraction mismatch"):
        validate_live_ciel_intention_phase_anchor_v04(receipt)


def test_intention_alignment_equal_phase_is_one():
    record = alignment(anchor_phase=0.75, target_phase=0.75)
    assert validate_intention_alignment_candidate_v04(record)
    assert validate_recomputed_intention_alignment_v04(record)
    assert float.fromhex(record["signed_cosine_alignment_f64_hex"]) == pytest.approx(1.0)
    assert float.fromhex(record["lock_alignment_01_f64_hex"]) == pytest.approx(1.0)
    assert record["vector_bound"] is False


def test_intention_alignment_antiphase_is_zero_lock():
    record = alignment(anchor_phase=0.5, target_phase=0.5 + math.pi)
    assert validate_recomputed_intention_alignment_v04(record)
    assert float.fromhex(record["signed_cosine_alignment_f64_hex"]) == pytest.approx(-1.0)
    assert float.fromhex(record["lock_alignment_01_f64_hex"]) == pytest.approx(0.0, abs=1e-15)


def test_intention_formula_reseal_attack_is_rejected_by_recompute_firewall():
    record = alignment(anchor_phase=0.5, target_phase=1.2)
    tampered = copy.deepcopy(record)
    fake_delta = 0.2
    fake_signed = math.cos(fake_delta)
    tampered["wrapped_delta_rad_f64_hex"] = fake_delta.hex()
    tampered["signed_cosine_alignment_f64_hex"] = fake_signed.hex()
    tampered["lock_alignment_01_f64_hex"] = (0.5 * (1.0 + fake_signed)).hex()
    core = dict(tampered)
    core.pop("intention_alignment_commitment")
    tampered["intention_alignment_commitment"] = hashlib.blake2b(
        ALIGNMENT_DOMAIN + canonical(core), digest_size=32
    ).hexdigest()
    assert validate_intention_alignment_candidate_v04(tampered)
    with pytest.raises(KakuScalarFacetFirewallError, match="differs from anchor-target"):
        validate_recomputed_intention_alignment_v04(tampered)


def test_kaku_facet_envelope_binds_facets_without_opening_vector_synthesis():
    envelope = build_kaku_scalar_facet_envelope_v04(
        kaku_id="kaku-001",
        operator_kind="TRANSFORM",
        direction="FORWARD",
        polarity=1.0,
        role="RELATION_TRANSFORM",
        source_binding="source:A",
        target_binding="target:B",
        valuation_receipt=observation_receipt("valuation", 0.4, "VALUATION/v0.4"),
        affect_facets=affect(),
        intention_alignment=alignment(),
        epistemic_support_receipt=observation_receipt(
            "epistemic_support", 0.8, "EPISTEMIC_SUPPORT/v0.4"
        ),
    )
    assert validate_kaku_scalar_facet_envelope_v04(envelope)
    assert envelope["affect_representation"] == "VAD_PLUS_CONFIDENCE_FACETS"
    assert envelope["scalar_facets_complete"] is True
    assert envelope["radical_admission_required"] is True
    assert envelope["vector_synthesis_allowed"] is False
    assert envelope["vector_bound"] is False
    assert envelope["t36_realization_present"] is False
    assert envelope["semantic_mass_present"] is False
    assert envelope["execution_admitted"] is False
    assert envelope["canon_allowed"] is False


def test_kaku_facet_envelope_rejects_wrong_standard_scalar_receipt_name():
    with pytest.raises(KakuScalarFacetError, match="expected valuation"):
        build_kaku_scalar_facet_envelope_v04(
            kaku_id="kaku-001",
            operator_kind="SOURCE",
            direction="FORWARD",
            polarity=1.0,
            role="SOURCE",
            source_binding="source:A",
            target_binding="target:B",
            valuation_receipt=observation_receipt("wrong", 0.4, "VALUATION/v0.4"),
            affect_facets=affect(),
            intention_alignment=alignment(),
            epistemic_support_receipt=observation_receipt(
                "epistemic_support", 0.8, "EPISTEMIC_SUPPORT/v0.4"
            ),
        )
