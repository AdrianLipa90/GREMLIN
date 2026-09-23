from __future__ import annotations

from hashlib import blake2b
import json
import math
from typing import Any, Mapping, Sequence

from .holo_memory import HoloMemoryIndex
from .relational_memory_encoder import encode_memory_text

SCHEMA = "GREMLIN_HOLO_MEMORY_NOEMA_TRACE_BRIDGE_V0_1"


class NoemaTraceBridgeError(RuntimeError):
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
        person=b"GRMLN-HOLO-NOEMA",
    ).hexdigest()


def _strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        if value.strip():
            out.append(value.strip())
    elif isinstance(value, Mapping):
        for key in sorted(value):
            if key in {
                "source_hashes",
                "unknown_fields",
                "phase_binding",
                "provenance",
            }:
                continue
            out.extend(_strings(value[key]))
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        for item in value:
            out.extend(_strings(item))
    return out


def _exact_packet(trace: Mapping[str, Any]) -> dict[str, Any] | None:
    phase = trace.get("phase36")
    amp = trace.get("amplitude36")
    if (
        isinstance(phase, Sequence)
        and not isinstance(phase, (str, bytes, bytearray))
        and len(phase) == 36
        and isinstance(amp, Sequence)
        and not isinstance(amp, (str, bytes, bytearray))
        and len(amp) == 36
    ):
        p = [float(x) for x in phase]
        a = [float(x) for x in amp]
        if not all(math.isfinite(x) for x in p + a):
            raise NoemaTraceBridgeError(
                "exact phase36/amplitude36 contains non-finite values"
            )
        if any(x < 0 for x in a):
            raise NoemaTraceBridgeError(
                "exact amplitude36 contains a negative value"
            )
        return {
            "phase36": p,
            "amplitude36": a,
            "semantic_commitment": str(
                trace.get("semantic_commitment")
                or _commit({"phase36": p, "amplitude36": a})
            ),
        }
    return None


def trace_semantic_text(trace: Mapping[str, Any]) -> str:
    if str(trace.get("schema", "")).strip() != "NOEMA_MEMORY_TRACE_V1":
        raise NoemaTraceBridgeError(
            "expected NOEMA_MEMORY_TRACE_V1"
        )

    content = trace.get("content")
    if not isinstance(content, Mapping):
        raise NoemaTraceBridgeError("trace content must be a mapping")

    pieces: list[str] = []

    layer = str(trace.get("layer", "")).strip()
    if layer:
        pieces.append(layer)

    binding = content.get("binding_semantics")
    if isinstance(binding, Mapping):
        pieces.extend(_strings(binding))

    source_fragments = content.get("source_fragments")
    if isinstance(source_fragments, Mapping):
        pieces.extend(_strings(source_fragments))

    tags = trace.get("semantic_tags")
    if isinstance(tags, Sequence) and not isinstance(
        tags, (str, bytes, bytearray)
    ):
        pieces.extend(
            str(x).strip()
            for x in tags
            if isinstance(x, str) and x.strip()
        )

    text = " | ".join(dict.fromkeys(pieces))
    if not text:
        raise NoemaTraceBridgeError(
            "trace exposes no admitted semantic body"
        )
    return text


def packet_from_noema_trace(
    trace: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    exact = _exact_packet(trace)
    phase_binding = trace.get("phase_binding")
    phase_status = None
    if isinstance(phase_binding, Mapping):
        phase_status = phase_binding.get("status")

    trace_id = str(trace.get("trace_id", "")).strip()
    trace_sha256 = str(trace.get("trace_sha256", "")).strip()
    epistemic = str(trace.get("epistemic_state", "")).strip()

    if exact is not None:
        provenance = {
            "phase_source": "EXACT_SOURCE_36D",
            "native_phase_binding_status": phase_status,
            "exact_legacy_phase_recovered": True,
            "trace_id": trace_id,
            "trace_sha256": trace_sha256,
            "epistemic_state": epistemic,
            "hash_used_as_semantic_coordinate": False,
        }
        return exact, provenance

    text = trace_semantic_text(trace)
    packet = encode_memory_text(text)
    provenance = {
        "phase_source": (
            "DERIVED_FROM_RECEIPTED_TRACE_TEXT/"
            "GREMLIN_RELATIONAL_MEMORY_ENCODER_V0_1"
        ),
        "native_phase_binding_status": phase_status,
        "exact_legacy_phase_recovered": False,
        "trace_id": trace_id,
        "trace_sha256": trace_sha256,
        "epistemic_state": epistemic,
        "semantic_text_commitment": packet["raw_text_commitment"],
        "hash_used_as_semantic_coordinate": False,
    }
    return packet, provenance


def materialize_noema_traces(
    traces: Sequence[Mapping[str, Any]],
    *,
    semantic_orbit_map: Mapping[str, str] | None = None,
    hex_scale: float = 9.0,
) -> tuple[HoloMemoryIndex, dict[str, Any]]:
    if not traces:
        raise NoemaTraceBridgeError("at least one trace is required")

    index = HoloMemoryIndex(hex_scale=hex_scale)
    rows = []
    origins = []

    for trace in traces:
        trace_id = str(trace.get("trace_id", "")).strip()
        trace_sha = str(trace.get("trace_sha256", "")).strip()
        layer = str(trace.get("layer", "")).strip()
        if not trace_id or not trace_sha or not layer:
            raise NoemaTraceBridgeError(
                "trace_id, trace_sha256 and layer are required"
            )

        packet, provenance = packet_from_noema_trace(trace)

        if semantic_orbit_map is None:
            semantic_orbit_id = None
            orbit_source = "SEMANTIC_ORBIT_UNBOUND"
        else:
            if trace_id not in semantic_orbit_map:
                raise NoemaTraceBridgeError(
                    f"semantic_orbit_map missing trace: {trace_id}"
                )
            semantic_orbit_id = str(
                semantic_orbit_map[trace_id]
            ).strip()
            if not semantic_orbit_id:
                raise NoemaTraceBridgeError(
                    "semantic orbit id must be non-empty"
                )
            orbit_source = "EXPLICIT_SEMANTIC_ORBIT_MAP"

        ledger_record_id = f"noema-trace:{trace_sha}"
        rows.append(
            {
                "memory_id": trace_id,
                "ledger_record_id": ledger_record_id,
                "packet": packet,
                "priority_orbit_index": 0,
                "semantic_orbit_id": semantic_orbit_id,
                "priority": 0.5,
            }
        )
        origins.append(
            {
                "trace_id": trace_id,
                "layer": layer,
                "trace_sha256": trace_sha,
                "phase_source": provenance["phase_source"],
                "native_phase_binding_status": provenance[
                    "native_phase_binding_status"
                ],
                "exact_legacy_phase_recovered": provenance[
                    "exact_legacy_phase_recovered"
                ],
                "semantic_orbit_id": semantic_orbit_id,
                "semantic_orbit_source": orbit_source,
            }
        )

    rebuild_commitment = index.rebuild(rows)
    core = {
        "schema": SCHEMA,
        "status": "MATERIALIZED_DERIVED_INDEX",
        "trace_count": len(traces),
        "mapped_count": index.count,
        "origins": origins,
        "hex_scale": float(hex_scale),
        "semantic_orbit_map_bound": semantic_orbit_map is not None,
        "rebuild_commitment": rebuild_commitment,
        "source_of_truth": "NOEMA_LIBRARY_TRACES",
        "derived_index_only": True,
        "ledger_mutation": False,
        "canon_allowed": False,
        "hash_used_as_semantic_coordinate": False,
    }
    return index, {
        **core,
        "receipt_commitment": _commit(core),
    }
