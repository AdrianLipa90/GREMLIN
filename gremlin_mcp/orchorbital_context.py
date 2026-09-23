from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric

SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_V0_1"
PACKET_SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_PACKET_V0_1"
BUNDLE_SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_BUNDLE_V0_1"
PACKET_PAYLOAD_KEY = "_gremlin_orchorbital_context_packet"
BUNDLE_PAYLOAD_KEY = "_gremlin_orchorbital_context_bundle"
BUNDLE_REF_PAYLOAD_KEY = "_gremlin_orchorbital_context_ref"
BUNDLE_REF_SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_BUNDLE_REF_V0_1"
FRAME_DOMAIN = b"GREMLIN-ORCHORBITAL-CONTEXT-FRAME/v0.1\x00"
MATERIALIZED_DOMAIN = b"GREMLIN-ORCHORBITAL-CONTEXT-MATERIALIZED/v0.1\x00"
PACKET_DOMAIN = b"GREMLIN-ORCHORBITAL-CONTEXT-PACKET/v0.1\x00"
BUNDLE_DOMAIN = b"GREMLIN-ORCHORBITAL-CONTEXT-BUNDLE/v0.1\x00"
MAX_CONTEXT_KEYS = 4096


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("context values must be finite JSON data") from exc


def _strict_text(value: Any, field: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > maximum:
        raise ValueError(f"{field} must contain 1..{maximum} characters")
    return out



def _strict_commitment(value: Any, field: str) -> str:
    text = _strict_text(value, field, maximum=64)
    if len(text) != 64:
        raise ValueError(f"{field} must be a 64-character commitment")
    try:
        int(text, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be hexadecimal") from exc
    return text

def _strict_mapping(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    out: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = _strict_text(raw_key, f"{field} key", maximum=256)
        if key in out:
            raise ValueError(f"duplicate {field} key after normalization: {key}")
        out[key] = deepcopy(raw_value)
    if len(out) > MAX_CONTEXT_KEYS:
        raise ValueError(f"{field} exceeds {MAX_CONTEXT_KEYS} keys")
    _canonical(out)
    return out


def _strict_delete_keys(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError("delete_keys must be an iterable of strings")
    out: list[str] = []
    for index, raw in enumerate(values):
        key = _strict_text(raw, f"delete_keys[{index}]", maximum=256)
        if key not in out:
            out.append(key)
    return tuple(sorted(out))


def _materialized_commitment(context: Mapping[str, Any]) -> str:
    return hashlib.blake2b(
        MATERIALIZED_DOMAIN + _canonical(context),
        digest_size=32,
    ).hexdigest()


def _frame_commitment(
    *,
    node_id: str,
    base_frame_commitment: str | None,
    set_values: Mapping[str, Any],
    delete_keys: tuple[str, ...],
    materialized_commitment: str,
) -> str:
    core = {
        "node_id": node_id,
        "base_frame_commitment": base_frame_commitment,
        "set_values": set_values,
        "delete_keys": list(delete_keys),
        "materialized_commitment": materialized_commitment,
    }
    return hashlib.blake2b(
        FRAME_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()


@dataclass(frozen=True)
class ContextFrame:
    node_id: str
    base_node_id: str | None
    base_frame_commitment: str | None
    frame_commitment: str
    materialized_commitment: str
    depth: int
    set_values: dict[str, Any]
    delete_keys: tuple[str, ...]

    def public_view(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "base_node_id": self.base_node_id,
            "base_frame_commitment": self.base_frame_commitment,
            "frame_commitment": self.frame_commitment,
            "materialized_commitment": self.materialized_commitment,
            "depth": self.depth,
            "set_key_count": len(self.set_values),
            "delete_key_count": len(self.delete_keys),
            "raw_values_included": False,
        }


class OrbitalContextStore:
    """Immutable base+delta context lineage keyed by orchorbital node identity."""

    def __init__(self, fabric: OrchorbitalFabric) -> None:
        if not isinstance(fabric, OrchorbitalFabric):
            raise ValueError("fabric must be an OrchorbitalFabric")
        self.fabric = fabric
        self._frames: dict[str, ContextFrame] = {}
        self._materialized: dict[str, dict[str, Any]] = {}

    def _bind(
        self,
        *,
        node_id: str,
        base_node_id: str | None,
        set_values: Mapping[str, Any],
        delete_keys: Iterable[str],
    ) -> ContextFrame:
        node = self.fabric.node(node_id)
        values = _strict_mapping(set_values, "set_values")
        deletes = _strict_delete_keys(delete_keys)
        overlap = set(values) & set(deletes)
        if overlap:
            raise ValueError(
                f"context keys cannot be set and deleted together: {sorted(overlap)!r}"
            )

        if base_node_id is None:
            if node.node_id != self.fabric.authority_root_id:
                raise ValueError("only authority root may bind a context without a base")
            base_context: dict[str, Any] = {}
            base_commitment = None
            depth = 0
        else:
            base_id = _strict_text(base_node_id, "base_node_id")
            if base_id == node.node_id:
                raise ValueError("context frame cannot base on itself")
            self.fabric.node(base_id)
            base_frame = self._frames.get(base_id)
            if base_frame is None:
                raise ValueError("base node context is not bound")
            base_context = deepcopy(self._materialized[base_id])
            base_commitment = base_frame.frame_commitment
            depth = base_frame.depth + 1

        materialized = base_context
        for key in deletes:
            materialized.pop(key, None)
        materialized.update(deepcopy(values))
        materialized_digest = _materialized_commitment(materialized)
        frame_digest = _frame_commitment(
            node_id=node.node_id,
            base_frame_commitment=base_commitment,
            set_values=values,
            delete_keys=deletes,
            materialized_commitment=materialized_digest,
        )
        frame = ContextFrame(
            node_id=node.node_id,
            base_node_id=base_node_id,
            base_frame_commitment=base_commitment,
            frame_commitment=frame_digest,
            materialized_commitment=materialized_digest,
            depth=depth,
            set_values=deepcopy(values),
            delete_keys=deletes,
        )

        prior = self._frames.get(node.node_id)
        if prior is not None:
            if prior.frame_commitment == frame.frame_commitment:
                return prior
            raise RuntimeError("node context is immutable once bound")

        self._frames[node.node_id] = frame
        self._materialized[node.node_id] = deepcopy(materialized)
        return frame

    def bind_root(self, context: Mapping[str, Any]) -> ContextFrame:
        return self._bind(
            node_id=self.fabric.authority_root_id,
            base_node_id=None,
            set_values=context,
            delete_keys=(),
        )

    def bind_node(
        self,
        node_id: str,
        *,
        base_node_id: str,
        set_values: Mapping[str, Any] | None = None,
        delete_keys: Iterable[str] = (),
    ) -> ContextFrame:
        return self._bind(
            node_id=_strict_text(node_id, "node_id"),
            base_node_id=_strict_text(base_node_id, "base_node_id"),
            set_values={} if set_values is None else set_values,
            delete_keys=delete_keys,
        )

    def inherit_from_caller(
        self,
        node_id: str,
        *,
        set_values: Mapping[str, Any] | None = None,
        delete_keys: Iterable[str] = (),
    ) -> ContextFrame:
        node = self.fabric.node(node_id)
        if node.caller_id is None:
            raise ValueError("authority root has no caller context")
        return self.bind_node(
            node.node_id,
            base_node_id=node.caller_id,
            set_values=set_values,
            delete_keys=delete_keys,
        )

    def inherit_from_center(
        self,
        node_id: str,
        *,
        set_values: Mapping[str, Any] | None = None,
        delete_keys: Iterable[str] = (),
    ) -> ContextFrame:
        node = self.fabric.node(node_id)
        if node.center_id is None:
            raise ValueError("node has no orbital center")
        return self.bind_node(
            node.node_id,
            base_node_id=node.center_id,
            set_values={} if set_values is None else set_values,
            delete_keys=delete_keys,
        )

    def frame(self, node_id: str) -> ContextFrame:
        nid = _strict_text(node_id, "node_id")
        frame = self._frames.get(nid)
        if frame is None:
            raise ValueError("node context is not bound")
        return ContextFrame(
            node_id=frame.node_id,
            base_node_id=frame.base_node_id,
            base_frame_commitment=frame.base_frame_commitment,
            frame_commitment=frame.frame_commitment,
            materialized_commitment=frame.materialized_commitment,
            depth=frame.depth,
            set_values=deepcopy(frame.set_values),
            delete_keys=frame.delete_keys,
        )

    def materialize(self, node_id: str) -> dict[str, Any]:
        nid = _strict_text(node_id, "node_id")
        if nid not in self._materialized:
            raise ValueError("node context is not bound")
        return deepcopy(self._materialized[nid])

    def packet(
        self,
        node_id: str,
        *,
        receiver_known_frames: Iterable[str] = (),
    ) -> dict[str, object]:
        target = self.frame(node_id)
        known = set(
            _strict_text(value, "receiver_known_frame", maximum=128)
            for value in receiver_known_frames
        )

        chain: list[ContextFrame] = []
        current = target
        required_base: str | None = None
        while True:
            if current.frame_commitment in known:
                required_base = current.frame_commitment
                chain = []
                break
            chain.append(current)
            if current.base_node_id is None:
                required_base = None
                break
            base = self.frame(current.base_node_id)
            if base.frame_commitment in known:
                required_base = base.frame_commitment
                break
            current = base

        frames = []
        for frame in reversed(chain):
            frames.append(
                {
                    "node_id": frame.node_id,
                    "base_frame_commitment": frame.base_frame_commitment,
                    "frame_commitment": frame.frame_commitment,
                    "materialized_commitment": frame.materialized_commitment,
                    "set_values": deepcopy(frame.set_values),
                    "delete_keys": list(frame.delete_keys),
                }
            )

        core = {
            "schema": PACKET_SCHEMA,
            "target_node_id": target.node_id,
            "target_frame_commitment": target.frame_commitment,
            "target_materialized_commitment": target.materialized_commitment,
            "required_base_frame_commitment": required_base,
            "frames": frames,
        }
        packet_commitment = hashlib.blake2b(
            PACKET_DOMAIN + _canonical(core),
            digest_size=32,
        ).hexdigest()
        materialized_bytes = len(_canonical(self._materialized[target.node_id]))
        packet_bytes = len(_canonical(core))
        return {
            **core,
            "packet_commitment": packet_commitment,
            "materialized_context_bytes": materialized_bytes,
            "packet_bytes": packet_bytes,
            "byte_saving_fraction": (
                0.0
                if materialized_bytes <= 0
                else 1.0 - packet_bytes / materialized_bytes
            ),
            "lossless": True,
            "actual_model_token_accounting": False,
            "token_saving_claim": False,
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "authority_root_id": self.fabric.authority_root_id,
            "frame_count": len(self._frames),
            "frames": [
                self._frames[node_id].public_view()
                for node_id in sorted(self._frames)
            ],
            "raw_values_included": False,
            "authority": "COGNITIVE_ROUTING_ONLY",
            "canon_allowed": False,
        }


def reduce_context_packet(
    packet: Mapping[str, Any],
    *,
    receiver_known_frames: Iterable[str] = (),
) -> dict[str, object]:
    """Reduce a full packet against receiver cache without changing semantics."""

    if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("invalid context packet schema")
    if packet.get("required_base_frame_commitment") is not None:
        raise ValueError("packet reduction requires a full self-contained packet")
    # Prove the source packet is internally consistent before shortening it.
    apply_context_packet(packet)

    if isinstance(receiver_known_frames, (str, bytes, Mapping)) or not isinstance(
        receiver_known_frames, Iterable
    ):
        raise ValueError("receiver_known_frames must be an iterable")
    known = {
        _strict_commitment(value, "receiver_known_frame")
        for value in receiver_known_frames
    }
    raw_frames = packet.get("frames")
    if not isinstance(raw_frames, list):
        raise ValueError("context packet frames must be a list")

    target = _strict_commitment(
        packet.get("target_frame_commitment"),
        "target_frame_commitment",
    )
    required: str | None = None
    frames = deepcopy(raw_frames)
    cache_hit: str | None = None

    if target in known:
        required = target
        frames = []
        cache_hit = target
    else:
        last_hit = -1
        last_commitment: str | None = None
        for index, raw_frame in enumerate(raw_frames):
            if not isinstance(raw_frame, Mapping):
                raise ValueError("context packet frame must be an object")
            commitment = _strict_commitment(
                raw_frame.get("frame_commitment"),
                f"frame[{index}].frame_commitment",
            )
            if commitment in known:
                last_hit = index
                last_commitment = commitment
        if last_hit >= 0:
            required = last_commitment
            frames = deepcopy(raw_frames[last_hit + 1 :])
            cache_hit = last_commitment

    core = {
        "schema": PACKET_SCHEMA,
        "target_node_id": packet.get("target_node_id"),
        "target_frame_commitment": target,
        "target_materialized_commitment": packet.get(
            "target_materialized_commitment"
        ),
        "required_base_frame_commitment": required,
        "frames": frames,
    }
    commitment = hashlib.blake2b(
        PACKET_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()
    materialized_bytes = packet.get("materialized_context_bytes")
    if isinstance(materialized_bytes, bool) or not isinstance(materialized_bytes, int):
        raise ValueError("materialized_context_bytes must be an integer")
    packet_bytes = len(_canonical(core))
    return {
        **core,
        "packet_commitment": commitment,
        "materialized_context_bytes": materialized_bytes,
        "packet_bytes": packet_bytes,
        "byte_saving_fraction": (
            0.0
            if materialized_bytes <= 0
            else 1.0 - packet_bytes / materialized_bytes
        ),
        "cache_hit_frame_commitment": cache_hit,
        "lossless": True,
        "actual_model_token_accounting": False,
        "token_saving_claim": False,
    }



def bundle_context_packets(
    packets: Mapping[str, Mapping[str, Any]],
    *,
    receiver_known_frames: Iterable[str] = (),
) -> dict[str, object]:
    """Deduplicate full context packet frames across one worker lease."""

    if not isinstance(packets, Mapping) or not packets:
        raise ValueError("packets must be a non-empty mapping")
    if isinstance(receiver_known_frames, (str, bytes, Mapping)) or not isinstance(
        receiver_known_frames, Iterable
    ):
        raise ValueError("receiver_known_frames must be an iterable")
    known = {
        _strict_commitment(value, "receiver_known_frame")
        for value in receiver_known_frames
    }

    normalized_packets: dict[str, Mapping[str, Any]] = {}
    frames_by_commitment: dict[str, dict[str, Any]] = {}
    targets: dict[str, dict[str, str]] = {}
    full_packet_bytes = 0

    for raw_task_id, packet in packets.items():
        task_id = _strict_text(raw_task_id, "task_id", maximum=128)
        if task_id in normalized_packets:
            raise ValueError("duplicate normalized task_id in context bundle")
        if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
            raise ValueError("invalid context packet schema")
        if packet.get("required_base_frame_commitment") is not None:
            raise ValueError("context bundle requires full self-contained packets")

        # Full packet verification is mandatory before any frame is deduplicated.
        apply_context_packet(packet)
        normalized_packets[task_id] = packet

        packet_bytes = packet.get("packet_bytes")
        if isinstance(packet_bytes, bool) or not isinstance(packet_bytes, int):
            raise ValueError("context packet packet_bytes must be an integer")
        full_packet_bytes += packet_bytes

        target = _strict_commitment(
            packet.get("target_frame_commitment"),
            "target_frame_commitment",
        )
        target_materialized = _strict_commitment(
            packet.get("target_materialized_commitment"),
            "target_materialized_commitment",
        )
        target_node_id = _strict_text(
            packet.get("target_node_id"),
            "target_node_id",
            maximum=128,
        )
        targets[task_id] = {
            "target_node_id": target_node_id,
            "target_frame_commitment": target,
            "target_materialized_commitment": target_materialized,
        }

        raw_frames = packet.get("frames")
        if not isinstance(raw_frames, list):
            raise ValueError("context packet frames must be a list")
        for index, raw_frame in enumerate(raw_frames):
            if not isinstance(raw_frame, Mapping):
                raise ValueError(f"context packet frame {index} must be an object")
            commitment = _strict_commitment(
                raw_frame.get("frame_commitment"),
                f"frame[{index}].frame_commitment",
            )
            if commitment in known:
                continue
            frame = deepcopy(dict(raw_frame))
            prior = frames_by_commitment.get(commitment)
            if prior is not None and _canonical(prior) != _canonical(frame):
                raise ValueError("same context frame commitment has conflicting content")
            frames_by_commitment[commitment] = frame

    # Emit one deterministic topological frame sequence. Every base must be
    # already held by the receiver or emitted earlier in the same bundle.
    pending = dict(frames_by_commitment)
    emitted: list[dict[str, Any]] = []
    available = set(known)
    while pending:
        ready: list[str] = []
        for commitment, frame in pending.items():
            base = frame.get("base_frame_commitment")
            if base is None or base in available:
                ready.append(commitment)
        if not ready:
            raise ValueError("context bundle frame graph is disconnected or cyclic")
        for commitment in sorted(ready):
            emitted.append(pending.pop(commitment))
            available.add(commitment)

    core = {
        "schema": BUNDLE_SCHEMA,
        "frames": emitted,
        "task_targets": dict(sorted(targets.items())),
    }
    commitment = hashlib.blake2b(
        BUNDLE_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()
    bundle_bytes = len(_canonical(core))
    return {
        **core,
        "bundle_commitment": commitment,
        "receiver_known_frame_count": len(known),
        "unique_frame_count": len(emitted),
        "full_packet_bytes": full_packet_bytes,
        "bundle_bytes": bundle_bytes,
        "byte_saving_fraction_vs_full_packets": (
            0.0
            if full_packet_bytes <= 0
            else 1.0 - bundle_bytes / full_packet_bytes
        ),
        "lossless": True,
        "actual_model_token_accounting": False,
        "token_saving_claim": False,
    }


def apply_context_bundle(
    bundle: Mapping[str, Any],
    *,
    known_contexts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, object]:
    """Verify one lease-level context bundle and return cache updates."""

    if not isinstance(bundle, Mapping) or bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("invalid context bundle schema")
    contexts: Mapping[str, Mapping[str, Any]] = (
        {} if known_contexts is None else known_contexts
    )
    if not isinstance(contexts, Mapping):
        raise ValueError("known_contexts must be a mapping")

    raw_frames = bundle.get("frames")
    if not isinstance(raw_frames, list):
        raise ValueError("context bundle frames must be a list")
    raw_targets = bundle.get("task_targets")
    if not isinstance(raw_targets, Mapping):
        raise ValueError("context bundle task_targets must be a mapping")

    updates: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    normalized_frames: list[dict[str, Any]] = []
    for index, raw_frame in enumerate(raw_frames):
        if not isinstance(raw_frame, Mapping):
            raise ValueError(f"context bundle frame {index} must be an object")
        node_id = _strict_text(
            raw_frame.get("node_id"),
            f"bundle.frame[{index}].node_id",
        )
        base = raw_frame.get("base_frame_commitment")
        if base is not None:
            base = _strict_commitment(
                base,
                f"bundle.frame[{index}].base_frame_commitment",
            )
            base_context = updates.get(base)
            if base_context is None:
                candidate = contexts.get(base)
                if not isinstance(candidate, Mapping):
                    raise ValueError("context bundle base frame is unavailable")
                current = _strict_mapping(candidate, "known bundle base context")
            else:
                current = deepcopy(base_context)
        else:
            current = {}

        set_values = _strict_mapping(
            raw_frame.get("set_values", {}),
            f"bundle.frame[{index}].set_values",
        )
        delete_keys = _strict_delete_keys(raw_frame.get("delete_keys", ()))
        if set(set_values) & set(delete_keys):
            raise ValueError("context bundle frame set/delete overlap")
        for key in delete_keys:
            current.pop(key, None)
        current.update(deepcopy(set_values))

        materialized = _materialized_commitment(current)
        claimed_materialized = _strict_commitment(
            raw_frame.get("materialized_commitment"),
            f"bundle.frame[{index}].materialized_commitment",
        )
        if materialized != claimed_materialized:
            raise ValueError("context bundle materialized commitment mismatch")
        expected_frame = _frame_commitment(
            node_id=node_id,
            base_frame_commitment=base,
            set_values=set_values,
            delete_keys=delete_keys,
            materialized_commitment=materialized,
        )
        claimed_frame = _strict_commitment(
            raw_frame.get("frame_commitment"),
            f"bundle.frame[{index}].frame_commitment",
        )
        if expected_frame != claimed_frame:
            raise ValueError("context bundle frame commitment mismatch")
        if claimed_frame in seen:
            raise ValueError("duplicate context frame in bundle")
        seen.add(claimed_frame)
        updates[claimed_frame] = deepcopy(current)
        normalized_frames.append(deepcopy(dict(raw_frame)))

    targets: dict[str, dict[str, str]] = {}
    for raw_task_id, raw_target in raw_targets.items():
        task_id = _strict_text(raw_task_id, "bundle task_id", maximum=128)
        if not isinstance(raw_target, Mapping):
            raise ValueError("context bundle target must be an object")
        target_node_id = _strict_text(
            raw_target.get("target_node_id"),
            "bundle target_node_id",
            maximum=128,
        )
        target_frame = _strict_commitment(
            raw_target.get("target_frame_commitment"),
            "bundle target_frame_commitment",
        )
        target_materialized = _strict_commitment(
            raw_target.get("target_materialized_commitment"),
            "bundle target_materialized_commitment",
        )
        materialized_context = updates.get(target_frame)
        if materialized_context is None:
            candidate = contexts.get(target_frame)
            if not isinstance(candidate, Mapping):
                raise ValueError("context bundle target frame is unavailable")
            materialized_context = _strict_mapping(
                candidate,
                "known bundle target context",
            )
        if _materialized_commitment(materialized_context) != target_materialized:
            raise ValueError("context bundle target materialized mismatch")
        targets[task_id] = {
            "target_node_id": target_node_id,
            "target_frame_commitment": target_frame,
            "target_materialized_commitment": target_materialized,
        }

    core = {
        "schema": BUNDLE_SCHEMA,
        "frames": normalized_frames,
        "task_targets": dict(sorted(targets.items())),
    }
    expected_bundle = hashlib.blake2b(
        BUNDLE_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()
    if bundle.get("bundle_commitment") != expected_bundle:
        raise ValueError("context bundle commitment mismatch")

    return {
        "schema": BUNDLE_SCHEMA,
        "cache_updates": updates,
        "task_targets": targets,
        "lossless": True,
    }



def context_bundle_reference(
    bundle: Mapping[str, Any],
    task_id: str,
) -> dict[str, str]:
    """Return a compact task-local reference into a verified-shaped bundle."""

    if not isinstance(bundle, Mapping) or bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("invalid context bundle schema")
    tid = _strict_text(task_id, "task_id", maximum=128)
    targets = bundle.get("task_targets")
    if not isinstance(targets, Mapping):
        raise ValueError("context bundle task_targets must be a mapping")
    raw_target = targets.get(tid)
    if not isinstance(raw_target, Mapping):
        raise ValueError("context bundle has no target for task")
    return {
        "schema": BUNDLE_REF_SCHEMA,
        "target_node_id": _strict_text(
            raw_target.get("target_node_id"),
            "target_node_id",
            maximum=128,
        ),
        "target_frame_commitment": _strict_commitment(
            raw_target.get("target_frame_commitment"),
            "target_frame_commitment",
        ),
        "target_materialized_commitment": _strict_commitment(
            raw_target.get("target_materialized_commitment"),
            "target_materialized_commitment",
        ),
    }


def apply_context_packet(
    packet: Mapping[str, Any],
    *,
    known_contexts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, object]:
    """Verify and materialize a worker-side context packet.

    known_contexts maps frame commitments to already cached materialized
    contexts. The returned cache_updates may be persisted by the receiver.
    """

    if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("invalid context packet schema")
    contexts: Mapping[str, Mapping[str, Any]] = {} if known_contexts is None else known_contexts
    if not isinstance(contexts, Mapping):
        raise ValueError("known_contexts must be a mapping")

    required = packet.get("required_base_frame_commitment")
    if required is not None and not isinstance(required, str):
        raise ValueError("required base frame commitment is invalid")
    if required is None:
        current: dict[str, Any] = {}
    else:
        base = contexts.get(required)
        if not isinstance(base, Mapping):
            raise ValueError("required base context is unavailable")
        current = _strict_mapping(base, "known base context")

    raw_frames = packet.get("frames")
    if not isinstance(raw_frames, list):
        raise ValueError("context packet frames must be a list")
    updates: dict[str, dict[str, Any]] = {}

    prior_commitment = required
    for index, raw_frame in enumerate(raw_frames):
        if not isinstance(raw_frame, Mapping):
            raise ValueError(f"context packet frame {index} must be an object")
        node_id = _strict_text(raw_frame.get("node_id"), f"frame[{index}].node_id")
        base_commitment = raw_frame.get("base_frame_commitment")
        if base_commitment != prior_commitment:
            raise ValueError("context packet frame chain is discontinuous")
        set_values = _strict_mapping(
            raw_frame.get("set_values", {}),
            f"frame[{index}].set_values",
        )
        delete_keys = _strict_delete_keys(raw_frame.get("delete_keys", ()))
        if set(set_values) & set(delete_keys):
            raise ValueError("context packet frame set/delete overlap")

        next_context = deepcopy(current)
        for key in delete_keys:
            next_context.pop(key, None)
        next_context.update(deepcopy(set_values))
        materialized_digest = _materialized_commitment(next_context)
        claimed_materialized = raw_frame.get("materialized_commitment")
        if materialized_digest != claimed_materialized:
            raise ValueError("context materialized commitment mismatch")
        claimed_frame = raw_frame.get("frame_commitment")
        expected_frame = _frame_commitment(
            node_id=node_id,
            base_frame_commitment=base_commitment,
            set_values=set_values,
            delete_keys=delete_keys,
            materialized_commitment=materialized_digest,
        )
        if claimed_frame != expected_frame:
            raise ValueError("context frame commitment mismatch")

        current = next_context
        prior_commitment = expected_frame
        updates[expected_frame] = deepcopy(current)

    target_frame = packet.get("target_frame_commitment")
    target_materialized = packet.get("target_materialized_commitment")
    if prior_commitment != target_frame:
        if not raw_frames and required == target_frame:
            cached = contexts.get(required)
            if not isinstance(cached, Mapping):
                raise ValueError("target cached context is unavailable")
            current = _strict_mapping(cached, "target cached context")
        else:
            raise ValueError("context packet target frame mismatch")
    if _materialized_commitment(current) != target_materialized:
        raise ValueError("context packet target materialized mismatch")

    core = {
        "schema": PACKET_SCHEMA,
        "target_node_id": packet.get("target_node_id"),
        "target_frame_commitment": target_frame,
        "target_materialized_commitment": target_materialized,
        "required_base_frame_commitment": required,
        "frames": raw_frames,
    }
    expected_packet = hashlib.blake2b(
        PACKET_DOMAIN + _canonical(core),
        digest_size=32,
    ).hexdigest()
    if packet.get("packet_commitment") != expected_packet:
        raise ValueError("context packet commitment mismatch")

    return {
        "schema": PACKET_SCHEMA,
        "target_node_id": packet.get("target_node_id"),
        "target_frame_commitment": target_frame,
        "materialized_context": deepcopy(current),
        "cache_updates": updates,
        "lossless": True,
    }


__all__ = [
    "BUNDLE_PAYLOAD_KEY",
    "BUNDLE_REF_PAYLOAD_KEY",
    "BUNDLE_REF_SCHEMA",
    "BUNDLE_SCHEMA",
    "ContextFrame",
    "MAX_CONTEXT_KEYS",
    "OrbitalContextStore",
    "PACKET_PAYLOAD_KEY",
    "PACKET_SCHEMA",
    "SCHEMA",
    "apply_context_bundle",
    "apply_context_packet",
    "bundle_context_packets",
    "context_bundle_reference",
    "reduce_context_packet",
]
