from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_scalar_source_registry_v03 import (
    ETHICS_CAPABILITY_SCHEMA,
    ETHICS_REQUEST_SCHEMA,
    NOEMA_ETHICS_MODULE_SHA256,
    NOEMA_ETHICS_SCHEMA,
    ScalarSourceRegistryError,
    build_noema_ethics_exchange_request,
    build_scalar_source_registry_v03,
    readiness_report,
    validate_scalar_source_registry_v03,
)

FIREWALL_SCHEMA = "GREMLIN_SCALAR_SOURCE_FIREWALL_V0_3"
REQUEST_DOMAIN = b"GREMLIN-NOEMA-ETHICS-EXCHANGE-REQUEST/v0.3\x00"


class ScalarSourceFirewallError(ScalarSourceRegistryError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise ScalarSourceFirewallError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ScalarSourceFirewallError(f"{name} must be hexadecimal") from exc
    return text


def validate_frozen_scalar_source_registry_v03(registry: Mapping[str, Any]) -> bool:
    """Validate both integrity and the exact frozen v0.3 source policy.

    The lower-level registry validator verifies shape, authority firewalls and the
    content commitment. This validator additionally requires byte-equivalent
    canonical policy content to the v0.3 builder. A caller therefore cannot re-seal
    a modified donor/readiness policy and still call it v0.3.
    """

    validate_scalar_source_registry_v03(registry)
    expected = build_scalar_source_registry_v03()
    if _canonical(registry) != _canonical(expected):
        raise ScalarSourceFirewallError("scalar source registry differs from frozen v0.3 policy")
    return True


def frozen_readiness_report_v03(registry: Mapping[str, Any]) -> dict[str, Any]:
    validate_frozen_scalar_source_registry_v03(registry)
    report = readiness_report(registry)
    return {
        "schema": FIREWALL_SCHEMA,
        **report,
        "policy_frozen": True,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def build_non_actuating_noema_ethics_exchange_request_v03(
    *,
    candidate_id: str,
    radical_id: str,
    node_state_commitment: str,
    semantic_tensor_commitment: str,
    context_commitment: str,
    consent_evidence_ref: str,
    reversibility_evidence_ref: str,
    no_go_evidence_ref: str,
    capability: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a GREMLIN research request only when NOEMA external execution is closed.

    This adapter is intentionally narrower than the generic capability object. A
    future NOEMA generation may expose broader execution capability; that must not
    silently enlarge GREMLIN authority. Such a change requires a new reviewed
    adapter version.
    """

    if capability.get("schema") != ETHICS_CAPABILITY_SCHEMA:
        raise ScalarSourceFirewallError("NOEMA ethics capability schema mismatch")
    if capability.get("status") != "ACTIVE":
        raise ScalarSourceFirewallError("ACTIVE NOEMA ethics capability required")
    if capability.get("ethics_field_schema") != NOEMA_ETHICS_SCHEMA:
        raise ScalarSourceFirewallError("NOEMA ethics schema mismatch")
    if capability.get("ethics_field_sha256") != NOEMA_ETHICS_MODULE_SHA256:
        raise ScalarSourceFirewallError("NOEMA ethics module seal mismatch")
    if capability.get("ethics_mode") != "LIVE_COMPUTE_ON_EXCHANGE":
        raise ScalarSourceFirewallError("NOEMA ethics must remain live-compute on exchange")
    if capability.get("ethics_static_state") is not False:
        raise ScalarSourceFirewallError("static ethics state is forbidden")
    if capability.get("external_execution_enabled") is not False:
        raise ScalarSourceFirewallError(
            "GREMLIN v0.3 research adapter requires NOEMA external execution to remain disabled"
        )

    request = build_noema_ethics_exchange_request(
        candidate_id=candidate_id,
        radical_id=radical_id,
        node_state_commitment=node_state_commitment,
        semantic_tensor_commitment=semantic_tensor_commitment,
        context_commitment=context_commitment,
        consent_evidence_ref=consent_evidence_ref,
        reversibility_evidence_ref=reversibility_evidence_ref,
        no_go_evidence_ref=no_go_evidence_ref,
        capability=capability,
    )
    if request.get("external_execution_enabled") is not False:
        raise ScalarSourceFirewallError("non-actuating request leaked external execution capability")
    validate_non_actuating_noema_ethics_exchange_request_v03(request)
    return request


def validate_non_actuating_noema_ethics_exchange_request_v03(request: Mapping[str, Any]) -> bool:
    if request.get("schema") != ETHICS_REQUEST_SCHEMA:
        raise ScalarSourceFirewallError("unsupported NOEMA ethics request schema")
    if request.get("request_scope") != "RESEARCH_ADAPTER_NON_ACTUATING":
        raise ScalarSourceFirewallError("NOEMA ethics request is outside non-actuating research scope")
    if request.get("external_execution_enabled") is not False:
        raise ScalarSourceFirewallError("NOEMA ethics request cannot enable external execution")
    if request.get("production_runtime_write") is not False:
        raise ScalarSourceFirewallError("NOEMA ethics request cannot grant runtime write")
    if request.get("execution_admitted") is not False or request.get("canon_allowed") is not False:
        raise ScalarSourceFirewallError("NOEMA ethics request authority boundary violated")
    if request.get("status") != "SEALED_NOEMA_ETHICS_EXCHANGE_REQUEST":
        raise ScalarSourceFirewallError("wrong NOEMA ethics request status")

    for key in ("candidate_id", "radical_id"):
        if not str(request.get(key, "")):
            raise ScalarSourceFirewallError(f"{key} must be non-empty")

    inputs = request.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ScalarSourceFirewallError("ethics request inputs must be a mapping")
    for key in ("node_state_commitment", "semantic_tensor_commitment", "context_commitment"):
        _hash64(inputs.get(key), f"inputs.{key}")

    gates = request.get("hard_gate_evidence")
    if not isinstance(gates, Mapping) or set(gates) != {"consent", "reversibility", "no_go"}:
        raise ScalarSourceFirewallError("exact hard-gate evidence set required")
    for key, value in gates.items():
        if not str(value):
            raise ScalarSourceFirewallError(f"hard_gate_evidence.{key} must be non-empty")

    binding = request.get("noema_ethics_binding")
    if not isinstance(binding, Mapping):
        raise ScalarSourceFirewallError("NOEMA ethics binding missing")
    if binding.get("schema") != NOEMA_ETHICS_SCHEMA:
        raise ScalarSourceFirewallError("request NOEMA ethics schema mismatch")
    if binding.get("module_sha256") != NOEMA_ETHICS_MODULE_SHA256:
        raise ScalarSourceFirewallError("request NOEMA ethics module seal mismatch")
    if binding.get("mode") != "LIVE_COMPUTE_ON_EXCHANGE":
        raise ScalarSourceFirewallError("request NOEMA ethics mode mismatch")
    _hash64(binding.get("ac_current_sha256"), "noema_ethics_binding.ac_current_sha256")
    _hash64(binding.get("phi_sha256"), "noema_ethics_binding.phi_sha256")

    supplied = _hash64(request.get("request_commitment"), "request_commitment")
    core = copy.deepcopy(dict(request))
    core.pop("request_commitment", None)
    expected = hashlib.blake2b(REQUEST_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise ScalarSourceFirewallError("NOEMA ethics request commitment mismatch")
    return True
