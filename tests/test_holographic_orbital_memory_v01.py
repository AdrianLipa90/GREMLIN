import math
import random

from gremlin_mcp.holographic_orbital_memory import (
    AUTHORITY,
    DIM,
    HolographicOrbitalIndex,
    apply_phase_carrier,
    holographic_address,
    kuramoto_potential,
    kuramoto_relax,
    moire_overlap,
    phase_rms_distance,
    project_hologram,
    validate_cell,
)


def _cell(offset=0.0):
    return tuple((offset + 0.07 * i) % (2 * math.pi) for i in range(DIM))


def test_exact_36d_and_authority_firewall():
    assert len(validate_cell(_cell())) == 36
    assert AUTHORITY["ledger_mutation"] is False
    assert AUTHORITY["canon_allowed"] is False
    try:
        validate_cell([0.0] * 35)
    except ValueError:
        pass
    else:
        raise AssertionError("35D cell must fail closed")


def test_equal_memory_projection_is_exact_and_coherent():
    a = _cell(0.2)
    p = project_hologram([a, a, a])
    assert p.global_coherence > 1.0 - 1e-12
    assert phase_rms_distance(p.phase_36d, a) < 1e-12


def test_antiphase_memories_cancel_holographically():
    a = _cell(0.1)
    b = tuple((x + math.pi) % (2 * math.pi) for x in a)
    p = project_hologram([a, b])
    assert max(p.amplitude_36d) < 1e-12


def test_global_phase_equivariance():
    a = _cell(0.1)
    b = _cell(0.3)
    shift = 0.71
    p0 = project_hologram([a, b])
    p1 = project_hologram([
        tuple((x + shift) % (2 * math.pi) for x in a),
        tuple((x + shift) % (2 * math.pi) for x in b),
    ])
    shifted = tuple((x + shift) % (2 * math.pi) for x in p0.phase_36d)
    assert phase_rms_distance(shifted, p1.phase_36d) < 1e-12
    assert max(abs(x - y) for x, y in zip(p0.amplitude_36d, p1.amplitude_36d)) < 1e-12


def test_moire_overlap_bounds_and_identity():
    a = _cell()
    assert abs(moire_overlap(a, a) - 1.0) < 1e-12
    b = tuple((x + math.pi) % (2 * math.pi) for x in a)
    assert abs(moire_overlap(a, b) - 1.0) < 1e-12
    c = tuple((x + (math.pi if i % 2 else 0.0)) % (2 * math.pi) for i, x in enumerate(a))
    assert moire_overlap(a, c) < 1e-12


def test_kuramoto_relax_does_not_raise_pair_potential():
    a = _cell(0.0)
    b = tuple((x + 0.9) % (2 * math.pi) for x in _cell(0.2))
    before = kuramoto_potential([a, b])
    relaxed = kuramoto_relax([a, b], coupling=0.8, dt=0.03, steps=20)
    after = kuramoto_potential(relaxed)
    assert after <= before + 1e-12


def test_address_is_deterministic_and_remap_rebuilds_exactly():
    records = {"m:1": _cell(0.1), "m:2": _cell(0.5), "m:3": _cell(1.0)}
    a = HolographicOrbitalIndex.remap(records)
    b = HolographicOrbitalIndex.remap(dict(reversed(list(records.items()))))
    assert a.mapping_commitment() == b.mapping_commitment()
    assert holographic_address(records["m:1"]) == holographic_address(records["m:1"])


def test_hex_orbital_prefilter_preserves_cluster_recall_with_large_comparison_reduction():
    rng = random.Random(17)
    cluster_count = 10
    per_cluster = 48
    bases = [tuple(rng.random() * 2 * math.pi for _ in range(DIM)) for _ in range(cluster_count)]
    records = {}
    labels = {}
    for c, base in enumerate(bases):
        for j in range(per_cluster):
            rid = f"c{c}:{j}"
            cell = tuple((x + rng.gauss(0.0, 0.18)) % (2 * math.pi) for x in base)
            records[rid] = cell
            labels[rid] = c
    index = HolographicOrbitalIndex.remap(records, hex_scale=16.0)
    good = 0
    comparisons = 0
    query_count = 0
    for c, base in enumerate(bases):
        for _ in range(6):
            query = tuple((x + rng.gauss(0.0, 0.22)) % (2 * math.pi) for x in base)
            result = index.retrieve(query, min_candidates=12, max_hex_ring=3, orbit_radius=1)
            good += int(labels[result.record_id] == c)
            comparisons += result.candidate_count
            query_count += 1
    recall = good / query_count
    average_candidates = comparisons / query_count
    assert recall >= 0.95
    assert average_candidates <= len(records) / 4.0


def test_phase_carrier_roundtrip_is_reversible():
    a = _cell(0.2)
    carrier = tuple(0.01 * (i - 18) for i in range(DIM))
    moved = apply_phase_carrier(a, carrier, gain=0.7)
    restored = apply_phase_carrier(moved, carrier, gain=-0.7)
    assert phase_rms_distance(a, restored) < 1e-12
