from __future__ import annotations

from pathlib import Path
from typing import Any

SCHEMA = "GREMLIN_MCP_PHASENAV_RUNTIME_V0_1"
VERSION = "0.1.0"


def status() -> dict[str, Any]:
    """Describe the standalone PhaseNav Bestiary runtime surface.

    The computational/vector paths are independent of a live NOEMA surface.
    Live replay is optional and fails closed when /dev/shm/ciel_noema is absent
    or inactive.
    """
    from tools.gremlin_bestiary_phasenav_phase_gates_v01 import (
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
        "live_noema_required_for_core": False,
        "live_replay_optional": True,
        "live_replay_default_root": "/dev/shm/ciel_noema",
        "static_runtime_fallback": False,
        "external_effects": False,
        "canon_allowed": False,
        "physical_analog_claim": False,
    }


def reference_sweep() -> dict[str, Any]:
    """Run all 18 species through the dependency-free reference phase layer."""
    from tools.gremlin_bestiary_phasenav_phase_gates_v01 import (
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
    """Replay all species against an explicitly supplied live PhaseNav surface.

    This path has no fallback.  If the surface is absent, inactive or missing
    required vectors, the imported live-binding module raises fail loud.
    """
    from tools.gremlin_bestiary_phasenav_live_binding_v01 import (
        replay_all_live_species,
    )

    return replay_all_live_species(
        Path(surface_root),
        steps=steps,
        require_canonical_root=(surface_root == "/dev/shm/ciel_noema"),
    )
