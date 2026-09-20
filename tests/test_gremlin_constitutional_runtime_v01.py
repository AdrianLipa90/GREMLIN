from __future__ import annotations

import copy

import pytest

from gremlin_mcp.constitutional_runtime import (
    RuntimeConstitutionalError,
    build_runtime_action_binding,
    build_runtime_constitutional_packet,
    require_constitutional_admission,
    validate_runtime_action_binding,
    validate_runtime_constitutional_packet,
)
from gremlin_mcp.mathematical_constitution import (
    BLOCK,
    ETHICS_GATES,
    PASS,
    UNRESOLVED,
    build_gate_receipt,
    evaluate_admission,
)


def _gate(gate: str, status: int = PASS) -> dict:
    return build_gate_receipt(
        gate=gate,
        status=status,
        relation_ids=("runtime:test:relation",),
        subject_refs=("runtime:test:subject",),
        source_classification="TEST_FIXTURE",
        source_ref=f"runtime:test:{gate.lower()}",
        evidence_refs=(f"runtime:test:evidence:{gate.lower()}",),
        reason="runtime constitutional test fixture",
    )


def _packet(
    *,
    endpoint: str,
    consequence_class: str,
    payload: dict,
    gate_override: dict[str, int] | None = None,
    capability: int = PASS,
    authority: int = PASS,
    evidence: int = PASS,
) -> dict:
    binding = build_runtime_action_binding(
        endpoint=endpoint,
        consequence_class=consequence_class,
        request_payload=payload,
    )
    override = dict(gate_override or {})
    gates = [_gate(gate, override.get(gate, PASS)) for gate in ETHICS_GATES]
    admission = evaluate_admission(
        action=binding["action_contract"],
        gate_receipts=gates,
        capability_status=capability,
        authority_status=authority,
        evidence_status=evidence,
    )
    return build_runtime_constitutional_packet(
        action_binding=binding,
        admission_receipt=admission,
    )


def test_runtime_binding_is_exact_content_addressed_request() -> None:
    payload = {"subject_id": "x", "priority": 0.82}
    binding = build_runtime_action_binding(
        endpoint="gremlin_hive_place",
        consequence_class="APPEND_ONLY",
        request_payload=payload,
    )
    assert validate_runtime_action_binding(binding) == binding
    assert binding["action_contract"]["action_id"].endswith(binding["request_sha256"])

    changed = build_runtime_action_binding(
        endpoint="gremlin_hive_place",
        consequence_class="APPEND_ONLY",
        request_payload={**payload, "priority": 0.83},
    )
    assert changed["request_sha256"] != binding["request_sha256"]
    assert changed["action_contract"]["action_sha256"] != binding["action_contract"]["action_sha256"]


def test_runtime_packet_allows_only_exact_bound_request() -> None:
    payload = {"subject_id": "x", "priority": 0.82}
    packet = _packet(
        endpoint="gremlin_hive_place",
        consequence_class="APPEND_ONLY",
        payload=payload,
    )
    validated = require_constitutional_admission(
        endpoint="gremlin_hive_place",
        consequence_class="APPEND_ONLY",
        request_payload=payload,
        constitutional_packet=packet,
    )
    assert validated["status"] == "ADMITTED"

    with pytest.raises(RuntimeConstitutionalError, match="exact runtime request"):
        require_constitutional_admission(
            endpoint="gremlin_hive_place",
            consequence_class="APPEND_ONLY",
            request_payload={**payload, "priority": 0.81},
            constitutional_packet=packet,
        )


def test_runtime_packet_cannot_cross_endpoint_or_consequence_class() -> None:
    payload = {"subject_id": "x"}
    packet = _packet(
        endpoint="gremlin_hive_dispute",
        consequence_class="APPEND_ONLY",
        payload=payload,
    )
    with pytest.raises(RuntimeConstitutionalError):
        require_constitutional_admission(
            endpoint="gremlin_hive_latch",
            consequence_class="GOVERNANCE",
            request_payload=payload,
            constitutional_packet=packet,
        )


def test_runtime_packet_denies_or_defers_fail_closed() -> None:
    payload = {"subject_id": "x"}
    denied = _packet(
        endpoint="gremlin_hive_dispute",
        consequence_class="APPEND_ONLY",
        payload=payload,
        capability=BLOCK,
    )
    with pytest.raises(RuntimeConstitutionalError, match="DENY"):
        require_constitutional_admission(
            endpoint="gremlin_hive_dispute",
            consequence_class="APPEND_ONLY",
            request_payload=payload,
            constitutional_packet=denied,
        )

    deferred = _packet(
        endpoint="gremlin_hive_dispute",
        consequence_class="APPEND_ONLY",
        payload=payload,
        authority=UNRESOLVED,
    )
    with pytest.raises(RuntimeConstitutionalError, match="DEFER"):
        require_constitutional_admission(
            endpoint="gremlin_hive_dispute",
            consequence_class="APPEND_ONLY",
            request_payload=payload,
            constitutional_packet=deferred,
        )


def test_runtime_packet_tamper_is_rejected() -> None:
    payload = {"subject_id": "x"}
    packet = _packet(
        endpoint="gremlin_hive_dispute",
        consequence_class="APPEND_ONLY",
        payload=payload,
    )
    validate_runtime_constitutional_packet(packet)
    tampered = copy.deepcopy(packet)
    tampered["action_binding"]["endpoint"] = "gremlin_hive_latch"
    with pytest.raises(RuntimeConstitutionalError):
        validate_runtime_constitutional_packet(tampered)
