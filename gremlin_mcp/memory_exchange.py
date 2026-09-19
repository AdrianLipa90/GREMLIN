from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .hive_authority import HiveAuthorityRuntime

SCHEMA = "GREMLIN_MEMORY_INFORMATION_EXCHANGE_V0_1"
VERSION = "0.1.0"
PHASENAV_SCHEMA = "PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1"
PHASENAV_ACK_SCHEMA = "PHASENAV_MEMORY_INFORMATION_EXCHANGE_ACK_V0_1"
EPISTEMIC = "CHYBA"
AUTHORITY = "SHARED_COGNITION_ONLY"
LAYERS = ("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL")
TOL = 1.0e-9


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("memory-exchange values must be finite JSON data") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _strict_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    return value


def _finite(value: Any, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def _refs(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be a sequence")
    out: list[str] = []
    for item in value:
        text = _text(item, field)
        if text not in out:
            out.append(text)
    return tuple(sorted(out))


def _layer(value: Any, field: str) -> str:
    layer = _text(value, field).upper()
    if layer not in LAYERS:
        raise ValueError(f"unsupported {field}")
    return layer


def _transport(edges: Sequence[float]) -> tuple[tuple[float, ...], float, float, float]:
    values = tuple(_finite(value, "route_edge_potentials") for value in edges)
    theta = math.fsum(values)
    real = math.cos(theta)
    imag = math.sin(theta)
    phase = math.atan2(imag, real)
    return values, real, imag, phase


def validate_exchange_envelope(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute all PhaseNav memory-exchange commitments fail-closed."""
    if not isinstance(packet, Mapping):
        raise ValueError("packet must be a mapping")
    row = dict(packet)
    if row.get("schema") != PHASENAV_SCHEMA:
        raise ValueError("unsupported memory-exchange schema")
    if row.get("version") != VERSION:
        raise ValueError("unsupported memory-exchange version")
    if row.get("epistemic") != EPISTEMIC:
        raise ValueError("memory-exchange packet must remain epistemic=CHYBA")
    if row.get("authority") != AUTHORITY:
        raise ValueError("memory-exchange packet must remain SHARED_COGNITION_ONLY")
    if row.get("canon_allowed") is not False:
        raise ValueError("memory-exchange packet must remain canon_allowed=false")

    subject = _text(row.get("subject_id"), "subject_id")
    producer = _text(row.get("producer_id"), "producer_id")
    generation = _text(row.get("generation_id"), "generation_id")
    sequence = _strict_int(row.get("sequence"), "sequence", minimum=0)
    source = _layer(row.get("source_layer"), "source_layer")
    target = _layer(row.get("target_layer"), "target_layer")

    payload = row.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    payload_dict = dict(payload)
    payload_sha = _sha256(payload_dict)
    if row.get("payload_sha256") != payload_sha:
        raise ValueError("payload_sha256 mismatch")

    parents = _refs(row.get("parent_envelope_ids", ()), "parent_envelope_ids")
    provenance = _refs(row.get("provenance", ()), "provenance")
    dependencies = _refs(row.get("dependencies", ()), "dependencies")

    edge_raw = row.get("route_edge_potentials", ())
    if not isinstance(edge_raw, Sequence) or isinstance(edge_raw, (str, bytes)):
        raise ValueError("route_edge_potentials must be a sequence")
    edges, real, imag, phase = _transport(edge_raw)

    hop_count = _strict_int(row.get("hop_count"), "hop_count", minimum=0)
    hop_limit = _strict_int(row.get("hop_limit"), "hop_limit", minimum=1)
    if hop_count > hop_limit:
        raise ValueError("hop_count cannot exceed hop_limit")

    transport = row.get("transport")
    if not isinstance(transport, Mapping):
        raise ValueError("transport must be a mapping")
    declared_real = _finite(transport.get("real"), "transport.real")
    declared_imag = _finite(transport.get("imag"), "transport.imag")
    declared_phase = _finite(transport.get("phase"), "transport.phase")
    declared_modulus = _finite(transport.get("modulus"), "transport.modulus")
    if abs(declared_real - real) > TOL or abs(declared_imag - imag) > TOL:
        raise ValueError("transport complex value does not match route_edge_potentials")
    phase_error = math.atan2(
        math.sin(declared_phase - phase),
        math.cos(declared_phase - phase),
    )
    if abs(phase_error) > TOL:
        raise ValueError("transport phase does not match route_edge_potentials")
    if abs(declared_modulus - 1.0) > TOL or abs(math.hypot(declared_real, declared_imag) - 1.0) > TOL:
        raise ValueError("memory-exchange U(1) transport must have unit modulus")

    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("claims must be a mapping")
    if claims.get("content_addressed_payload") is not True:
        raise ValueError("content_addressed_payload claim must be true")
    if claims.get("causal_lineage") is not True:
        raise ValueError("causal_lineage claim must be true")
    if claims.get("computational_u1_route_phase") is not True:
        raise ValueError("computational_u1_route_phase claim must be true")
    for key in ("physical_nonlocal_signalling", "physical_channel_identified", "canon_promoted"):
        if claims.get(key) is not False:
            raise ValueError(f"unsupported claim must remain false: {key}")

    core = {
        "schema": PHASENAV_SCHEMA,
        "version": VERSION,
        "subject_id": subject,
        "producer_id": producer,
        "generation_id": generation,
        "sequence": sequence,
        "source_layer": source,
        "target_layer": target,
        "payload_sha256": payload_sha,
        "parent_envelope_ids": list(parents),
        "provenance": list(provenance),
        "dependencies": list(dependencies),
        "route_edge_potentials": list(edges),
        "hop_count": hop_count,
        "hop_limit": hop_limit,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    envelope_id = "px:" + _sha256(core)
    if row.get("envelope_id") != envelope_id:
        raise ValueError("envelope_id commitment mismatch")

    return {
        "schema": PHASENAV_SCHEMA,
        "version": VERSION,
        "envelope_id": envelope_id,
        "subject_id": subject,
        "producer_id": producer,
        "generation_id": generation,
        "sequence": sequence,
        "source_layer": source,
        "target_layer": target,
        "payload": payload_dict,
        "payload_sha256": payload_sha,
        "parent_envelope_ids": list(parents),
        "provenance": list(provenance),
        "dependencies": list(dependencies),
        "route_edge_potentials": list(edges),
        "transport": {
            "real": real,
            "imag": imag,
            "phase": phase,
            "modulus": 1.0,
        },
        "hop_count": hop_count,
        "hop_limit": hop_limit,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
        "claims": {
            "content_addressed_payload": True,
            "causal_lineage": True,
            "computational_u1_route_phase": True,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }


def build_exchange_ack(
    envelope: Mapping[str, Any],
    *,
    consumer_id: str,
    outcome: str = "ACCEPTED",
    reason_code: str = "HIVE_INGESTED",
) -> dict[str, Any]:
    normalized = validate_exchange_envelope(envelope)
    consumer = _text(consumer_id, "consumer_id")
    status = _text(outcome, "outcome").upper()
    if status not in {"ACCEPTED", "DUPLICATE", "QUARANTINED", "REJECTED"}:
        raise ValueError("unsupported exchange outcome")
    reason = _text(reason_code, "reason_code")
    core = {
        "schema": PHASENAV_ACK_SCHEMA,
        "version": VERSION,
        "envelope_id": normalized["envelope_id"],
        "payload_sha256": normalized["payload_sha256"],
        "consumer_id": consumer,
        "outcome": status,
        "reason_code": reason,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "ack_id": "pxa:" + _sha256(core),
    }


def ingest_exchange_envelope(
    runtime: HiveAuthorityRuntime,
    envelope: Mapping[str, Any],
    *,
    priority: float = 0.82,
    consumer_id: str = "GREMLIN-HIVE",
) -> dict[str, Any]:
    """Ingest one PhaseNav envelope into RELATIONAL Hive memory.

    The operation is idempotent and never sets closure gates or latches. Causal
    parents must already exist in the same Hive authority surface.
    """
    normalized = validate_exchange_envelope(envelope)
    if normalized["target_layer"] != "RELATIONAL":
        raise ValueError("GREMLIN Hive exchange ingest requires target_layer=RELATIONAL")

    p = _finite(priority, "priority")
    if not 0.0 <= p <= 1.0:
        raise ValueError("priority must be in [0,1]")

    for parent_id in normalized["parent_envelope_ids"]:
        try:
            parent = runtime.head(f"exchange:{parent_id}")
        except KeyError as exc:
            raise RuntimeError("orphan memory-exchange ingest: parent not present in Hive") from exc
        parent_payload = dict(parent.payload)
        if parent_payload.get("generation_id") != normalized["generation_id"]:
            raise RuntimeError("memory-exchange parent generation mismatch")
        if int(parent_payload.get("sequence", -1)) >= normalized["sequence"]:
            raise RuntimeError("memory-exchange child sequence must exceed parent sequence")

    hive_subject = f"exchange:{normalized['envelope_id']}"
    hive_payload = {
        "kind": "PHASENAV_MEMORY_INFORMATION_EXCHANGE",
        "envelope_id": normalized["envelope_id"],
        "subject_id": normalized["subject_id"],
        "producer_id": normalized["producer_id"],
        "generation_id": normalized["generation_id"],
        "sequence": normalized["sequence"],
        "source_layer": normalized["source_layer"],
        "target_layer": normalized["target_layer"],
        "payload_sha256": normalized["payload_sha256"],
        "payload": normalized["payload"],
        "transport": normalized["transport"],
        "hop_count": normalized["hop_count"],
        "hop_limit": normalized["hop_limit"],
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    provenance = tuple(sorted(set(
        normalized["provenance"]
        + [
            f"envelope:{normalized['envelope_id']}",
            f"payload:{normalized['payload_sha256']}",
        ]
    )))
    dependencies = tuple(sorted(set(
        normalized["dependencies"]
        + [f"exchange:{parent_id}" for parent_id in normalized["parent_envelope_ids"]]
    )))

    record, created = runtime.place_idempotent(
        subject_id=hive_subject,
        payload=hive_payload,
        priority=p,
        semantic_key=f"memory-exchange/{normalized['subject_id']}",
        relation_phase=float(normalized["transport"]["phase"]),
        provenance=provenance,
        dependencies=dependencies,
    )

    ack = build_exchange_ack(
        normalized,
        consumer_id=consumer_id,
        outcome="ACCEPTED",
        reason_code="HIVE_INGESTED",
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "INGESTED",
        "created": created,
        "envelope_id": normalized["envelope_id"],
        "payload_sha256": normalized["payload_sha256"],
        "hive_subject_id": hive_subject,
        "hive_record_id": record.record_id,
        "hive_state": record.state,
        "hive_gates": asdict(record.gates),
        "ack": ack,
        "automatic_latch": False,
        "authority": AUTHORITY,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "claims": {
            "shared_cognition_ingest": True,
            "physical_nonlocal_signalling": False,
            "physical_channel_identified": False,
            "canon_promoted": False,
        },
    }


__all__ = [
    "AUTHORITY",
    "EPISTEMIC",
    "LAYERS",
    "PHASENAV_ACK_SCHEMA",
    "PHASENAV_SCHEMA",
    "SCHEMA",
    "VERSION",
    "build_exchange_ack",
    "ingest_exchange_envelope",
    "validate_exchange_envelope",
]
