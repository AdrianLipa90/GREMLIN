from __future__ import annotations

from tools.gremlin_orchorbital_context_transport_bench_v01 import run_benchmark


def test_orchorbital_context_transport_benchmark_is_lossless_and_reduces_bytes() -> None:
    receipt = run_benchmark(
        branches=3,
        depth=4,
        shared_chars=4096,
        delta_chars=64,
        cache_limit=64,
    )
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_LOSSLESS_CONTEXT_TRANSPORT_REDUCTION"
    assert summary["exact_reconstruction"] is True
    assert summary["transport_packet_bytes"] < summary["full_packet_bytes"]
    assert summary["transport_byte_saving_fraction"] > 0.25
    assert summary["cache_hit_fraction"] > 0.5
    assert summary["canonical_task_commitment_changed"] is False
    assert summary["bundle_exact_reconstruction"] is True
    assert summary["bundle_transport_bytes"] < summary["same_lease_packet_bytes"]
    assert summary["bundle_byte_saving_fraction_vs_same_lease_packets"] > 0.05
    assert summary["same_lease_packets_to_bundle_ratio"] > 1.0
    assert summary["context_storage"]["storage_byte_reduction_fraction_proxy"] > 0.0
    assert summary["bundle_context_storage"]["storage_byte_reduction_fraction_proxy"] > 0.0
    assert summary["context_storage"]["cached_materialized_frame_count"] <= 8
    assert summary["bundle_context_storage"]["cached_materialized_frame_count"] <= 8
    assert summary["context_storage"]["actual_python_heap_accounting"] is False
    assert summary["runtime_speedup_claim"] is False


def test_orchorbital_context_transport_benchmark_is_deterministic() -> None:
    kwargs = {
        "branches": 2,
        "depth": 3,
        "shared_chars": 1024,
        "delta_chars": 32,
        "cache_limit": 16,
    }
    assert run_benchmark(**kwargs) == run_benchmark(**kwargs)


def test_bounded_cache_still_preserves_lossless_reconstruction() -> None:
    receipt = run_benchmark(
        branches=3,
        depth=5,
        shared_chars=2048,
        delta_chars=48,
        cache_limit=4,
    )

    assert receipt["summary"]["exact_reconstruction"] is True
    assert receipt["summary"]["final_cached_frame_count"] <= 4
    assert receipt["summary"]["canonical_task_commitment_changed"] is False
    assert receipt["summary"]["bundle_exact_reconstruction"] is True


def test_storage_proxy_respects_small_materialization_cache() -> None:
    receipt = run_benchmark(
        branches=4,
        depth=6,
        shared_chars=8192,
        delta_chars=64,
        cache_limit=32,
        store_cache_frames=2,
    )

    normal = receipt["summary"]["context_storage"]
    bundled = receipt["summary"]["bundle_context_storage"]

    assert normal["cached_materialized_frame_count"] <= 2
    assert bundled["cached_materialized_frame_count"] <= 2
    assert normal["delta_plus_cache_bytes_proxy"] < normal[
        "eager_materialized_bytes_proxy"
    ]
    assert bundled["delta_plus_cache_bytes_proxy"] < bundled[
        "eager_materialized_bytes_proxy"
    ]
    assert normal["actual_python_heap_accounting"] is False
    assert bundled["actual_python_heap_accounting"] is False
