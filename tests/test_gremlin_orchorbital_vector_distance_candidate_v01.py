from __future__ import annotations

import math

from tools.gremlin_orchorbital_vector_distance_candidate_v01 import run_benchmark


def test_vector_distance_candidate_matches_scalar_numerically_without_enabling_routing() -> None:
    receipt = run_benchmark(candidate_count=257, repeats=1)
    summary = receipt["summary"]

    assert receipt["verdict"] == "PASS_NUMERICAL_EQUIVALENCE_CANDIDATE"
    assert summary["max_abs_error"] <= 1e-12
    assert summary["checksum_error"] <= 1e-8
    assert summary["same_nearest_index"] is True
    assert summary["same_farthest_index"] is True
    assert math.isfinite(summary["observed_microkernel_speedup"])
    assert summary["observed_microkernel_speedup"] > 0.0
    assert summary["routing_enabled"] is False
    assert summary["selection_equivalence_proven"] is False
    assert summary["end_to_end_speedup_claim"] is False
    assert summary["two_hundred_x_end_to_end_claim"] is False
