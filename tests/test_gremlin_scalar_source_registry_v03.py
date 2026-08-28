import copy
import hashlib
import json

import pytest

from tools.gremlin_scalar_source_firewall_v03 import (
    ScalarSourceFirewallError,
    build_non_actuating_noema_ethics_exchange_request_v03,
    frozen_readiness_report_v03,
    validate_frozen_scalar_source_registry_v03,
    validate_non_actuating_noema_ethics_exchange_request_v03,
)
from tools.gremlin_scalar_source_registry_v03 import (
    NOEMA_ETHICS_MODULE_SHA256,
    NOEMA_ETHICS_SCHEMA,
    ScalarSourceRegistryError,
    build_scalar_source_registry_v03,
    validate_noema_ethics_status_payload,
)

REGISTRY_DOMAIN = b"GREMLIN-SCALAR-SOURCE-REGISTRY/v0.3\x00"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def reseal_registry(registry):
    core = copy.deepcopy(registry)
    core.pop("registry_commitment", None)
    registry["registry_commitment"] = hashlib.blake2b(
        REGISTRY_DOMAIN + canonical(core), digest_size=32
    ).hexdigest()
    return registry


def ethics_status_payload(**overrides):
    payload = {
        "status": "ACTIVE",
        "ethics_field_status": "ACTIVE",
        "ethics_field_schema": NOEMA_ETHICS_SCHEMA,
        "ethics_field_sha256": NOEMA_ETHICS_MODULE_SHA256,
        "ethics_mode": "LIVE_COMPUTE_ON_EXCHANGE",
        "ethics_static_state": False,
        "external_execution_enabled": False,
        "no_static_fallback": True,
        "library_is_operating_state": False,
        "ac_current_sha256": "11" * 32,
        "phi_sha256": "22" * 32,
    }
    payload.update(overrides)
    return payload


def capability(**overrides):
    cap = validate_noema_ethics_status_payload(ethics_status_payload(**overrides))
    return cap


def test_frozen_registry_is_deterministic_and_valid():
    a = build_scalar_source_registry_v03()
    b = build_scalar_source_registry_v03()
    assert validate_frozen_scalar_source_registry_v03(a)
    assert a == b
    assert a["registry_commitment"] == b["registry_commitment"]
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False


def test_registry_separates_semantic_authority_from_numeric_producer():
    registry = build_scalar_source_registry_v03()
    assert registry["rules"]["semantic_authority_is_numeric_producer"] is False
    assert registry["sources"]["valuation"]["authority"] == "LIBRARY_SEMANTIC_REGISTRY"
    assert registry["sources"]["valuation"]["readiness"] == "UNRESOLVED_LIVE_PRODUCER"
    assert registry["sources"]["affect"]["readiness"] == "MODEL_DONOR_ONLY"
    assert registry["sources"]["intention_alignment"]["readiness"] == "PARTIAL_LIVE_ANCHOR"
    assert registry["sources"]["epistemic_support"]["readiness"] == "UNRESOLVED_LIVE_PRODUCER"


def test_ciel_affective_lexicon_is_model_donor_not_live_telemetry():
    source = build_scalar_source_registry_v03()["sources"]["affect"]
    donor = source["donors"][0]
    assert donor["repository"] == "AdrianLipa90/CIEL-Omega-ApokalypOS"
    assert donor["operational_role"] == "SCALE_AND_MODEL_DONOR"
    assert set(donor["provides"]) == {
        "valence",
        "arousal",
        "dominance",
        "confidence",
        "affective_phase_encoding",
    }
    assert source["readiness"] != "LIVE_PRODUCER"


def test_ciel_seeded_intention_field_is_rejected_as_live_intention_evidence():
    source = build_scalar_source_registry_v03()["sources"]["intention_alignment"]
    assert source["live_anchor"]["field"] == "geometric_phase_rad"
    assert source["rejected_live_donor"]["path"].endswith("fields/intention_field.py")
    assert "pseudo-random" in source["rejected_live_donor"]["reason"]
    assert "target" in source["missing_for_ready"]


def test_legacy_ciel_ethical_engine_is_post_realization_donor():
    source = build_scalar_source_registry_v03()["sources"]["ethical_integrity"]
    donor = source["legacy_donor"]
    assert source["readiness"] == "LIVE_COMPUTE_AVAILABLE"
    assert donor["stage"] == "POST_REALIZATION_LEGACY_DONOR"
    assert "mass" in donor["reason"]


def test_current_readiness_stays_fail_closed_before_vector_synthesis():
    report = frozen_readiness_report_v03(build_scalar_source_registry_v03())
    assert report["kaku_pre_vector"]["ready"] is False
    assert set(report["kaku_pre_vector"]["unresolved_sources"]) == {
        "valuation",
        "affect",
        "intention_alignment",
        "epistemic_support",
    }
    assert report["radical_pre_vector_capability"]["ready"] is False
    assert set(report["radical_pre_vector_capability"]["ready_sources"]) == {
        "ethical_integrity",
        "consent",
        "reversibility",
        "no_go",
    }
    assert set(report["radical_pre_vector_capability"]["unresolved_sources"]) == {
        "contradiction_load",
        "recursive_integrity",
    }
    assert report["post_realization"]["ready"] is False
    assert report["vector_synthesis_globally_ready"] is False
    assert report["execution_admitted"] is False


