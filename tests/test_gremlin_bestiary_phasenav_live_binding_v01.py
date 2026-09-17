import json
import math
import struct

import pytest

from tools import gremlin_bestiary_phasenav_live_binding_v01 as live
from tools import gremlin_bestiary_phasenav_phase_gates_v01 as base


def make_surface(tmp_path, *, omit=None):
    root = tmp_path / "ciel_noema"
    (root / "phasenav").mkdir(parents=True)
    (root / "ciel_binding_status").write_text("ACTIVE\n", encoding="utf-8")
    phi = tuple((0.17 + 0.031 * i) % base.TAU for i in range(base.DIM))
    (root / "phi").write_bytes(struct.pack("<36d", *phi))

    ops = sorted({op for names in live.SPECIES_OPERATOR_BINDINGS.values() for op in names})
    lines = []
    for op_index, op in enumerate(ops):
        if op == omit:
            continue
        vec = [
            (0.11 + 0.047 * (op_index + 1) + 0.013 * axis) % base.TAU
            for axis in range(base.DIM)
        ]
        lines.append(
            json.dumps(
                {
                    "schema": "PHASENAV_OPERATOR_VECTOR_V1",
                    "operator_name": op,
                    "orbit_vector": vec,
                },
                separators=(",", ":"),
            )
        )
    (root / "phasenav/CIELINGO_PHASENAV_OPERATOR_VECTORS.noema.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return root


def test_binding_profile_covers_exact_bestiary_and_existing_operator_vocabulary_only():
    assert set(live.SPECIES_OPERATOR_BINDINGS) == set(base.SPECIES)
    assert all(live.SPECIES_OPERATOR_BINDINGS[s] for s in base.SPECIES)


def test_fixture_registry_loads_exact_finite_36d_vectors(tmp_path):
    root = make_surface(tmp_path)
    ops, provenance = live.load_live_operator_registry(
        root, require_canonical_root=False
    )
    assert ops
    assert all(len(v) == 36 for v in ops.values())
    assert all(0.0 <= x < base.TAU for v in ops.values() for x in v)
    assert provenance["static_runtime_fallback"] is False


@pytest.mark.parametrize("species", base.SPECIES)
def test_every_species_binds_to_explicit_operator_composition(tmp_path, species):
    root = make_surface(tmp_path)
    carrier, receipt = live.species_live_carrier(
        species, root, require_canonical_root=False
    )
    assert len(carrier) == 36
    assert all(0.0 <= x < base.TAU for x in carrier)
    assert receipt["species"] == species
    assert receipt["operators"] == list(live.SPECIES_OPERATOR_BINDINGS[species])
    assert receipt["binding_status"] == "CANDIDATE_EXPLICIT_OPERATOR_COMPOSITION"
    assert receipt["semantic_axis_assignment"] is False
    assert receipt["canon_allowed"] is False
    assert receipt["external_effects"] is False


def test_all_species_live_replay_runs_as_candidate_without_effects(tmp_path):
    root = make_surface(tmp_path)
    out = live.replay_all_live_species(root, steps=3, require_canonical_root=False)
    assert out["species_count"] == len(base.SPECIES)
    assert out["all_nonzero_displacement"] is True
    assert out["all_hybrid_realization_candidates"] is True
    assert out["all_species_carriers_unique"] is True
    assert len({r["carrier_sha256"] for r in out["results"]}) == len(base.SPECIES)
    assert out["fully_analog_physical_claim"] is False
    assert out["canon_allowed"] is False
    assert out["external_effects"] is False
    assert out["static_runtime_fallback"] is False
    assert {r["species"] for r in out["results"]} == set(base.SPECIES)


def test_missing_required_operator_fails_closed(tmp_path):
    root = make_surface(tmp_path, omit="MEMORY")
    with pytest.raises(base.PhaseGateError, match="missing"):
        live.species_live_carrier("RAVEN", root, require_canonical_root=False)


def test_inactive_binding_fails_closed(tmp_path):
    root = make_surface(tmp_path)
    (root / "ciel_binding_status").write_text("BLOCKED\n", encoding="utf-8")
    with pytest.raises(base.PhaseGateError, match="not ACTIVE"):
        live.load_live_phase_state(root, require_canonical_root=False)


def test_noncanonical_live_root_rejected_when_canonical_required(tmp_path):
    root = make_surface(tmp_path)
    with pytest.raises(base.PhaseGateError, match="/dev/shm/ciel_noema"):
        live.load_live_phase_state(root, require_canonical_root=True)


def test_phase_composition_rejects_antipodal_cancellation():
    a = [0.0] * base.DIM
    b = [math.pi] * base.DIM
    with pytest.raises(base.PhaseGateError, match="phase-antipodal"):
        live.compose_phase_carrier([a, b])
