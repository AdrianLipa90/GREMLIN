from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path

from gremlin_mcp.orchorbital_context import (
    OrbitalContextStore,
    apply_context_bundle,
    apply_context_packet,
    bundle_context_packets,
    context_bundle_reference,
    reduce_context_packet,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric

OUT = Path("provenance/GREMLIN_ORCHORBITAL_CONTEXT_TRANSPORT_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_TRANSPORT_BENCHMARK_V0_1"


def _json_size(value: object) -> int:
    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )


def _positive_int(value: int, field: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def run_benchmark(
    *,
    branches: int = 6,
    depth: int = 8,
    shared_chars: int = 16_384,
    delta_chars: int = 192,
    cache_limit: int = 256,
    store_cache_frames: int = 8,
) -> dict[str, object]:
    branches = _positive_int(branches, "branches")
    depth = _positive_int(depth, "depth")
    shared_chars = _positive_int(shared_chars, "shared_chars", minimum=128)
    delta_chars = _positive_int(delta_chars, "delta_chars", minimum=8)
    cache_limit = _positive_int(cache_limit, "cache_limit")
    store_cache_frames = _positive_int(
        store_cache_frames,
        "store_cache_frames",
    )

    fabric = OrchorbitalFabric(max_nodes=1 + branches * depth)
    contexts = OrbitalContextStore(
        fabric,
        materialization_cache_frames=store_cache_frames,
    )
    contexts.bind_root(
        {
            "request": "R" * shared_chars,
            "memory_projection": "M" * shared_chars,
            "constraints": {
                "authority": "candidate-only",
                "routing": "orchorbital",
                "deterministic": True,
            },
        }
    )

    traversal: list[str] = []
    parent_by_branch = {branch: fabric.authority_root_id for branch in range(branches)}
    for level in range(depth):
        for branch_index in range(branches):
            parent_id = parent_by_branch[branch_index]
            node_id = f"B{branch_index:03d}:D{level:03d}"
            node = fabric.spawn(
                parent_id,
                "SPIDER",
                node_id=node_id,
                obligations=(f"branch-{branch_index}-level-{level}",),
                join_to_caller=False,
            )
            contexts.inherit_from_caller(
                node.node_id,
                set_values={
                    "local_node": node.node_id,
                    "local_delta": (
                        f"branch={branch_index};depth={level};"
                        + chr(65 + (branch_index % 26)) * delta_chars
                    ),
                },
            )
            parent_by_branch[branch_index] = node.node_id
            traversal.append(node.node_id)

    cache: OrderedDict[str, dict[str, object]] = OrderedDict()
    full_packet_bytes = 0
    transport_packet_bytes = 0
    materialized_context_bytes = 0
    cache_hit_tasks = 0
    delivered_frames = 0
    exact_reconstruction = True

    for node_id in traversal:
        full = contexts.packet(node_id)
        reduced = reduce_context_packet(
            full,
            receiver_known_frames=tuple(cache),
        )
        decoded = apply_context_packet(
            reduced,
            known_contexts=cache,
        )
        expected = contexts.materialize(node_id)
        if decoded["materialized_context"] != expected:
            exact_reconstruction = False
            raise RuntimeError(f"context reconstruction mismatch at {node_id}")

        full_packet_bytes += int(full["packet_bytes"])
        transport_packet_bytes += int(reduced["packet_bytes"])
        materialized_context_bytes += int(full["materialized_context_bytes"])
        delivered_frames += len(reduced["frames"])
        if reduced["required_base_frame_commitment"] is not None:
            cache_hit_tasks += 1

        updates = decoded["cache_updates"]
        if not isinstance(updates, dict):
            raise RuntimeError("context decoder returned invalid cache_updates")
        for commitment, materialized in updates.items():
            if commitment in cache:
                del cache[commitment]
            cache[commitment] = dict(materialized)
        target = decoded["target_frame_commitment"]
        materialized = decoded["materialized_context"]
        if not isinstance(target, str) or not isinstance(materialized, dict):
            raise RuntimeError("context decoder returned invalid target")
        if target in cache:
            del cache[target]
        cache[target] = dict(materialized)
        while len(cache) > cache_limit:
            cache.popitem(last=False)

    # Separate same-lease sibling benchmark. Every level fans out from one
    # shared orbital parent, so all tasks in a lease genuinely share ancestry.
    bundle_fabric = OrchorbitalFabric(max_nodes=1 + branches * depth)
    bundle_contexts = OrbitalContextStore(
        bundle_fabric,
        materialization_cache_frames=store_cache_frames,
    )
    bundle_contexts.bind_root(
        {
            "request": "R" * shared_chars,
            "memory_projection": "M" * shared_chars,
            "constraints": {
                "authority": "candidate-only",
                "routing": "orchorbital-bundle",
                "deterministic": True,
            },
        }
    )
    shared_parent = bundle_fabric.authority_root_id
    level_nodes: list[list[str]] = []
    for level in range(depth):
        current_level: list[str] = []
        shared_frame_id = f"CTX:BENCH:L{level:03d}"
        bundle_contexts.bind_shared_frame(
            shared_frame_id,
            base_frame_id=shared_parent,
            set_values={
                "handoff": (
                    f"level={level};"
                    + "H" * max(delta_chars * 8, shared_chars // 8)
                ),
                "parent_result_commitment_proxy": f"result-{level:03d}",
            },
        )
        for sibling in range(branches):
            node_id = f"L{level:03d}:S{sibling:03d}"
            node = bundle_fabric.spawn(
                shared_parent,
                "SPIDER",
                node_id=node_id,
                obligations=(f"level-{level}-sibling-{sibling}",),
                join_to_caller=False,
            )
            bundle_contexts.bind_node(
                node.node_id,
                base_node_id=shared_frame_id,
                set_values={
                    "local_node": node.node_id,
                    "local_delta": (
                        f"level={level};sibling={sibling};"
                        + chr(65 + (sibling % 26)) * delta_chars
                    ),
                },
            )
            current_level.append(node.node_id)
        level_nodes.append(current_level)
        shared_parent = current_level[0]

    bundle_cache: OrderedDict[str, dict[str, object]] = OrderedDict()
    same_lease_packet_bytes = 0
    bundle_transport_bytes = 0
    bundle_full_packet_bytes = 0
    bundle_unique_frames = 0
    bundle_exact_reconstruction = True

    for current_level in level_nodes:
        known_before = tuple(bundle_cache)
        packets = {
            node_id: bundle_contexts.packet(node_id)
            for node_id in current_level
        }
        for packet in packets.values():
            reduced = reduce_context_packet(
                packet,
                receiver_known_frames=known_before,
            )
            same_lease_packet_bytes += int(reduced["packet_bytes"])
            bundle_full_packet_bytes += int(packet["packet_bytes"])

        bundle = bundle_context_packets(
            packets,
            receiver_known_frames=known_before,
        )
        decoded_bundle = apply_context_bundle(
            bundle,
            known_contexts=bundle_cache,
        )
        refs = {
            node_id: context_bundle_reference(bundle, node_id)
            for node_id in current_level
        }
        bundle_transport_bytes += int(bundle["bundle_bytes"]) + sum(
            _json_size(ref) for ref in refs.values()
        )
        bundle_unique_frames += int(bundle["unique_frame_count"])

        updates = decoded_bundle["cache_updates"]
        if not isinstance(updates, dict):
            raise RuntimeError("context bundle decoder returned invalid cache_updates")
        staged = dict(bundle_cache)
        for commitment, materialized in updates.items():
            if not isinstance(commitment, str) or not isinstance(materialized, dict):
                raise RuntimeError("context bundle cache update is invalid")
            staged[commitment] = dict(materialized)

        for node_id, ref in refs.items():
            target = ref["target_frame_commitment"]
            materialized = staged.get(target)
            expected = bundle_contexts.materialize(node_id)
            if materialized != expected:
                bundle_exact_reconstruction = False
                raise RuntimeError(
                    f"context bundle reconstruction mismatch at {node_id}"
                )

        bundle_cache = OrderedDict(staged.items())
        while len(bundle_cache) > cache_limit:
            bundle_cache.popitem(last=False)

    bundle_saving_fraction = (
        0.0
        if same_lease_packet_bytes <= 0
        else 1.0 - bundle_transport_bytes / same_lease_packet_bytes
    )
    bundle_ratio = (
        1.0
        if bundle_transport_bytes <= 0
        else same_lease_packet_bytes / bundle_transport_bytes
    )

    def storage_proxy(store: OrbitalContextStore) -> dict[str, float | int]:
        frame_ids = sorted(store._frames)
        eager_materialized_bytes = sum(
            _json_size(store.materialize(frame_id))
            for frame_id in frame_ids
        )
        delta_frame_bytes = sum(
            _json_size(
                {
                    "node_id": frame.node_id,
                    "base_node_id": frame.base_node_id,
                    "base_frame_commitment": frame.base_frame_commitment,
                    "frame_commitment": frame.frame_commitment,
                    "materialized_commitment": frame.materialized_commitment,
                    "depth": frame.depth,
                    "set_values": frame.set_values,
                    "delete_keys": list(frame.delete_keys),
                }
            )
            for frame in store._frames.values()
        )
        cache_materialized_bytes = sum(
            _json_size(value)
            for value in store._materialized_cache.values()
        )
        delta_plus_cache_bytes = delta_frame_bytes + cache_materialized_bytes
        reduction = (
            0.0
            if eager_materialized_bytes <= 0
            else 1.0 - delta_plus_cache_bytes / eager_materialized_bytes
        )
        ratio = (
            1.0
            if delta_plus_cache_bytes <= 0
            else eager_materialized_bytes / delta_plus_cache_bytes
        )
        return {
            "frame_count": len(frame_ids),
            "cache_limit_frames": store._materialization_cache_frames,
            "cached_materialized_frame_count": len(store._materialized_cache),
            "eager_materialized_bytes_proxy": eager_materialized_bytes,
            "delta_frame_bytes_proxy": delta_frame_bytes,
            "cache_materialized_bytes_proxy": cache_materialized_bytes,
            "delta_plus_cache_bytes_proxy": delta_plus_cache_bytes,
            "storage_byte_reduction_fraction_proxy": reduction,
            "eager_to_delta_plus_cache_ratio_proxy": ratio,
            "actual_python_heap_accounting": False,
        }

    context_storage = storage_proxy(contexts)
    bundle_context_storage = storage_proxy(bundle_contexts)

    task_count = len(traversal)
    saving_fraction = (
        0.0
        if full_packet_bytes <= 0
        else 1.0 - transport_packet_bytes / full_packet_bytes
    )
    compression_ratio = (
        1.0
        if transport_packet_bytes <= 0
        else full_packet_bytes / transport_packet_bytes
    )
    verdict = (
        "PASS_LOSSLESS_CONTEXT_TRANSPORT_REDUCTION"
        if (
            exact_reconstruction
            and bundle_exact_reconstruction
            and transport_packet_bytes < full_packet_bytes
            and bundle_transport_bytes < same_lease_packet_bytes
            and float(
                context_storage["storage_byte_reduction_fraction_proxy"]
            ) > 0.0
            and float(
                bundle_context_storage["storage_byte_reduction_fraction_proxy"]
            ) > 0.0
        )
        else "FAIL_CONTEXT_TRANSPORT_REDUCTION"
    )

    return {
        "schema": SCHEMA,
        "fixture": {
            "branches": branches,
            "depth": depth,
            "node_count": task_count,
            "shared_chars_per_root_field": shared_chars,
            "delta_chars_per_node": delta_chars,
            "cache_limit_frames": cache_limit,
            "store_materialization_cache_frames": store_cache_frames,
            "traversal": "DEPTH_ROUND_ROBIN_BRANCHES",
            "species": "SPIDER",
            "same_lease_shared_frame": True,
            "shared_handoff_chars_per_level": max(
                delta_chars * 8,
                shared_chars // 8,
            ),
        },
        "summary": {
            "task_count": task_count,
            "full_packet_bytes": full_packet_bytes,
            "transport_packet_bytes": transport_packet_bytes,
            "transport_byte_saving_fraction": saving_fraction,
            "full_to_transport_ratio": compression_ratio,
            "materialized_context_bytes_proxy": materialized_context_bytes,
            "cache_hit_tasks": cache_hit_tasks,
            "cache_hit_fraction": 0.0 if task_count <= 0 else cache_hit_tasks / task_count,
            "delivered_frame_count": delivered_frames,
            "final_cached_frame_count": len(cache),
            "exact_reconstruction": exact_reconstruction,
            "same_lease_packet_bytes": same_lease_packet_bytes,
            "bundle_transport_bytes": bundle_transport_bytes,
            "bundle_byte_saving_fraction_vs_same_lease_packets": bundle_saving_fraction,
            "same_lease_packets_to_bundle_ratio": bundle_ratio,
            "bundle_full_packet_bytes": bundle_full_packet_bytes,
            "bundle_unique_frame_count": bundle_unique_frames,
            "bundle_exact_reconstruction": bundle_exact_reconstruction,
            "context_storage": context_storage,
            "bundle_context_storage": bundle_context_storage,
            "canonical_task_commitment_changed": False,
            "actual_model_token_accounting": False,
            "actual_model_billing_accounting": False,
            "runtime_speedup_claim": False,
            "external_effects": False,
            "canon_allowed": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "BYTE_TRANSPORT_AND_SERIALIZED_STORAGE_PROXY_REDUCTION_FOR_THIS_SYNTHETIC_"
            "ORCHORBITAL_CONTEXT_FIXTURE_ONLY; LOSSLESS_RECONSTRUCTION_VERIFIED; "
            "NOT ACTUAL PYTHON HEAP, TOKEN, BILLING, LATENCY OR 200X CLAIM"
        ),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def main() -> int:
    receipt = run_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"verdict={receipt['verdict']}")
    print(f"claim_scope={receipt['claim_scope']}")
    print(f"receipt={OUT}")
    return 0 if receipt["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
