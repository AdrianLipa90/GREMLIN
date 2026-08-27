from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_relational_lambda_holonomy_v08 import validate_qhtri_holonomy_lag_v08

HBAR_SI = 1.054_571_817e-34

COUPLING_SCHEMA = "GREMLIN_RELATIONAL_COUPLING_ENERGY_V0_9"
COUPLING_DOMAIN = b"GREMLIN-RELATIONAL-COUPLING-ENERGY/v0.9\x00"
HAMILTONIAN_SCHEMA = "GREMLIN_RELATIONAL_PHASED_EXCHANGE_HAMILTONIAN_V0_9"
HAMILTONIAN_DOMAIN = b"GREMLIN-RELATIONAL-PHASED-EXCHANGE-HAMILTONIAN/v0.9\x00"
PAIR_WITNESS_SCHEMA = "GREMLIN_RELATIONAL_PAIR_ENTANGLEMENT_WITNESS_V0_9"
PAIR_WITNESS_DOMAIN = b"GREMLIN-RELATIONAL-PAIR-ENTANGLEMENT-WITNESS/v0.9\x00"


class RelationalHamiltonianEntanglementError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    text = str(value)
    if not text:
        raise RelationalHamiltonianEntanglementError(f"{name} must be non-empty")
    return text


def _finite(value: Any, name: str) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise RelationalHamiltonianEntanglementError(f"{name} must be finite")
    return x


def _nonnegative(value: Any, name: str) -> float:
    x = _finite(value, name)
    if x < 0.0:
        raise RelationalHamiltonianEntanglementError(f"{name} must be non-negative")
    return x


def _hash64(value: Any, name: str) -> str:
    text = _nonempty(value, name)
    if len(text) != 64:
        raise RelationalHamiltonianEntanglementError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise RelationalHamiltonianEntanglementError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise RelationalHamiltonianEntanglementError(f"{name} must be a binary64 hex float") from exc
    return _finite(x, name)


def _complex_packet(z: complex) -> dict[str, str]:
    return {"re_f64_hex": float(z.real).hex(), "im_f64_hex": float(z.imag).hex()}


def _complex_from_packet(packet: Mapping[str, Any], name: str) -> complex:
    if not isinstance(packet, Mapping):
        raise RelationalHamiltonianEntanglementError(f"{name} must be a complex packet")
    return complex(
        _from_hex(packet.get("re_f64_hex"), f"{name}.real"),
        _from_hex(packet.get("im_f64_hex"), f"{name}.imag"),
    )


def build_relational_coupling_energy_v09(
    *,
    qhtri_binding: Mapping[str, Any],
    coupling_J_joule: Any,
    source_ref: str,
    source_commitment: str,
    epistemic_status: str,
    interaction_model_id: str = "HOLONOMY_PHASED_EXCHANGE_V1",
) -> dict[str, Any]:
    validate_qhtri_holonomy_lag_v08(qhtri_binding)
    J = _finite(coupling_J_joule, "coupling_J_joule")
    epsilon = _from_hex(qhtri_binding["epsilon_qhtri_rad_f64_hex"], "epsilon_qhtri")
    tau = _from_hex(qhtri_binding["tau_holonomy_rad_f64_hex"], "tau_holonomy")
    potential_energy = -J * math.cos(epsilon)
    phase_gradient_energy = -J * math.sin(epsilon)
    core = {
        "schema": COUPLING_SCHEMA,
        "relation_id": str(qhtri_binding["relation_id"]),
        "oscillator_i": str(qhtri_binding["oscillator_i"]),
        "oscillator_j": str(qhtri_binding["oscillator_j"]),
        "qhtri_holonomy_lag_commitment": str(qhtri_binding["qhtri_holonomy_lag_commitment"]),
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "epsilon_qhtri_rad_f64_hex": epsilon.hex(),
        "coupling_J_joule_f64_hex": J.hex(),
        "qhtri_potential_energy_joule_f64_hex": potential_energy.hex(),
        "qhtri_phase_gradient_energy_joule_f64_hex": phase_gradient_energy.hex(),
        "potential_law": "V_ij=-J_ij*cos(epsilon_ij)",
        "phase_gradient_law": "dV/dphase=-J_ij*sin(epsilon_ij)",
        "interaction_model_id": _nonempty(interaction_model_id, "interaction_model_id"),
        "source_ref": _nonempty(source_ref, "source_ref"),
        "source_commitment": _hash64(source_commitment, "source_commitment"),
        "epistemic_status": _nonempty(epistemic_status, "epistemic_status"),
        "coupling_energy_scale_status": "BOUND_MODEL_PARAMETER",
        "hamiltonian_realization_status": "READY_MODEL",
        "physical_interaction_identification_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_COUPLING_ENERGY_BOUND",
    }
    return {**core, "relational_coupling_energy_commitment": _seal(COUPLING_DOMAIN, core)}


