from __future__ import annotations

import cmath
import math
from typing import Any, Mapping

from tools.gremlin_relational_hamiltonian_entanglement_v09 import (
    HBAR_SI,
    RelationalHamiltonianEntanglementError,
    validate_pair_entanglement_witness_v09,
    validate_phased_exchange_hamiltonian_v09,
    validate_relational_coupling_energy_v09,
)


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise RelationalHamiltonianEntanglementError(f"{name} must be a binary64 hex float") from exc
    if not math.isfinite(x):
        raise RelationalHamiltonianEntanglementError(f"{name} must be finite")
    return x


def _complex(packet: Mapping[str, Any], name: str) -> complex:
    if not isinstance(packet, Mapping):
        raise RelationalHamiltonianEntanglementError(f"{name} must be a complex packet")
    return complex(
        _from_hex(packet.get("re_f64_hex"), f"{name}.real"),
        _from_hex(packet.get("im_f64_hex"), f"{name}.imag"),
    )


def validate_entanglement_lineage_v09(
    *,
    coupling: Mapping[str, Any],
    hamiltonian: Mapping[str, Any],
    witness: Mapping[str, Any],
) -> bool:
    """Recompute the v0.9 model witness from the bound J, tau and interaction time."""
    validate_relational_coupling_energy_v09(coupling)
    validate_phased_exchange_hamiltonian_v09(hamiltonian)
    validate_pair_entanglement_witness_v09(witness)

    c_commit = str(coupling["relational_coupling_energy_commitment"])
    h_commit = str(hamiltonian["relational_hamiltonian_commitment"])
    if hamiltonian.get("relational_coupling_energy_commitment") != c_commit:
        raise RelationalHamiltonianEntanglementError("Hamiltonian/coupling lineage mismatch")
    if witness.get("relational_coupling_energy_commitment") != c_commit:
        raise RelationalHamiltonianEntanglementError("witness/coupling lineage mismatch")
    if witness.get("relational_hamiltonian_commitment") != h_commit:
        raise RelationalHamiltonianEntanglementError("witness/Hamiltonian lineage mismatch")

    J = _from_hex(coupling["coupling_J_joule_f64_hex"], "coupling_J_joule")
    tau = _from_hex(coupling["tau_holonomy_rad_f64_hex"], "tau_holonomy")
    t = _from_hex(witness["interaction_time_s_f64_hex"], "interaction_time_s")
    if t < 0.0:
        raise RelationalHamiltonianEntanglementError("interaction_time_s must be non-negative")

    expected_h_01_10 = J * cmath.exp(-1j * tau)
    expected_h_10_01 = expected_h_01_10.conjugate()
    if _complex(hamiltonian["H_01_10_joule"], "H_01_10") != expected_h_01_10:
        raise RelationalHamiltonianEntanglementError("Hamiltonian off-diagonal term does not match bound J and tau")
    if _complex(hamiltonian["H_10_01_joule"], "H_10_01") != expected_h_10_01:
        raise RelationalHamiltonianEntanglementError("Hamiltonian conjugate term does not match bound J and tau")

    alpha = J * t / HBAR_SI
    expected_a01 = -1j * cmath.exp(-1j * tau) * math.sin(alpha)
    expected_a10 = complex(math.cos(alpha), 0.0)
    actual_a01 = _complex(witness["amplitude_01"], "amplitude_01")
    actual_a10 = _complex(witness["amplitude_10"], "amplitude_10")

    if not cmath.isclose(actual_a01, expected_a01, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("witness amplitude_01 does not match J/tau/time evolution")
    if not cmath.isclose(actual_a10, expected_a10, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("witness amplitude_10 does not match J/time evolution")

    stored_alpha = _from_hex(witness["alpha_Jt_over_hbar_f64_hex"], "alpha_Jt_over_hbar")
    if not math.isclose(stored_alpha, alpha, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored alpha does not match J*t/hbar")

    expected_concurrence = 2.0 * abs(expected_a01 * expected_a10)
    stored_concurrence = _from_hex(witness["pure_state_concurrence_f64_hex"], "concurrence")
    if not math.isclose(stored_concurrence, expected_concurrence, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored concurrence does not match bound dynamics")

    expected_purity = abs(expected_a01) ** 4 + abs(expected_a10) ** 4
    stored_purity = _from_hex(witness["reduced_single_mode_purity_f64_hex"], "reduced_purity")
    if not math.isclose(stored_purity, expected_purity, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored reduced purity does not match bound dynamics")

    expected_state = "ENTANGLED_MODEL_WITNESS" if expected_concurrence > 1e-12 else "SEPARABLE_MODEL_SAMPLE"
    if witness.get("entanglement_witness_state") != expected_state:
        raise RelationalHamiltonianEntanglementError("entanglement classification does not match bound dynamics")
    return True
