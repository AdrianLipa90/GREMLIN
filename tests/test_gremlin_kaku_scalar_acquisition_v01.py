import copy

import pytest

from tools.gremlin_kaku_radical_scalar_plane_v01 import validate_kaku_scalar_packet
from tools.gremlin_kaku_scalar_acquisition_v01 import (
    CIEL_IMPLEMENTATION_DONORS,
    GremlinScalarAcquisitionError,
    build_acquisition_bundle,
    build_kaku_scalar_packet_from_acquisition,
    build_observation_receipt,
    build_producer_contract,
    validate_acquisition_bundle,
    validate_observation_receipt,
    validate_producer_contract,
)

INPUT_HASH = "11" * 32


def producer(role, *, source="TEST_FIXTURE", live=False, scale=None):
    return build_producer_contract(
        producer_id=f"producer:{role}",
        producer_version="0.1",
        semantic_role=role,
        scale_id=scale or f"{role}/v1",
        formula_contract_ref=f"formula:{role}/v1",
        implementation_ref=f"implementation:{role}/v1",
        source_classification=source,
        producer_classification="TEST_PRODUCER" if source == "TEST_FIXTURE" else "SEMANTICALLY_BOUND_PRODUCER_CANDIDATE",
        live_required=live,
    )


def receipt(role, value, *, source="TEST_FIXTURE", live=False, scale=None):
    contract = producer(role, source=source, live=live, scale=scale)
    return build_observation_receipt(
        producer_contract=contract,
        value=value,
        source_ref=f"source:{role}",
        input_commitment=INPUT_HASH,
        epistemic_status="OBSERVED_CANDIDATE",
        evidence_refs=[f"evidence:{role}:b", f"evidence:{role}:a"],
        live_surface_ref="/dev/shm/ciel_noema" if live else None,
    )


def bundle():
    return build_acquisition_bundle([
        receipt("valuation", 0.4),
        receipt("affect", -0.2),
        receipt("intention_alignment", 0.8),
        receipt("epistemic_support", 0.9),
    ])


def test_producer_contract_is_deterministic_and_semantically_bound():
    a = producer("valuation")
    b = producer("valuation")
    assert validate_producer_contract(a)
    assert a == b
    assert a["canonical_term_id"] == "CLX2-AFFECT-001"
    assert a["silent_scale_conversion_allowed"] is False
    assert a["conflict_averaging_allowed"] is False
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False


def test_affect_declares_valuation_dependency():
    contract = producer("affect")
    assert contract["canonical_term_id"] == "CLX2-AFFECT-002"
    assert contract["support_term_ids"] == ["CLX2-AFFECT-001"]


def test_epistemic_support_is_confidence_bound_to_evidence_and_truth_evaluation():
    contract = producer("epistemic_support")
    assert contract["canonical_term_id"] == "CLX2-SEM-023"
    assert contract["support_term_ids"] == ["CLX2-SEM-019", "CLX2-AFFECT-005"]


def test_unknown_semantic_role_fails_closed():
    with pytest.raises(GremlinScalarAcquisitionError, match="unsupported scalar semantic role"):
        producer("resonance_as_truth")


def test_nonfinite_observation_fails_closed():
    contract = producer("affect")
    with pytest.raises(GremlinScalarAcquisitionError, match="value must be finite"):
        build_observation_receipt(
            producer_contract=contract,
            value=float("nan"),
            source_ref="source:affect",
            input_commitment=INPUT_HASH,
            epistemic_status="OBSERVED_CANDIDATE",
            evidence_refs=[],
        )


def test_observation_scale_mismatch_has_no_silent_conversion():
    contract = producer("valuation", scale="valuation/unit-a")
    with pytest.raises(GremlinScalarAcquisitionError, match="observed scale differs"):
        build_observation_receipt(
            producer_contract=contract,
            value=0.5,
            source_ref="source:valuation",
            input_commitment=INPUT_HASH,
            epistemic_status="OBSERVED_CANDIDATE",
            evidence_refs=[],
            observed_scale_id="valuation/unit-b",
        )


def test_live_required_producer_rejects_static_source_contract():
    with pytest.raises(GremlinScalarAcquisitionError, match="must bind LIVE_NOEMA_WITNESS"):
        producer("intention_alignment", source="STATIC_REFERENCE", live=True)


def test_live_receipt_requires_canonical_noema_surface():
    contract = producer("intention_alignment", source="LIVE_NOEMA_WITNESS", live=True)
    with pytest.raises(GremlinScalarAcquisitionError, match="canonical NOEMA surface"):
        build_observation_receipt(
            producer_contract=contract,
            value=0.7,
            source_ref="source:intention",
            input_commitment=INPUT_HASH,
            epistemic_status="LIVE_OBSERVATION_CANDIDATE",
            evidence_refs=[],
            live_surface_ref="/tmp/fake_noema",
        )


