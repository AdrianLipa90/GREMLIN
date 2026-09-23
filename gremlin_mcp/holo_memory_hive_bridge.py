from __future__ import annotations

from dataclasses import asdict
from hashlib import blake2b
import json
from typing import Any, Mapping

from .holo_memory import HoloMemoryIndex, remap_hive_record
from .relational_memory_encoder import encode_memory_text

SCHEMA = "GREMLIN_HOLO_MEMORY_HIVE_BRIDGE_V0_1"


class HoloMemoryBridgeError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _commit(value: Any) -> str:
    return blake2b(
        _canonical(value),
        digest_size=32,
        person=b"GRMLN-HOLO-BRDG",
    ).hexdigest()


def packet_from_payload(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if not isinstance(payload, Mapping):
        raise HoloMemoryBridgeError("Hive payload must be a mapping")

    nested = payload.get("relational_memory_packet")
    if isinstance(nested, Mapping):
        phase = nested.get("phase36")
        amp = nested.get("amplitude36")
        if (
            isinstance(phase, list)
            and len(phase) == 36
            and isinstance(amp, list)
            and len(amp) == 36
        ):
            return dict(nested), "RELATIONAL_MEMORY_PACKET"

    phase = payload.get("phase36")
    amp = payload.get("amplitude36")
    if (
        isinstance(phase, list)
        and len(phase) == 36
        and isinstance(amp, list)
        and len(amp) == 36
    ):
        return dict(payload), "PAYLOAD_PHASE36"

    for key in ("memory_text", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return encode_memory_text(value), f"TEXT_FIELD:{key}"

    raise HoloMemoryBridgeError(
        "Hive payload has no admitted 36D packet or explicit memory text"
    )


def materialize_orbital_hive(
    hive: Any,
    *,
    hex_scale: float = 9.0,
    strict: bool = True,
) -> tuple[HoloMemoryIndex, dict[str, Any]]:
    if not hasattr(hive, "flat_ring_table"):
        raise HoloMemoryBridgeError(
            "hive must expose flat_ring_table()"
        )

    records = tuple(hive.flat_ring_table())
    before = [
        {
            "record_id": str(record.record_id),
            "subject_id": str(record.subject_id),
            "version": int(record.version),
            "payload_hash": str(record.payload_hash),
        }
        for record in records
    ]

    rows = []
    mapped = []
    skipped = []

    for record in records:
        try:
            packet, source = packet_from_payload(record.payload)
        except HoloMemoryBridgeError as exc:
            if strict:
                raise
            skipped.append(
                {
                    "record_id": str(record.record_id),
                    "subject_id": str(record.subject_id),
                    "reason": str(exc),
                }
            )
            continue

        rows.append(remap_hive_record(record, packet))
        mapped.append(
            {
                "record_id": str(record.record_id),
                "subject_id": str(record.subject_id),
                "phase_source": source,
            }
        )

    index = HoloMemoryIndex(hex_scale=hex_scale)
    rebuild_commitment = index.rebuild(rows)

    after_records = tuple(hive.flat_ring_table())
    after = [
        {
            "record_id": str(record.record_id),
            "subject_id": str(record.subject_id),
            "version": int(record.version),
            "payload_hash": str(record.payload_hash),
        }
        for record in after_records
    ]

    if before != after:
        raise HoloMemoryBridgeError(
            "source Hive changed during read-only materialization"
        )

    core = {
        "schema": SCHEMA,
        "status": "MATERIALIZED_CANDIDATE",
        "source_record_count": len(records),
        "mapped_count": len(mapped),
        "skipped_count": len(skipped),
        "strict": bool(strict),
        "hex_scale": float(hex_scale),
        "mapped": mapped,
        "skipped": skipped,
        "source_head_commitment": _commit(before),
        "holo_rebuild_commitment": rebuild_commitment,
        "ledger_mutation": False,
        "source_of_truth": "ORBITAL_HIVE_MEMORY",
        "holo_authority": "DERIVED_INDEX_ONLY",
        "canon_allowed": False,
    }
    return index, {
        **core,
        "receipt_commitment": _commit(core),
    }
