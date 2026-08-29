from tools.gremlin_bestiary_vector_species_v03 import (
    build_species_plan,
    dispatch_compression,
    lane_width,
    validate_plan,
)


def test_outer_orbit_batches_are_not_smaller_than_hummingbird():
    assert lane_width("BELZEBUB") >= lane_width("HUMMINGBIRD")
    assert lane_width("MOLE") >= lane_width("HUMMINGBIRD")


def test_plan_preserves_all_routed_work():
    counts = {"SPIDER": 101, "RAVEN": 83, "MOLE": 47, "BELZEBUB": 29}
    plan = build_species_plan(counts, vector_width=8)
    validate_plan(plan)
    assert sum(p.route_count for p in plan) == sum(counts.values())
    assert all(p.batch_count * p.lane_width >= p.route_count for p in plan)


def test_plan_is_ordered_by_service_frequency():
    counts = {"BELZEBUB": 1, "HUMMINGBIRD": 1, "HOUND": 1, "MOLE": 1}
    plan = build_species_plan(counts)
    omegas = [p.omega for p in plan]
    assert omegas == sorted(omegas, reverse=True)


def test_dispatch_compression_is_real_for_batched_work():
    plan = build_species_plan({"SPIDER": 1000, "MOLE": 1000, "BELZEBUB": 1000})
    assert dispatch_compression(plan) > 1.0


def test_unknown_species_fail_closed():
    try:
        lane_width("DRAGON")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown species must fail closed")
