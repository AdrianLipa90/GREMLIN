from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from .hive_authority import HiveAuthorityRuntime
from .memory_anti_entropy import (
    build_hive_inventory,
    build_hive_manifest,
    export_hive_delta,
    plan_hive_delta,
)
from .memory_capabilities import require_access
from .memory_consolidation import (
    build_consolidation_route,
    validate_consolidation_plan,
)
from .memory_exchange import (
    ingest_exchange_bundle,
    ingest_exchange_envelope,
    validate_exchange_bundle,
    validate_exchange_envelope,
)

SCHEMA = "GREMLIN_BESTIARY_MEMORY_GATEWAY_V0_1"
VERSION = "0.1.0"
RELATIONAL_LAYER = "RELATIONAL"
APPEND_INTENTS = frozenset(
    {
        "OBSERVE_APPEND",
        "DERIVE",
        "GRAPH_APPEND",
        "EDGE_APPEND",
        "NODE_LINK",
        "FLAG",
        "CONSOLIDATE",
        "SUPERSEDE_REQUEST",
        "QUARANTINE_REQUEST",
        "PROMOTE_REQUEST",
        "RETENTION_REQUEST",
    }
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _operation(value: Any) -> str:
    return _text(value, "operation").upper()


def _receipt(
    *,
    beast: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_id: str,
    generation_id: str,
    task_id: str,
    token: Mapping[str, Any],
) -> dict[str, Any]:
    return require_access(
        beast=beast,
        layer=layer,
        operation=operation,
        artifact_type=artifact_type,
        subject_id=subject_id,
        generation_id=generation_id,
        task_id=task_id,
        token=token,
    )


def _gateway_result(
    *,
    action: str,
    capability_receipt: Mapping[str, Any],
    result: Any,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "action": action,
        "capability_receipt": dict(capability_receipt),
        "result": result,
        "authority": "SHARED_COGNITION_ONLY",
        "epistemic": "CHYBA",
        "canon_allowed": False,
        "claims": {
            "bestiary_capability_enforced": True,
            "storage_engine_is_principal_neutral": True,
            "capability_implies_identity_authentication": False,
            "deletion_authority": False,
            "overwrite_authority": False,
            "in_place_edit_authority": False,
        },
    }


def read_hive_head(
    runtime: HiveAuthorityRuntime,
    *,
    beast: str,
    artifact_type: str,
    hive_subject_id: str,
    subject_id: str,
    generation_id: str,
    task_id: str,
    token: Mapping[str, Any],
    include_payload: bool = False,
) -> dict[str, Any]:
    """Read one RELATIONAL Hive head under logical subject/generation scope."""
    hive_subject = _text(hive_subject_id, "hive_subject_id")
    subject = _text(subject_id, "subject_id")
    generation = _text(generation_id, "generation_id")
    operation = "READ_PAYLOAD" if include_payload else "READ_METADATA"
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation=operation,
        artifact_type=artifact_type,
        subject_id=subject,
        generation_id=generation,
        task_id=task_id,
        token=token,
    )
    record = runtime.head(hive_subject)
    record_payload = dict(record.payload)
    embedded_subject = record_payload.get("subject_id")
    embedded_generation = record_payload.get("generation_id")
    if embedded_subject is not None and embedded_subject != subject:
        raise PermissionError("Hive record is outside authorized logical subject scope")
    if embedded_generation is not None and embedded_generation != generation:
        raise PermissionError("Hive record is outside authorized generation scope")
    if embedded_subject is None and embedded_generation is None and record.subject_id != subject:
        raise PermissionError("Hive record is outside authorized logical subject scope")
    row = {
        "record_id": record.record_id,
        "subject_id": record.subject_id,
        "version": record.version,
        "payload_hash": record.payload_hash,
        "priority": record.priority,
        "coordinate": asdict(record.coordinate),
        "semantic_key": record.semantic_key,
        "state": record.state,
        "gates": asdict(record.gates),
        "provenance": list(record.provenance),
        "dependencies": list(record.dependencies),
        "contradictions": list(record.contradictions),
        "parent_record_id": record.parent_record_id,
        "seal_receipt": record.seal_receipt,
        "authority": record.authority,
    }
    if include_payload:
        row["payload"] = dict(record.payload)
    return _gateway_result(
        action="READ_HIVE_HEAD_PAYLOAD" if include_payload else "READ_HIVE_HEAD_METADATA",
        capability_receipt=receipt,
        result=row,
    )


def build_hive_inventory_as_beast(
    runtime: HiveAuthorityRuntime,
    *,
    beast: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    node_id: str,
) -> dict[str, Any]:
    """Expose anti-entropy inventory only under whole-Hive metadata authority."""
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation="READ_METADATA",
        artifact_type=artifact_type,
        subject_id="*",
        generation_id="*",
        task_id=task_id,
        token=token,
    )
    result = build_hive_inventory(runtime, node_id=node_id)
    return _gateway_result(
        action="BUILD_HIVE_ANTI_ENTROPY_INVENTORY",
        capability_receipt=receipt,
        result=result,
    )


def build_hive_manifest_as_beast(
    runtime: HiveAuthorityRuntime,
    *,
    beast: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    node_id: str,
    prefixes: Sequence[str],
) -> dict[str, Any]:
    """Expose divergent-bucket descriptors without disclosing exchange proof payloads."""
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation="READ_METADATA",
        artifact_type=artifact_type,
        subject_id="*",
        generation_id="*",
        task_id=task_id,
        token=token,
    )
    result = build_hive_manifest(runtime, node_id=node_id, prefixes=prefixes)
    return _gateway_result(
        action="BUILD_HIVE_ANTI_ENTROPY_MANIFEST",
        capability_receipt=receipt,
        result=result,
    )


