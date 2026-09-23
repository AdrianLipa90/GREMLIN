import math

from gremlin_mcp.server_with_hive import (
    gremlin_hive_holographic_phase_transport,
    gremlin_hive_holographic_project,
    gremlin_hive_holographic_remap,
    gremlin_hive_holographic_retrieve,
    gremlin_hive_status,
)


def _cell(offset: float) -> list[float]:
    return [float((offset + 0.09 * i) % (2 * math.pi)) for i in range(36)]


def test_hive_status_exposes_read_only_holographic_memory():
    status = gremlin_hive_status()
    holo = status["holographic_orbital_memory"]
    assert holo["status"] == "AVAILABLE_READ_ONLY_DERIVED"
    assert holo["ledger_mutation"] is False
    assert holo["rebuildable_from_ledger"] is True


def test_native_holographic_surfaces_are_callable_and_non_authoritative():
    a = _cell(0.1)
    b = _cell(0.6)
    records = {"a": a, "b": b}

    projection = gremlin_hive_holographic_project([a, b])
    assert projection["source_count"] == 2
    assert projection["authority"]["ledger_mutation"] is False

    remap = gremlin_hive_holographic_remap(records)
    assert remap["record_count"] == 2
    assert remap["authority"]["canon_allowed"] is False

    retrieved = gremlin_hive_holographic_retrieve(
        a,
        records,
        min_candidates=1,
        max_hex_ring=3,
        orbit_radius=8,
    )
    assert retrieved["record_id"] == "a"

    carrier = [0.01 * (i - 18) for i in range(36)]
    moved = gremlin_hive_holographic_phase_transport(a, carrier, gain=0.5)
    restored = gremlin_hive_holographic_phase_transport(
        moved["phase_36d"],
        carrier,
        gain=-0.5,
    )
    err = math.sqrt(
        sum(
            math.atan2(math.sin(x - y), math.cos(x - y)) ** 2
            for x, y in zip(a, restored["phase_36d"])
        ) / 36
    )
    assert err < 1e-12
    assert moved["physical_qhtri_claim"] is False
