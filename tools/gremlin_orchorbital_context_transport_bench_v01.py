from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path

from gremlin_mcp.orchorbital_context import (
    OrbitalContextStore,
    apply_context_packet,
    reduce_context_packet,
)
from gremlin_mcp.orchorbital_fabric import OrchorbitalFabric

OUT = Path("provenance/GREMLIN_ORCHORBITAL_CONTEXT_TRANSPORT_BENCHMARK_V0_1.json")
SCHEMA = "GREMLIN_ORCHORBITAL_CONTEXT_TRANSPORT_BENCHMARK_V0_1"


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
) -> dict[str, object]:
    branches = _positive_int(branches, "branches")
    depth = _positive_int(depth, "depth")
    shared_chars = _positive_int(shared_chars, "shared_chars", minimum=128)
    delta_chars = _positive_int(delta_chars, "delta_chars", minimum=8)
    cache_limit = _positive_int(cache_limit, "cache_limit")

    fabric = OrchorbitalFabric(max_nodes=1 + branches * depth)
    contexts = OrbitalContextStore(fabric)
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
        if exact_reconstruction and transport_packet_bytes < full_packet_bytes
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
            "traversal": "DEPTH_ROUND_ROBIN_BRANCHES",
            "species": "SPIDER",
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
            "canonical_task_commitment_changed": False,
            "actual_model_token_accounting": False,
            "actual_model_billing_accounting": False,
            "runtime_speedup_claim": False,
            "external_effects": False,
            "canon_allowed": False,
        },
        "verdict": verdict,
        "claim_scope": (
            "BYTE_TRANSPORT_REDUCTION_FOR_THIS_SYNTHETIC_ORCHORBITAL_CONTEXT_FIXTURE_ONLY; "
            "LOSSLESS_RECONSTRUCTION_VERIFIED; NOT A TOKEN, BILLING, LATENCY OR 200X CLAIM"
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