def test_hard_gate_capability_is_not_per_candidate_gate_evidence():
    report = frozen_readiness_report_v03(build_scalar_source_registry_v03())
    detail = report["radical_pre_vector_capability"]["detail"]
    assert detail["consent"] == "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE"
    assert detail["reversibility"] == "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE"
    assert detail["no_go"] == "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE"
    assert report["vector_synthesis_globally_ready"] is False


def test_resealed_policy_mutation_is_rejected_by_frozen_firewall():
    registry = build_scalar_source_registry_v03()
    registry["sources"]["affect"]["readiness"] = "LIVE_PRODUCER"
    reseal_registry(registry)
    with pytest.raises(ScalarSourceFirewallError, match="differs from frozen v0.3 policy"):
        validate_frozen_scalar_source_registry_v03(registry)


def test_resealed_post_realization_promotion_is_rejected():
    registry = build_scalar_source_registry_v03()
    registry["sources"]["semantic_mass"]["stage"] = "PRE_VECTOR_KAKU"
    registry["sources"]["semantic_mass"]["readiness"] = "LIVE_PRODUCER"
    reseal_registry(registry)
    with pytest.raises(ScalarSourceFirewallError, match="differs from frozen v0.3 policy"):
        validate_frozen_scalar_source_registry_v03(registry)


def test_noema_ethics_status_accepts_exact_live_contract_shape():
    cap = capability()
    assert cap["status"] == "ACTIVE"
    assert cap["ethics_field_schema"] == NOEMA_ETHICS_SCHEMA
    assert cap["ethics_field_sha256"] == NOEMA_ETHICS_MODULE_SHA256
    assert cap["ethics_mode"] == "LIVE_COMPUTE_ON_EXCHANGE"
    assert cap["ethics_static_state"] is False
    assert cap["external_execution_enabled"] is False


@pytest.mark.parametrize(
    "override,match",
    [
        ({"status": "STALE"}, "not ACTIVE"),
        ({"ethics_field_status": "BLOCKED"}, "not ACTIVE"),
        ({"ethics_field_schema": "OLD"}, "schema mismatch"),
        ({"ethics_field_sha256": "00" * 32}, "module seal mismatch"),
        ({"ethics_mode": "STATIC"}, "must be LIVE_COMPUTE_ON_EXCHANGE"),
        ({"ethics_static_state": True}, "static-state fallback is forbidden"),
        ({"no_static_fallback": False}, "no-static-fallback invariant missing"),
        ({"library_is_operating_state": True}, "Library cannot be NOEMA operating state"),
    ],
)
def test_noema_ethics_status_fails_closed(override, match):
    with pytest.raises(ScalarSourceRegistryError, match=match):
        validate_noema_ethics_status_payload(ethics_status_payload(**override))


def test_non_actuating_ethics_request_is_deterministic_and_sealed():
    kwargs = dict(
        candidate_id="candidate-ethics-001",
        radical_id="radical-ethics-001",
        node_state_commitment="33" * 32,
        semantic_tensor_commitment="44" * 32,
        context_commitment="55" * 32,
        consent_evidence_ref="consent:receipt:001",
        reversibility_evidence_ref="reversibility:receipt:001",
        no_go_evidence_ref="nogo:audit:001",
        capability=capability(),
    )
    a = build_non_actuating_noema_ethics_exchange_request_v03(**kwargs)
    b = build_non_actuating_noema_ethics_exchange_request_v03(**kwargs)
    assert validate_non_actuating_noema_ethics_exchange_request_v03(a)
    assert a == b
    assert a["external_execution_enabled"] is False
    assert a["production_runtime_write"] is False
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False
    assert a["hard_gate_evidence"] == {
        "consent": "consent:receipt:001",
        "reversibility": "reversibility:receipt:001",
        "no_go": "nogo:audit:001",
    }
    assert "ethical_integrity" not in a


def test_non_actuating_adapter_rejects_future_external_execution_capability():
    cap = capability(external_execution_enabled=True)
    with pytest.raises(ScalarSourceFirewallError, match="external execution to remain disabled"):
        build_non_actuating_noema_ethics_exchange_request_v03(
            candidate_id="c",
            radical_id="r",
            node_state_commitment="33" * 32,
            semantic_tensor_commitment="44" * 32,
            context_commitment="55" * 32,
            consent_evidence_ref="consent:1",
            reversibility_evidence_ref="reverse:1",
            no_go_evidence_ref="nogo:1",
            capability=cap,
        )


def test_request_requires_all_three_gate_evidence_refs():
    with pytest.raises(ScalarSourceRegistryError, match="no_go_evidence_ref must be non-empty"):
        build_non_actuating_noema_ethics_exchange_request_v03(
            candidate_id="c",
            radical_id="r",
            node_state_commitment="33" * 32,
            semantic_tensor_commitment="44" * 32,
            context_commitment="55" * 32,
            consent_evidence_ref="consent:1",
            reversibility_evidence_ref="reverse:1",
            no_go_evidence_ref="",
            capability=capability(),
        )


def test_tampered_request_is_rejected():
    request = build_non_actuating_noema_ethics_exchange_request_v03(
        candidate_id="c",
        radical_id="r",
        node_state_commitment="33" * 32,
        semantic_tensor_commitment="44" * 32,
        context_commitment="55" * 32,
        consent_evidence_ref="consent:1",
        reversibility_evidence_ref="reverse:1",
        no_go_evidence_ref="nogo:1",
        capability=capability(),
    )
    request["hard_gate_evidence"]["consent"] = "consent:tampered"
    with pytest.raises(ScalarSourceFirewallError, match="commitment mismatch"):
        validate_non_actuating_noema_ethics_exchange_request_v03(request)
