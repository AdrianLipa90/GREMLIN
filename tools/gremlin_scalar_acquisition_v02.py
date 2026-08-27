from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping

OBSERVATION_SCHEMA = "GREMLIN_SCALAR_OBSERVATION_RECEIPT_V0_2"
OBSERVATION_DOMAIN = b"GREMLIN-SCALAR-OBSERVATION-RECEIPT/v0.2\x00"
LIVE_NOEMA_ROOT = Path("/dev/shm/ciel_noema")
F64_REDUCERS = {"INDEX", "MEAN", "RMS", "CIRCULAR_COHERENCE"}


class ScalarAcquisitionError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise ScalarAcquisitionError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ScalarAcquisitionError(f"{name} must be finite")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise ScalarAcquisitionError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ScalarAcquisitionError(f"{name} must be hexadecimal") from exc
    return text


def reduce_f64_le(data: bytes, reducer: str, *, index: int | None = None) -> tuple[float, dict[str, Any]]:
    if not data or len(data) % 8:
        raise ScalarAcquisitionError("f64 source must contain a non-empty whole number of float64 values")
    count = len(data) // 8
    values = struct.unpack(f"<{count}d", data)
    if not all(math.isfinite(v) for v in values):
        raise ScalarAcquisitionError("f64 source contains non-finite values")

    mode = _nonempty(reducer, "reducer").upper()
    if mode not in F64_REDUCERS:
        raise ScalarAcquisitionError(f"unsupported f64 reducer: {mode}")

    metadata: dict[str, Any] = {"reducer": mode, "sample_count": count}
    if mode == "INDEX":
        if index is None:
            raise ScalarAcquisitionError("INDEX reducer requires index")
        idx = int(index)
        if idx < 0 or idx >= count:
            raise ScalarAcquisitionError("f64 index outside source bounds")
        metadata["index"] = idx
        return float(values[idx]), metadata

    if index is not None:
        raise ScalarAcquisitionError(f"{mode} reducer does not accept index")

    if mode == "MEAN":
        return math.fsum(values) / count, metadata
    if mode == "RMS":
        return math.sqrt(math.fsum(v * v for v in values) / count), metadata

    c = math.fsum(math.cos(v) for v in values)
    s = math.fsum(math.sin(v) for v in values)
    return math.hypot(c, s) / count, metadata