def validate_relational_coupling_energy_v09(binding: Mapping[str, Any]) -> bool:
    if binding.get("schema") != COUPLING_SCHEMA:
        raise RelationalHamiltonianEntanglementError("unsupported relational coupling-energy schema")
    for key in ("relation_id", "oscillator_i", "oscillator_j", "interaction_model_id", "source_ref", "epistemic_status"):
        _nonempty(binding.get(key), key)
    _hash64(binding.get("qhtri_holonomy_lag_commitment"), "qhtri_holonomy_lag_commitment")
    _hash64(binding.get("source_commitment"), "source_commitment")
    tau = _from_hex(binding.get("tau_holonomy_rad_f64_hex"), "tau_holonomy")
    epsilon = _from_hex(binding.get("epsilon_qhtri_rad_f64_hex"), "epsilon_qhtri")
    J = _from_hex(binding.get("coupling_J_joule_f64_hex"), "coupling_J_joule")
    expected_potential = -J * math.cos(epsilon)
    expected_gradient = -J * math.sin(epsilon)
    if _from_hex(binding.get("qhtri_potential_energy_joule_f64_hex"), "qhtri_potential_energy").hex() != expected_potential.hex():
        raise RelationalHamiltonianEntanglementError("QHTRI potential energy mismatch")
    if _from_hex(binding.get("qhtri_phase_gradient_energy_joule_f64_hex"), "qhtri_phase_gradient_energy").hex() != expected_gradient.hex():
        raise RelationalHamiltonianEntanglementError("QHTRI phase-gradient energy mismatch")
    if not math.isfinite(tau):
        raise RelationalHamiltonianEntanglementError("holonomy phase must be finite")
    if binding.get("potential_law") != "V_ij=-J_ij*cos(epsilon_ij)" or binding.get("phase_gradient_law") != "dV/dphase=-J_ij*sin(epsilon_ij)":
        raise RelationalHamiltonianEntanglementError("coupling-energy law mismatch")
    expected = {
        "coupling_energy_scale_status": "BOUND_MODEL_PARAMETER",
        "hamiltonian_realization_status": "READY_MODEL",
        "physical_interaction_identification_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_COUPLING_ENERGY_BOUND",
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise RelationalHamiltonianEntanglementError(f"coupling-energy status mismatch: {key}")
    supplied = _hash64(binding.get("relational_coupling_energy_commitment"), "relational_coupling_energy_commitment")
    core = dict(binding)
    core.pop("relational_coupling_energy_commitment", None)
    if supplied != _seal(COUPLING_DOMAIN, core):
        raise RelationalHamiltonianEntanglementError("relational coupling-energy commitment mismatch")
    return True


def build_phased_exchange_hamiltonian_v09(*, coupling: Mapping[str, Any]) -> dict[str, Any]:
    validate_relational_coupling_energy_v09(coupling)
    J = _from_hex(coupling["coupling_J_joule_f64_hex"], "coupling_J_joule")
    tau = _from_hex(coupling["tau_holonomy_rad_f64_hex"], "tau_holonomy")
    h_01_10 = J * cmath.exp(-1j * tau)
    h_10_01 = h_01_10.conjugate()
    core = {
        "schema": HAMILTONIAN_SCHEMA,
        "relation_id": str(coupling["relation_id"]),
        "oscillator_i": str(coupling["oscillator_i"]),
        "oscillator_j": str(coupling["oscillator_j"]),
        "relational_coupling_energy_commitment": str(coupling["relational_coupling_energy_commitment"]),
        "basis": ["|01>", "|10>"],
        "H_01_01_joule": _complex_packet(0j),
        "H_01_10_joule": _complex_packet(h_01_10),
        "H_10_01_joule": _complex_packet(h_10_01),
        "H_10_10_joule": _complex_packet(0j),
        "hamiltonian_law": "H_rel=J*(exp(-i*tau)|01><10|+exp(i*tau)|10><01|)",
        "hermiticity_status": "EXACT_BY_CONSTRUCTION",
        "holonomy_role": "RELATIONAL_EXCHANGE_PHASE",
        "interaction_status": "MODEL_HAMILTONIAN_BOUND",
        "physical_interaction_identification_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_PHASED_EXCHANGE_HAMILTONIAN_BOUND",
    }
    return {**core, "relational_hamiltonian_commitment": _seal(HAMILTONIAN_DOMAIN, core)}


def validate_phased_exchange_hamiltonian_v09(hamiltonian: Mapping[str, Any]) -> bool:
    if hamiltonian.get("schema") != HAMILTONIAN_SCHEMA:
        raise RelationalHamiltonianEntanglementError("unsupported relational Hamiltonian schema")
    for key in ("relation_id", "oscillator_i", "oscillator_j"):
        _nonempty(hamiltonian.get(key), key)
    _hash64(hamiltonian.get("relational_coupling_energy_commitment"), "relational_coupling_energy_commitment")
    if hamiltonian.get("basis") != ["|01>", "|10>"]:
        raise RelationalHamiltonianEntanglementError("exchange Hamiltonian basis mismatch")
    d0 = _complex_from_packet(hamiltonian.get("H_01_01_joule"), "H_01_01")
    d1 = _complex_from_packet(hamiltonian.get("H_10_10_joule"), "H_10_10")
    a = _complex_from_packet(hamiltonian.get("H_01_10_joule"), "H_01_10")
    b = _complex_from_packet(hamiltonian.get("H_10_01_joule"), "H_10_01")
    if d0 != 0j or d1 != 0j or b != a.conjugate():
        raise RelationalHamiltonianEntanglementError("exchange Hamiltonian hermiticity mismatch")
    if hamiltonian.get("hamiltonian_law") != "H_rel=J*(exp(-i*tau)|01><10|+exp(i*tau)|10><01|)":
        raise RelationalHamiltonianEntanglementError("exchange Hamiltonian law mismatch")
    expected = {
        "hermiticity_status": "EXACT_BY_CONSTRUCTION",
        "holonomy_role": "RELATIONAL_EXCHANGE_PHASE",
        "interaction_status": "MODEL_HAMILTONIAN_BOUND",
        "physical_interaction_identification_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_PHASED_EXCHANGE_HAMILTONIAN_BOUND",
    }
    for key, value in expected.items():
        if hamiltonian.get(key) != value:
            raise RelationalHamiltonianEntanglementError(f"Hamiltonian status mismatch: {key}")
    supplied = _hash64(hamiltonian.get("relational_hamiltonian_commitment"), "relational_hamiltonian_commitment")
    core = dict(hamiltonian)
    core.pop("relational_hamiltonian_commitment", None)
    if supplied != _seal(HAMILTONIAN_DOMAIN, core):
        raise RelationalHamiltonianEntanglementError("relational Hamiltonian commitment mismatch")
    return True


def build_pair_entanglement_witness_v09(
    *,
    coupling: Mapping[str, Any],
    hamiltonian: Mapping[str, Any],
    interaction_time_s: Any,
    initial_state: str = "|10>",
) -> dict[str, Any]:
    validate_relational_coupling_energy_v09(coupling)
    validate_phased_exchange_hamiltonian_v09(hamiltonian)
    if hamiltonian["relational_coupling_energy_commitment"] != coupling["relational_coupling_energy_commitment"]:
        raise RelationalHamiltonianEntanglementError("Hamiltonian/coupling lineage mismatch")
    if initial_state != "|10>":
        raise RelationalHamiltonianEntanglementError("v0.9 pair witness currently binds the |10> initial-state contract")
    t = _nonnegative(interaction_time_s, "interaction_time_s")
    J = _from_hex(coupling["coupling_J_joule_f64_hex"], "coupling_J_joule")
    tau = _from_hex(coupling["tau_holonomy_rad_f64_hex"], "tau_holonomy")
    alpha = J * t / HBAR_SI
    a_01 = -1j * cmath.exp(-1j * tau) * math.sin(alpha)
    a_10 = complex(math.cos(alpha), 0.0)
    norm = abs(a_01) ** 2 + abs(a_10) ** 2
    concurrence = 2.0 * abs(a_01 * a_10)
    reduced_purity = abs(a_01) ** 4 + abs(a_10) ** 4
    witness_state = "ENTANGLED_MODEL_WITNESS" if concurrence > 1e-12 else "SEPARABLE_MODEL_SAMPLE"
    core = {
        "schema": PAIR_WITNESS_SCHEMA,
        "relation_id": str(coupling["relation_id"]),
        "oscillator_i": str(coupling["oscillator_i"]),
        "oscillator_j": str(coupling["oscillator_j"]),
        "relational_coupling_energy_commitment": str(coupling["relational_coupling_energy_commitment"]),
        "relational_hamiltonian_commitment": str(hamiltonian["relational_hamiltonian_commitment"]),
        "initial_state": initial_state,
        "interaction_time_s_f64_hex": t.hex(),
        "alpha_Jt_over_hbar_f64_hex": alpha.hex(),
        "amplitude_01": _complex_packet(a_01),
        "amplitude_10": _complex_packet(a_10),
        "state_law": "|psi(t)>=cos(alpha)|10>-i*exp(-i*tau)*sin(alpha)|01>",
        "state_norm_f64_hex": norm.hex(),
        "pure_state_concurrence_f64_hex": concurrence.hex(),
        "reduced_single_mode_purity_f64_hex": reduced_purity.hex(),
        "entanglement_witness_state": witness_state,
        "holonomy_role": "RELATIONAL_STATE_PHASE",
        "exchange_energy_role": "ENTANGLING_DYNAMICS_MODEL_PARAMETER",
        "witness_scope": "TWO_MODE_MODEL_LEVEL",
        "physical_neutrino_pair_validation_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_PAIR_ENTANGLEMENT_WITNESS_BOUND",
    }
    return {**core, "pair_entanglement_witness_commitment": _seal(PAIR_WITNESS_DOMAIN, core)}


def validate_pair_entanglement_witness_v09(witness: Mapping[str, Any]) -> bool:
    if witness.get("schema") != PAIR_WITNESS_SCHEMA:
        raise RelationalHamiltonianEntanglementError("unsupported pair-entanglement witness schema")
    for key in ("relation_id", "oscillator_i", "oscillator_j"):
        _nonempty(witness.get(key), key)
    _hash64(witness.get("relational_coupling_energy_commitment"), "relational_coupling_energy_commitment")
    _hash64(witness.get("relational_hamiltonian_commitment"), "relational_hamiltonian_commitment")
    if witness.get("initial_state") != "|10>":
        raise RelationalHamiltonianEntanglementError("pair witness initial-state contract mismatch")
    t = _nonnegative(_from_hex(witness.get("interaction_time_s_f64_hex"), "interaction_time_s"), "interaction_time_s")
    alpha = _from_hex(witness.get("alpha_Jt_over_hbar_f64_hex"), "alpha_Jt_over_hbar")
    a_01 = _complex_from_packet(witness.get("amplitude_01"), "amplitude_01")
    a_10 = _complex_from_packet(witness.get("amplitude_10"), "amplitude_10")
    norm = abs(a_01) ** 2 + abs(a_10) ** 2
    concurrence = 2.0 * abs(a_01 * a_10)
    reduced_purity = abs(a_01) ** 4 + abs(a_10) ** 4
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise RelationalHamiltonianEntanglementError("pair witness state normalization mismatch")
    if not math.isclose(_from_hex(witness.get("state_norm_f64_hex"), "state_norm"), norm, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored pair witness norm mismatch")
    if not math.isclose(_from_hex(witness.get("pure_state_concurrence_f64_hex"), "concurrence"), concurrence, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored concurrence mismatch")
    if not math.isclose(_from_hex(witness.get("reduced_single_mode_purity_f64_hex"), "reduced_purity"), reduced_purity, rel_tol=0.0, abs_tol=1e-15):
        raise RelationalHamiltonianEntanglementError("stored reduced purity mismatch")
    expected_state = "ENTANGLED_MODEL_WITNESS" if concurrence > 1e-12 else "SEPARABLE_MODEL_SAMPLE"
    if witness.get("entanglement_witness_state") != expected_state:
        raise RelationalHamiltonianEntanglementError("entanglement witness classification mismatch")
    if witness.get("state_law") != "|psi(t)>=cos(alpha)|10>-i*exp(-i*tau)*sin(alpha)|01>":
        raise RelationalHamiltonianEntanglementError("pair witness state law mismatch")
    expected = {
        "holonomy_role": "RELATIONAL_STATE_PHASE",
        "exchange_energy_role": "ENTANGLING_DYNAMICS_MODEL_PARAMETER",
        "witness_scope": "TWO_MODE_MODEL_LEVEL",
        "physical_neutrino_pair_validation_status": "OPEN",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "RELATIONAL_PAIR_ENTANGLEMENT_WITNESS_BOUND",
    }
    for key, value in expected.items():
        if witness.get(key) != value:
            raise RelationalHamiltonianEntanglementError(f"pair witness status mismatch: {key}")
    _ = t, alpha
    supplied = _hash64(witness.get("pair_entanglement_witness_commitment"), "pair_entanglement_witness_commitment")
    core = dict(witness)
    core.pop("pair_entanglement_witness_commitment", None)
    if supplied != _seal(PAIR_WITNESS_DOMAIN, core):
        raise RelationalHamiltonianEntanglementError("pair entanglement witness commitment mismatch")
    return True
