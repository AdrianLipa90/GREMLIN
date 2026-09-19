from __future__ import annotations

import math

import pytest

from gremlin_mcp.spectroscopic_holonomy import (
    build_spectroscopic_inverse_plan,
    validate_phasenav_spectroscopic_packet,
)


def _packet(*, beta_1: int = 1) -> dict:
    if beta_1 == 0:
        return {
            "schema": "PHASENAV_SPECTROSCOPIC_HOLONOMY_STATE_V0_1",
            "version": "0.1.0",
            "epistemic": "CHYBA",
            "canon_allowed": False,
            "graph": {
                "vertex_count": 4,
                "edge_count": 3,
                "component_count": 1,
                "beta_1": 0,
            },
            "cycle_edge_potentials": [],
            "cycle_phases": [],
            "cycle_holonomies": [],
            "claims": {
                "computational_graph_holonomy": True,
                "physical_gauge_field": False,
                "physical_substrate": False,
                "physical_nonlocal_signalling": False,
                "hypercharge_identification": False,
                "weak_boson_identification": False,
            },
        }
    phi = 0.40
    return {
        "schema": "PHASENAV_SPECTROSCOPIC_HOLONOMY_STATE_V0_1",
        "version": "0.1.0",
        "epistemic": "CHYBA",
        "canon_allowed": False,
        "graph": {
            "vertex_count": 6,
            "edge_count": 6,
            "component_count": 1,
            "beta_1": 1,
        },
        "cycle_edge_potentials": [[0.20, 0.35, -0.15]],
        "cycle_phases": [phi],
        "cycle_holonomies": [
            {
                "real": math.cos(phi),
                "imag": math.sin(phi),
                "modulus": 1.0,
            }
        ],
        "claims": {
            "computational_graph_holonomy": True,
            "physical_gauge_field": False,
            "physical_substrate": False,
            "physical_nonlocal_signalling": False,
            "hypercharge_identification": False,
            "weak_boson_identification": False,
        },
    }


def test_validator_accepts_typed_unit_modulus_packet() -> None:
    validated = validate_phasenav_spectroscopic_packet(_packet())
    assert validated["graph"]["beta_1"] == 1
    assert validated["epistemic"] == "CHYBA"
    assert validated["canon_allowed"] is False
    assert len(validated["packet_commitment_sha256"]) == 64


def test_inverse_plan_uses_existing_bestiary_without_new_species() -> None:
    plan = build_spectroscopic_inverse_plan(
        _packet(),
        ["line_position", "cross_peak_phase", "coherence_time"],
    )
    assert plan["status"] == "CANDIDATE_PLAN"
    assert plan["inverse_problem"]["unknowns"] == ["Phi_1"]
    assert plan["inverse_problem"]["expected_jacobian_shape"] == [3, 1]
    assert plan["inverse_problem"]["expected_fisher_shape"] == [1, 1]
    assert plan["species_union"] == [
        "SPIDER",
        "ANT",
        "BAT",
        "MOLE",
        "HOUND",
        "OWL",
        "MANTIS",
        "BELZEBUB",
    ]
    assert plan["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "raphael_decree_required_for_mutation": True,
    }


def test_plan_commitment_is_deterministic() -> None:
    packet = _packet()
    observables = ["line_position", "intensity"]
    a = build_spectroscopic_inverse_plan(packet, observables)
    b = build_spectroscopic_inverse_plan(packet, observables)
    assert a["plan_commitment_sha256"] == b["plan_commitment_sha256"]
    assert a["phasenav_packet"]["packet_commitment_sha256"] == b["phasenav_packet"]["packet_commitment_sha256"]


def test_tree_control_has_no_phase_inverse_problem() -> None:
    plan = build_spectroscopic_inverse_plan(_packet(beta_1=0), ["line_position"])
    inverse = plan["inverse_problem"]
    assert inverse["unknown_count"] == 0
    assert inverse["tree_control"] is True
    assert inverse["tree_phase_parameter_forbidden"] is True
    assert inverse["rank_gate"] == "NO_PHASE_INVERSE_PROBLEM_FOR_TREE"


def test_fail_closed_on_beta_mismatch_or_physical_claim_promotion() -> None:
    bad_beta = _packet()
    bad_beta["graph"]["beta_1"] = 2
    with pytest.raises(ValueError):
        validate_phasenav_spectroscopic_packet(bad_beta)

    bad_claim = _packet()
    bad_claim["claims"]["physical_gauge_field"] = True
    with pytest.raises(ValueError):
        validate_phasenav_spectroscopic_packet(bad_claim)