def select_jsonl_f64(
    data: bytes,
    *,
    selector_key: str,
    selector_value: Any,
    field: str,
) -> tuple[float, dict[str, Any]]:
    selector = _nonempty(selector_key, "selector_key")
    field_name = _nonempty(field, "field")
    matches: list[tuple[int, Mapping[str, Any], bytes]] = []

    for line_number, raw_line in enumerate(data.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ScalarAcquisitionError(f"invalid JSONL record at line {line_number}") from exc
        if not isinstance(record, Mapping):
            raise ScalarAcquisitionError(f"JSONL record at line {line_number} must be an object")
        if record.get(selector) == selector_value:
            matches.append((line_number, record, raw_line))

    if len(matches) != 1:
        raise ScalarAcquisitionError(
            f"selector must resolve exactly one JSONL record; found {len(matches)}"
        )

    line_number, record, raw_line = matches[0]
    if field_name not in record:
        raise ScalarAcquisitionError(f"selected JSONL record has no field: {field_name}")
    value = _finite(record[field_name], field_name)
    metadata = {
        "selector_key": selector,
        "selector_value": selector_value,
        "field": field_name,
        "line_number": line_number,
        "record_sha256": _sha256(raw_line),
    }
    return value, metadata


def _assert_live_noema(root: str | Path) -> tuple[Path, dict[str, Any]]:
    requested = Path(root)
    if requested != LIVE_NOEMA_ROOT:
        raise ScalarAcquisitionError("NOEMA acquisition root is fixed to /dev/shm/ciel_noema")

    if not requested.is_dir():
        raise ScalarAcquisitionError("live NOEMA surface is absent")

    try:
        binding = (requested / "ciel_binding_status").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ScalarAcquisitionError("cannot read live NOEMA binding status") from exc
    if binding != "ACTIVE":
        raise ScalarAcquisitionError("live NOEMA binding is not ACTIVE")

    try:
        tether_bytes = (requested / "tether_runtime_status.json").read_bytes()
        tether = json.loads(tether_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ScalarAcquisitionError("cannot read live NOEMA tether status") from exc
    if not isinstance(tether, Mapping) or tether.get("status") != "ACTIVE":
        raise ScalarAcquisitionError("live NOEMA tether is not ACTIVE")

    try:
        phi_bytes = (requested / "phi").read_bytes()
    except OSError as exc:
        raise ScalarAcquisitionError("cannot read live NOEMA phi") from exc
    if len(phi_bytes) != 36 * 8:
        raise ScalarAcquisitionError("live NOEMA phi must be exactly 36 little-endian float64 values")
    phi = struct.unpack("<36d", phi_bytes)
    if not all(math.isfinite(v) for v in phi):
        raise ScalarAcquisitionError("live NOEMA phi contains non-finite values")

    tick_path = requested / "tick"
    tick_sha = _sha256(tick_path.read_bytes()) if tick_path.is_file() else None
    return requested, {
        "root": str(requested),
        "binding_status": binding,
        "tether_status": "ACTIVE",
        "phi_sha256": _sha256(phi_bytes),
        "tether_status_sha256": _sha256(tether_bytes),
        "tick_sha256": tick_sha,
        "live_surface_witness": True,
    }


def _resolve_live_source(root: Path, relative_path: str) -> tuple[Path, str]:
    rel = Path(_nonempty(relative_path, "relative_path"))
    if rel.is_absolute() or ".." in rel.parts:
        raise ScalarAcquisitionError("source path must be a contained relative live-NOEMA path")
    candidate = root / rel
    if not candidate.is_file():
        raise ScalarAcquisitionError(f"live NOEMA source is absent: {relative_path}")
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_root not in resolved_candidate.parents:
        raise ScalarAcquisitionError("source path escaped live NOEMA root")
    return resolved_candidate, rel.as_posix()


def _seal_receipt(
    *,
    observation_name: str,
    value: Any,
    scale_id: str,
    source_ref: str,
    epistemic_status: str,
    semantic_adapter_id: str,
    semantic_adapter_status: str,
    producer: Mapping[str, Any],
    live_witness: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "schema": OBSERVATION_SCHEMA,
        "observation_name": _nonempty(observation_name, "observation_name"),
        "value_f64_hex": _finite(value, "observation_value").hex(),
        "scale_id": _nonempty(scale_id, "scale_id"),
        "source_ref": _nonempty(source_ref, "source_ref"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "semantic_adapter": {
            "adapter_id": _nonempty(semantic_adapter_id, "semantic_adapter_id"),
            "status": _nonempty(semantic_adapter_status, "semantic_adapter_status"),
        },
        "producer": dict(producer),
        "live_noema_witness": dict(live_witness),
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "OBSERVATION_ACQUIRED",
    }
    commitment = hashlib.blake2b(OBSERVATION_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "observation_receipt_commitment": commitment}


def acquire_noema_f64_observation(
    *,
    observation_name: str,
    relative_path: str,
    reducer: str,
    scale_id: str,
    epistemic_status: str,
    semantic_adapter_id: str,
    semantic_adapter_status: str = "CANDIDATE",
    index: int | None = None,
    root: str | Path = LIVE_NOEMA_ROOT,
) -> dict[str, Any]:
    live_root, witness = _assert_live_noema(root)
    source_path, rel = _resolve_live_source(live_root, relative_path)
    source_bytes = source_path.read_bytes()
    value, extraction = reduce_f64_le(source_bytes, reducer, index=index)
    producer = {
        "producer_kind": "NOEMA_LIVE_F64",
        "source_path": rel,
        "source_sha256": _sha256(source_bytes),
        "source_size": len(source_bytes),
        "source_format": "little_endian_float64",
        "extraction": extraction,
    }
    source_ref = f"noema-live://{rel}#{extraction['reducer']}"
    if "index" in extraction:
        source_ref += f":{extraction['index']}"
    return _seal_receipt(
        observation_name=observation_name,
        value=value,
        scale_id=scale_id,
        source_ref=source_ref,
        epistemic_status=epistemic_status,
        semantic_adapter_id=semantic_adapter_id,
        semantic_adapter_status=semantic_adapter_status,
        producer=producer,
        live_witness=witness,
    )


def acquire_ciel_jsonl_observation(
    *,
    observation_name: str,
    relative_path: str,
    selector_key: str,
    selector_value: Any,
    field: str,
    scale_id: str,
    epistemic_status: str,
    semantic_adapter_id: str,
    semantic_adapter_status: str = "CANDIDATE",
    root: str | Path = LIVE_NOEMA_ROOT,
) -> dict[str, Any]:
    live_root, witness = _assert_live_noema(root)
    source_path, rel = _resolve_live_source(live_root, relative_path)
    if not rel.startswith("phasenav/") or not rel.endswith(".noema.jsonl"):
        raise ScalarAcquisitionError("CIEL acquisition requires a live phasenav/*.noema.jsonl source")
    source_bytes = source_path.read_bytes()
    value, extraction = select_jsonl_f64(
        source_bytes,
        selector_key=selector_key,
        selector_value=selector_value,
        field=field,
    )
    producer = {
        "producer_kind": "CIEL_NOEMA_JSONL_FIELD",
        "source_path": rel,
        "source_sha256": _sha256(source_bytes),
        "source_size": len(source_bytes),
        "source_format": "utf8_jsonl",
        "extraction": extraction,
    }
    source_ref = (
        f"ciel-noema://{rel}"
        f"?{extraction['selector_key']}={selector_value!s}#{extraction['field']}"
    )
    return _seal_receipt(
        observation_name=observation_name,
        value=value,
        scale_id=scale_id,
        source_ref=source_ref,
        epistemic_status=epistemic_status,
        semantic_adapter_id=semantic_adapter_id,
        semantic_adapter_status=semantic_adapter_status,
        producer=producer,
        live_witness=witness,
    )


def validate_scalar_observation_receipt(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("schema") != OBSERVATION_SCHEMA:
        raise ScalarAcquisitionError("unsupported scalar observation receipt schema")
    _nonempty(receipt.get("observation_name"), "observation_name")
    _finite(float.fromhex(str(receipt.get("value_f64_hex"))), "observation_value")
    for key in ("scale_id", "source_ref", "epistemic_status"):
        _nonempty(receipt.get(key), key)

    adapter = receipt.get("semantic_adapter")
    if not isinstance(adapter, Mapping):
        raise ScalarAcquisitionError("semantic_adapter must be a mapping")
    _nonempty(adapter.get("adapter_id"), "semantic_adapter.adapter_id")
    _nonempty(adapter.get("status"), "semantic_adapter.status")

    producer = receipt.get("producer")
    if not isinstance(producer, Mapping):
        raise ScalarAcquisitionError("producer must be a mapping")
    kind = producer.get("producer_kind")
    if kind not in {"NOEMA_LIVE_F64", "CIEL_NOEMA_JSONL_FIELD"}:
        raise ScalarAcquisitionError("unsupported scalar observation producer")
    _nonempty(producer.get("source_path"), "producer.source_path")
    _hash64(producer.get("source_sha256"), "producer.source_sha256")
    if int(producer.get("source_size", 0)) <= 0:
        raise ScalarAcquisitionError("producer.source_size must be positive")
    if not isinstance(producer.get("extraction"), Mapping):
        raise ScalarAcquisitionError("producer.extraction must be a mapping")

    witness = receipt.get("live_noema_witness")
    if not isinstance(witness, Mapping):
        raise ScalarAcquisitionError("live_noema_witness must be a mapping")
    if witness.get("root") != str(LIVE_NOEMA_ROOT):
        raise ScalarAcquisitionError("receipt is not bound to the canonical live NOEMA root")
    if witness.get("binding_status") != "ACTIVE" or witness.get("tether_status") != "ACTIVE":
        raise ScalarAcquisitionError("receipt does not witness ACTIVE NOEMA binding/tether")
    if witness.get("live_surface_witness") is not True:
        raise ScalarAcquisitionError("receipt lacks live surface witness")
    _hash64(witness.get("phi_sha256"), "live_noema_witness.phi_sha256")
    _hash64(witness.get("tether_status_sha256"), "live_noema_witness.tether_status_sha256")

    if receipt.get("production_runtime_write") is not False:
        raise ScalarAcquisitionError("scalar acquisition cannot grant production runtime write")
    if receipt.get("execution_admitted") is not False or receipt.get("canon_allowed") is not False:
        raise ScalarAcquisitionError("scalar acquisition authority boundary violated")
    if receipt.get("status") != "OBSERVATION_ACQUIRED":
        raise ScalarAcquisitionError("wrong scalar acquisition status")

    supplied = _hash64(receipt.get("observation_receipt_commitment"), "observation_receipt_commitment")
    core = dict(receipt)
    core.pop("observation_receipt_commitment", None)
    expected = hashlib.blake2b(OBSERVATION_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise ScalarAcquisitionError("scalar observation receipt commitment mismatch")
    return True


def scalar_mapping_from_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    validate_scalar_observation_receipt(receipt)
    return {
        "value": float.fromhex(str(receipt["value_f64_hex"])),
        "scale_id": str(receipt["scale_id"]),
        "source_ref": str(receipt["source_ref"]),
        "epistemic_status": str(receipt["epistemic_status"]),
        "observation_receipt_commitment": str(receipt["observation_receipt_commitment"]),
    }


ACQUIRED_KAKU_SCHEMA = "GREMLIN_ACQUIRED_KAKU_SCALAR_PACKET_V0_2"
ACQUIRED_KAKU_DOMAIN = b"GREMLIN-ACQUIRED-KAKU-SCALAR-PACKET/v0.2\x00"
ACQUIRED_RADICAL_SCHEMA = "GREMLIN_ACQUIRED_RADICAL_SCALAR_ADMISSION_V0_2"
ACQUIRED_RADICAL_DOMAIN = b"GREMLIN-ACQUIRED-RADICAL-SCALAR-ADMISSION/v0.2\x00"

KAKU_SCALAR_NAMES = ("valuation", "affect", "intention_alignment", "epistemic_support")
RADICAL_SCALAR_NAMES = ("ethical_integrity", "contradiction_load", "recursive_integrity")


def _require_named_receipts(
    receipts: Mapping[str, Mapping[str, Any]],
    names: tuple[str, ...],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(receipts, Mapping) or set(receipts) != set(names):
        raise ScalarAcquisitionError(f"exact observation receipt set required: {', '.join(names)}")
    out: dict[str, Mapping[str, Any]] = {}
    for name in names:
        receipt = receipts[name]
        validate_scalar_observation_receipt(receipt)
        if receipt.get("observation_name") != name:
            raise ScalarAcquisitionError(
                f"observation receipt name mismatch for {name}: {receipt.get('observation_name')}"
            )
        out[name] = receipt
    return out


def build_acquired_kaku_scalar_packet(
    *,
    kaku_id: str,
    operator_kind: str,
    direction: str,
    polarity: Any,
    role: str,
    source_binding: str,
    target_binding: str,
    observation_receipts: Mapping[str, Mapping[str, Any]],
    evidence_refs: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    from tools.gremlin_kaku_radical_scalar_plane_v01 import build_kaku_scalar_packet

    receipts = _require_named_receipts(observation_receipts, KAKU_SCALAR_NAMES)
    receipt_refs = [
        f"scalar-observation:{receipts[name]['observation_receipt_commitment']}"
        for name in KAKU_SCALAR_NAMES
    ]
    legacy = build_kaku_scalar_packet(
        kaku_id=kaku_id,
        operator_kind=operator_kind,
        direction=direction,
        polarity=polarity,
        role=role,
        source_binding=source_binding,
        target_binding=target_binding,
        valuation=scalar_mapping_from_receipt(receipts["valuation"]),
        affect=scalar_mapping_from_receipt(receipts["affect"]),
        intention_alignment=scalar_mapping_from_receipt(receipts["intention_alignment"]),
        epistemic_support=scalar_mapping_from_receipt(receipts["epistemic_support"]),
        evidence_refs=[*evidence_refs, *receipt_refs],
    )
    core = {
        "schema": ACQUIRED_KAKU_SCHEMA,
        "kaku_packet_v01": legacy,
        "observation_receipts": {name: dict(receipts[name]) for name in KAKU_SCALAR_NAMES},
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "KAKU_SCALARS_ACQUIRED",
    }
    commitment = hashlib.blake2b(ACQUIRED_KAKU_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    return {**core, "acquired_kaku_commitment": commitment}


def validate_acquired_kaku_scalar_packet(record: Mapping[str, Any]) -> bool:
    from tools.gremlin_kaku_radical_scalar_plane_v01 import validate_kaku_scalar_packet

    if record.get("schema") != ACQUIRED_KAKU_SCHEMA:
        raise ScalarAcquisitionError("unsupported acquired KAKU schema")
    legacy = record.get("kaku_packet_v01")
    if not isinstance(legacy, Mapping):
        raise ScalarAcquisitionError("kaku_packet_v01 must be a mapping")
    validate_kaku_scalar_packet(legacy)

    receipts = _require_named_receipts(record.get("observation_receipts"), KAKU_SCALAR_NAMES)
    expected_refs = {
        f"scalar-observation:{receipts[name]['observation_receipt_commitment']}"
        for name in KAKU_SCALAR_NAMES
    }
    if not expected_refs.issubset(set(legacy.get("evidence_refs", []))):
        raise ScalarAcquisitionError("legacy KAKU packet does not bind all observation receipts")

    for name in KAKU_SCALAR_NAMES:
        scalar = legacy["scalars"][name]
        receipt = receipts[name]
        if scalar["value_f64_hex"] != receipt["value_f64_hex"]:
            raise ScalarAcquisitionError(f"{name} value differs from acquired observation")
        for key in ("scale_id", "source_ref", "epistemic_status"):
            if scalar[key] != receipt[key]:
                raise ScalarAcquisitionError(f"{name}.{key} differs from acquired observation")

    if record.get("production_runtime_write") is not False:
        raise ScalarAcquisitionError("acquired KAKU cannot grant production runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise ScalarAcquisitionError("acquired KAKU authority boundary violated")
    if record.get("status") != "KAKU_SCALARS_ACQUIRED":
        raise ScalarAcquisitionError("wrong acquired KAKU status")

    supplied = _hash64(record.get("acquired_kaku_commitment"), "acquired_kaku_commitment")
    core = dict(record)
    core.pop("acquired_kaku_commitment", None)
    expected = hashlib.blake2b(ACQUIRED_KAKU_DOMAIN + _canonical(core), digest_size=32).hexdigest()
    if supplied != expected:
        raise ScalarAcquisitionError("acquired KAKU commitment mismatch")
    return True


def build_acquired_radical_scalar_admission(
    *,
    radical_id: str,
    candidate_id: str,
    ordered_acquired_kaku_packets: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    relation_ids: list[str] | tuple[str, ...],
    radical_observation_receipts: Mapping[str, Mapping[str, Any]],
    consent_gate: Mapping[str, Any],
    reversibility_gate: Mapping[str, Any],
    no_go_gate: Mapping[str, Any],
    evidence_refs: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    from tools.gremlin_kaku_radical_scalar_plane_v01 import build_radical_scalar_admission

    if not ordered_acquired_kaku_packets:
        raise ScalarAcquisitionError("acquired Radical requires at least one acquired KAKU")
    acquired_kaku = []
    legacy_packets = []
    for item in ordered_acquired_kaku_packets:
        validate_acquired_kaku_scalar_packet(item)
        acquired_kaku.append(dict(item))
        legacy_packets.append(item["kaku_packet_v01"])

    receipts = _require_named_receipts(radical_observation_receipts, RADICAL_SCALAR_NAMES)
    receipt_refs = [
        f"scalar-observation:{receipts[name]['observation_receipt_commitment']}"
        for name in RADICAL_SCALAR_NAMES
    ]
    kaku_refs = [
        f"acquired-kaku:{item['acquired_kaku_commitment']}"
        for item in acquired_kaku
    ]
    legacy = build_radical_scalar_admission(
        radical_id=radical_id,
        candidate_id=candidate_id,
        ordered_kaku_packets=legacy_packets,
        relation_ids=relation_ids,
        ethical_integrity=scalar_mapping_from_receipt(receipts["ethical_integrity"]),
        consent_gate=consent_gate,
        reversibility_gate=reversibility_gate,
        no_go_gate=no_go_gate,
        contradiction_load=scalar_mapping_from_receipt(receipts["contradiction_load"]),
        recursive_integrity=scalar_mapping_from_receipt(receipts["recursive_integrity"]),
        evidence_refs=[*evidence_refs, *receipt_refs, *kaku_refs],
    )
    core = {
        "schema": ACQUIRED_RADICAL_SCHEMA,
        "radical_admission_v01": legacy,
        "ordered_acquired_kaku": acquired_kaku,
        "radical_observation_receipts": {
            name: dict(receipts[name]) for name in RADICAL_SCALAR_NAMES
        },
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": (
            "ACQUIRED_PRE_VECTOR_ADMITTED"
            if legacy["status"] == "PRE_VECTOR_ADMITTED"
            else "ACQUIRED_PRE_VECTOR_BLOCKED"
        ),
    }
    commitment = hashlib.blake2b(
        ACQUIRED_RADICAL_DOMAIN + _canonical(core), digest_size=32
    ).hexdigest()
    return {**core, "acquired_radical_commitment": commitment}


def validate_acquired_radical_scalar_admission(record: Mapping[str, Any]) -> bool:
    from tools.gremlin_kaku_radical_scalar_plane_v01 import validate_radical_scalar_admission

    if record.get("schema") != ACQUIRED_RADICAL_SCHEMA:
        raise ScalarAcquisitionError("unsupported acquired Radical schema")
    legacy = record.get("radical_admission_v01")
    if not isinstance(legacy, Mapping):
        raise ScalarAcquisitionError("radical_admission_v01 must be a mapping")
    validate_radical_scalar_admission(legacy)

    ordered = record.get("ordered_acquired_kaku")
    if not isinstance(ordered, list) or not ordered:
        raise ScalarAcquisitionError("ordered acquired KAKU lineage required")
    for item in ordered:
        validate_acquired_kaku_scalar_packet(item)

    receipts = _require_named_receipts(
        record.get("radical_observation_receipts"), RADICAL_SCALAR_NAMES
    )
    expected_refs = {
        *(f"scalar-observation:{receipts[name]['observation_receipt_commitment']}"
          for name in RADICAL_SCALAR_NAMES),
        *(f"acquired-kaku:{item['acquired_kaku_commitment']}" for item in ordered),
    }
    if not expected_refs.issubset(set(legacy.get("evidence_refs", []))):
        raise ScalarAcquisitionError("legacy Radical does not bind complete acquisition lineage")

    expected_status = (
        "ACQUIRED_PRE_VECTOR_ADMITTED"
        if legacy["status"] == "PRE_VECTOR_ADMITTED"
        else "ACQUIRED_PRE_VECTOR_BLOCKED"
    )
    if record.get("status") != expected_status:
        raise ScalarAcquisitionError("acquired Radical status mismatch")
    if record.get("production_runtime_write") is not False:
        raise ScalarAcquisitionError("acquired Radical cannot grant production runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise ScalarAcquisitionError("acquired Radical authority boundary violated")

    supplied = _hash64(record.get("acquired_radical_commitment"), "acquired_radical_commitment")
    core = dict(record)
    core.pop("acquired_radical_commitment", None)
    expected = hashlib.blake2b(
        ACQUIRED_RADICAL_DOMAIN + _canonical(core), digest_size=32
    ).hexdigest()
    if supplied != expected:
        raise ScalarAcquisitionError("acquired Radical commitment mismatch")
    return True