def plan_hive_delta_as_beast(
    *,
    beast: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    sender_inventory: Mapping[str, Any],
    receiver_inventory: Mapping[str, Any],
    sender_manifest: Mapping[str, Any],
    receiver_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare anti-entropy metadata under explicit COMPARE authority."""
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation="COMPARE",
        artifact_type=artifact_type,
        subject_id="*",
        generation_id="*",
        task_id=task_id,
        token=token,
    )
    result = plan_hive_delta(
        sender_inventory,
        receiver_inventory,
        sender_manifest,
        receiver_manifest,
    )
    return _gateway_result(
        action="PLAN_HIVE_ANTI_ENTROPY_DELTA",
        capability_receipt=receipt,
        result=result,
    )


def export_hive_delta_as_beast(
    runtime: HiveAuthorityRuntime,
    plan: Mapping[str, Any],
    *,
    beast: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
) -> dict[str, Any]:
    """Export proof payloads only under whole-Hive READ_PAYLOAD authority."""
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation="READ_PAYLOAD",
        artifact_type=artifact_type,
        subject_id="*",
        generation_id="*",
        task_id=task_id,
        token=token,
    )
    result = export_hive_delta(runtime, plan)
    return _gateway_result(
        action="EXPORT_HIVE_ANTI_ENTROPY_DELTA",
        capability_receipt=receipt,
        result=result,
    )


def ingest_exchange_envelope_as_beast(
    runtime: HiveAuthorityRuntime,
    envelope: Mapping[str, Any],
    *,
    beast: str,
    operation: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    priority: float = 0.82,
    consumer_id: str = "GREMLIN-HIVE",
    constitutional_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one validated RELATIONAL exchange envelope under typed Bestiary write intent."""
    normalized = validate_exchange_envelope(envelope)
    op = _operation(operation)
    if op not in APPEND_INTENTS:
        raise PermissionError("memory exchange ingest requires an append/proposal intent")
    if normalized["target_layer"] != RELATIONAL_LAYER:
        raise ValueError("GREMLIN Bestiary gateway only ingests RELATIONAL exchange targets")
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation=op,
        artifact_type=artifact_type,
        subject_id=normalized["subject_id"],
        generation_id=normalized["generation_id"],
        task_id=task_id,
        token=token,
    )
    result = ingest_exchange_envelope(
        runtime,
        normalized,
        priority=priority,
        consumer_id=consumer_id,
    )
    return _gateway_result(
        action="INGEST_EXCHANGE_ENVELOPE",
        capability_receipt=receipt,
        result=result,
    )


def ingest_exchange_bundle_as_beast(
    runtime: HiveAuthorityRuntime,
    bundle: Mapping[str, Any],
    *,
    beast: str,
    operation: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    priority: float = 0.82,
    consumer_id: str = "GREMLIN-HIVE",
    constitutional_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one lineage-verified RELATIONAL exchange target under typed Bestiary intent."""
    normalized = validate_exchange_bundle(bundle)
    target = normalized["target_envelope"]
    op = _operation(operation)
    if op not in APPEND_INTENTS:
        raise PermissionError("memory exchange bundle ingest requires an append/proposal intent")
    if target["target_layer"] != RELATIONAL_LAYER:
        raise ValueError("GREMLIN Bestiary gateway only ingests RELATIONAL exchange targets")
    receipt = _receipt(
        beast=beast,
        layer=RELATIONAL_LAYER,
        operation=op,
        artifact_type=artifact_type,
        subject_id=target["subject_id"],
        generation_id=target["generation_id"],
        task_id=task_id,
        token=token,
    )
    result = ingest_exchange_bundle(
        runtime,
        normalized,
        priority=priority,
        consumer_id=consumer_id,
    )
    return _gateway_result(
        action="INGEST_EXCHANGE_BUNDLE",
        capability_receipt=receipt,
        result=result,
    )


def build_consolidation_route_as_beast(
    plan: Mapping[str, Any],
    *,
    beast: str,
    artifact_type: str,
    task_id: str,
    token: Mapping[str, Any],
    receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a non-mutating consolidation/retention route under RETENTION_REQUEST authority."""
    validated = validate_consolidation_plan(plan)
    capability_receipt = _receipt(
        beast=beast,
        layer="SEMANTIC",
        operation="RETENTION_REQUEST",
        artifact_type=artifact_type,
        subject_id=validated["subject_id"],
        generation_id=validated["generation_id"],
        task_id=task_id,
        token=token,
    )
    result = build_consolidation_route(validated, receipt)
    return _gateway_result(
        action="BUILD_CONSOLIDATION_ROUTE",
        capability_receipt=capability_receipt,
        result=result,
    )


__all__ = [
    "APPEND_INTENTS",
    "RELATIONAL_LAYER",
    "SCHEMA",
    "VERSION",
    "build_consolidation_route_as_beast",
    "build_hive_inventory_as_beast",
    "build_hive_manifest_as_beast",
    "export_hive_delta_as_beast",
    "ingest_exchange_bundle_as_beast",
    "ingest_exchange_envelope_as_beast",
    "plan_hive_delta_as_beast",
    "read_hive_head",
]
