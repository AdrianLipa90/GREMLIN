from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA = "GREMLIN_MCP_PHASENAV_RUNTIME_V0_2"
VERSION = "0.2.0"


def status() -> dict[str, Any]:
    """Describe the standalone PhaseNav Bestiary runtime surface.

    The computational/vector paths are independent of a live NOEMA surface.
    Live replay is optional and fails closed when /dev/shm/ciel_noema is absent
    or inactive.
    """
    from tools.gremlin_bestiary_phasenav_phase_gates_v02 import (
        DIM,
        SPECIES,
        phase_gate_vectorization_manifest,
    )

    manifest = phase_gate_vectorization_manifest()
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "standalone": True,
        "dimension": DIM,
        "space": "T^36",
        "species": list(SPECIES),
        "species_count": len(SPECIES),
        "computational_reference_available": True,
        "vector_backend_available": bool(manifest["vectorized_batch_realization"]),
        "threeway_continuous_reference_available": True,
        "analog_invariant_suite_available": True,
        "full_bestiary_phase_carriers": True,
        "full_bestiary_phase_carrier_count": len(SPECIES),
        "arpl_phase_law_bound": True,
        "role_geometry": "CANDIDATE_10_ORTHOPLEX",
        "legacy_threeway_scope_species": 18,
        "legacy_analog_invariant_scope_species": 9,
        "spectroscopic_holonomy_packet_schema": "PHASENAV_SPECTROSCOPIC_HOLONOMY_STATE_V0_1",
        "spectroscopic_inverse_problem_available": True,
        "live_noema_required_for_core": False,
        "live_replay_optional": True,
        "live_replay_default_root": "/dev/shm/ciel_noema",
        "static_runtime_fallback": False,
        "external_effects": False,
        "canon_allowed": False,
        "physical_analog_claim": False,
    }


def reference_sweep() -> dict[str, Any]:
    """Run all 20 roles through the ARPL-bound reference phase layer."""
    from tools.gremlin_bestiary_phasenav_phase_gates_v02 import (
        run_full_bestiary_reference_sweep,
    )

    return run_full_bestiary_reference_sweep()


def threeway(
    *,
    batch_size: int = 12,
    horizon: float = 0.8,
    coarse_steps: int = 8,
    fine_steps: int = 64,
    rk4_substeps: int = 256,
) -> dict[str, Any]:
    """Compare scalar, NumPy-vector and continuous T^36 realizations."""
    from tools.gremlin_bestiary_phasenav_threeway_v01 import run_threeway_suite

    return run_threeway_suite(
        batch_size=batch_size,
        horizon=horizon,
        coarse_steps=coarse_steps,
        fine_steps=fine_steps,
        rk4_substeps=rk4_substeps,
    )


def analog_invariants() -> dict[str, Any]:
    """Run specialist invariants for all current analog-core candidates."""
    from tools.gremlin_bestiary_phasenav_analog_invariants_v01 import (
        run_analog_invariant_suite,
    )

    return run_analog_invariant_suite()


def live_replay(
    *,
    surface_root: str = "/dev/shm/ciel_noema",
    steps: int = 1,
) -> dict[str, Any]:
    """Replay all 20 phase-armed roles against an explicit live PhaseNav surface.

    This path has no fallback. If the surface is absent, inactive or missing
    required existing operator vectors, the v0.2 live-binding adapter fails loud.
    """
    from tools.gremlin_bestiary_phasenav_live_binding_v02 import (
        replay_all_live_species,
    )

    return replay_all_live_species(
        Path(surface_root),
        steps=steps,
        require_canonical_root=(surface_root == "/dev/shm/ciel_noema"),
    )


def spectroscopic_holonomy(
    packet: dict[str, Any],
    observables: list[str],
) -> dict[str, Any]:
    """Validate a PhaseNav spectroscopic packet and build a read-only Bestiary plan."""
    from gremlin_mcp.spectroscopic_holonomy import build_spectroscopic_inverse_plan

    return build_spectroscopic_inverse_plan(packet, observables)