def test_live_receipt_accepts_live_noema_surface_and_is_deterministic():
    a = receipt("intention_alignment", 0.7, source="LIVE_NOEMA_WITNESS", live=True)
    b = receipt("intention_alignment", 0.7, source="LIVE_NOEMA_WITNESS", live=True)
    assert validate_observation_receipt(a)
    assert a == b
    assert a["live_surface_ref"] == "/dev/shm/ciel_noema"


def test_tampered_observation_receipt_fails():
    record = receipt("valuation", 0.4)
    record["value_f64_hex"] = float(0.5).hex()
    with pytest.raises(GremlinScalarAcquisitionError, match="commitment mismatch"):
        validate_observation_receipt(record)


def test_bundle_requires_exact_four_semantic_roles():
    with pytest.raises(GremlinScalarAcquisitionError, match="exact scalar role set required"):
        build_acquisition_bundle([
            receipt("valuation", 0.4),
            receipt("affect", -0.2),
            receipt("intention_alignment", 0.8),
        ])


def test_bundle_rejects_duplicate_or_conflicting_role_instead_of_averaging():
    with pytest.raises(GremlinScalarAcquisitionError, match="conflicting duplicate scalar role"):
        build_acquisition_bundle([
            receipt("valuation", 0.4),
            receipt("valuation", 0.6),
            receipt("affect", -0.2),
            receipt("intention_alignment", 0.8),
            receipt("epistemic_support", 0.9),
        ])


def test_bundle_is_order_independent_at_acquisition_input_and_canonically_ordered():
    receipts = [
        receipt("epistemic_support", 0.9),
        receipt("valuation", 0.4),
        receipt("intention_alignment", 0.8),
        receipt("affect", -0.2),
    ]
    a = build_acquisition_bundle(receipts)
    b = bundle()
    assert validate_acquisition_bundle(a)
    assert a == b
    assert [x["semantic_role"] for x in a["observations"]] == [
        "affect",
        "epistemic_support",
        "intention_alignment",
        "valuation",
    ]
    assert a["silent_scale_conversion_used"] is False
    assert a["conflict_averaging_used"] is False


def test_tampered_bundle_fails():
    record = bundle()
    record["observations"][0]["value_f64_hex"] = float(99.0).hex()
    with pytest.raises(GremlinScalarAcquisitionError, match="bundle commitment mismatch"):
        validate_acquisition_bundle(record)


def test_kaku_packet_is_built_from_receipt_lineage_and_remains_valid():
    acquisition = bundle()
    packet = build_kaku_scalar_packet_from_acquisition(
        acquisition_bundle=acquisition,
        kaku_id="k-acquired-001",
        operator_kind="TRANSFORM",
        direction="FORWARD",
        polarity=1.0,
        role="RELATION_TRANSFORM",
        source_binding="source:node-a",
        target_binding="target:node-b",
        evidence_refs=["candidate:001"],
    )
    assert validate_kaku_scalar_packet(packet)
    assert packet["vector_bound"] is False
    assert packet["execution_admitted"] is False
    assert packet["canon_allowed"] is False
    assert f"acquisition:{acquisition['acquisition_bundle_commitment']}" in packet["evidence_refs"]
    for observation in acquisition["observations"]:
        assert f"receipt:{observation['receipt_id']}" in packet["evidence_refs"]


def test_different_scalar_receipt_changes_kaku_commitment():
    a = bundle()
    b = build_acquisition_bundle([
        receipt("valuation", 0.41),
        receipt("affect", -0.2),
        receipt("intention_alignment", 0.8),
        receipt("epistemic_support", 0.9),
    ])
    kwargs = dict(
        kaku_id="k-acquired-001",
        operator_kind="TRANSFORM",
        direction="FORWARD",
        polarity=1.0,
        role="RELATION_TRANSFORM",
        source_binding="source:node-a",
        target_binding="target:node-b",
    )
    ka = build_kaku_scalar_packet_from_acquisition(acquisition_bundle=a, **kwargs)
    kb = build_kaku_scalar_packet_from_acquisition(acquisition_bundle=b, **kwargs)
    assert ka["kaku_scalar_commitment"] != kb["kaku_scalar_commitment"]


def test_ciel_donors_are_explicit_candidates():
    assert CIEL_IMPLEMENTATION_DONORS["intention_field"]["candidate_role"] == "intention_alignment"
    assert CIEL_IMPLEMENTATION_DONORS["affective_orchestrator"]["candidate_role"] == "affect"
    assert all(v["binding_status"] == "IMPLEMENTATION_DONOR_CANDIDATE" for v in CIEL_IMPLEMENTATION_DONORS.values())
