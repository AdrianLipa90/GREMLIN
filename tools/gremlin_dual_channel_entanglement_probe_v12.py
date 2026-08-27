from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.gremlin_joint_quantum_witness_v10 import (
    HBAR_SI,
    build_joint_pure_state_v10,
    build_zz_coupling_evolution_v10,
    validate_zz_coupling_evolution_v10,
)
from tools.gremlin_relational_coupling_energy_v11 import (
    validate_relational_coupling_energy_partition_v11,
)
from tools.gremlin_relational_lambda_holonomy_v08 import validate_relational_lambda_energy_v08
from tools.gremlin_connection_path_holonomy_v09 import (
    validate_connection_path_integral_v09,
    validate_qhtri_connection_derived_lag_v09,
)

PROBE_SCHEMA = "GREMLIN_DUAL_CHANNEL_ENTANGLEMENT_PROBE_V1_2"
PROBE_DOMAIN = b"GREMLIN-DUAL-CHANNEL-ENTANGLEMENT-PROBE/v1.2\x00"


class DualChannelEntanglementProbeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, value: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise DualChannelEntanglementProbeError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise DualChannelEntanglementProbeError(f"{name} must be hexadecimal") from exc
    return text


def _from_hex(value: Any, name: str) -> float:
    try:
        x = float.fromhex(str(value))
    except (TypeError, ValueError) as exc:
        raise DualChannelEntanglementProbeError(f"{name} must be a binary64 hex float") from exc
    if not math.isfinite(x):
        raise DualChannelEntanglementProbeError(f"{name} must be finite")
    return x


def _channel_time(j: float) -> tuple[str, float | None]:
    if j == 0.0:
        return "UNREACHABLE_UNDER_ZERO_CHANNEL_COUPLING", None
    return "FINITE_FIRST_MAXIMUM", (math.pi * HBAR_SI) / (4.0 * abs(j))


def _encoded_optional_float(value: float | None) -> str | None:
    return None if value is None else value.hex()


def build_dual_channel_entanglement_probe_v12(
    *,
    qhtri_receipt: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> dict[str, Any]:
    validate_qhtri_connection_derived_lag_v09(qhtri_receipt)
    validate_relational_lambda_energy_v08(energy)
    validate_connection_path_integral_v09(path)
    validate_relational_coupling_energy_partition_v11(partition, energy=energy, path=path)

    if str(qhtri_receipt["qhtri_holonomy_lag_v08"]["relation_id"]) != str(energy["relation_id"]):
        raise DualChannelEntanglementProbeError("QHTRI and Lambda-energy relation lineage mismatch")
    if str(qhtri_receipt["qhtri_holonomy_lag_v08"]["loop_id"]) != str(path["loop_id"]):
        raise DualChannelEntanglementProbeError("QHTRI and connection-path loop lineage mismatch")

    source_energy = _from_hex(partition["source_energy_j_f64_hex"], "source_energy")
    if source_energy == 0.0:
        raise DualChannelEntanglementProbeError("dual-channel diagnostic requires non-zero source energy")

    j_c = _from_hex(partition["coherence_channel_J_C_j_f64_hex"], "J_C")
    j_d = _from_hex(partition["torsion_channel_J_D_j_f64_hex"], "J_D")
    c_h = _from_hex(partition["coherence_C_h_f64_hex"], "C_h")
    d_h = _from_hex(partition["torsion_D_h_f64_hex"], "D_h")
    tau = _from_hex(partition["tau_holonomy_rad_f64_hex"], "tau_holonomy")

    diagnostic_state = build_joint_pure_state_v10(
        qhtri_receipt=qhtri_receipt,
        amplitudes=[0.5, 0.5, 0.5, 0.5],
        source_ref="diagnostic:equal-superposition-product-state",
        epistemic_status="MODEL_DIAGNOSTIC",
    )

    source_quarter_action_time = (math.pi * HBAR_SI) / (4.0 * abs(source_energy))
    coupling_commitment = _hash64(
        partition["relational_coupling_energy_commitment"],
        "relational_coupling_energy_commitment",
    )

    evolution_c = build_zz_coupling_evolution_v10(
        initial_state=diagnostic_state,
        coupling_energy_j=j_c,
        duration_s=source_quarter_action_time,
        coupling_source_ref="v1.1:COHERENCE_CHANNEL",
        coupling_source_commitment=coupling_commitment,
        coupling_epistemic_status="RELATIONAL_ENERGY_CHANNEL_CANDIDATE",
    )
    evolution_d = build_zz_coupling_evolution_v10(
        initial_state=diagnostic_state,
        coupling_energy_j=j_d,
        duration_s=source_quarter_action_time,
        coupling_source_ref="v1.1:TORSION_CHANNEL",
        coupling_source_commitment=coupling_commitment,
        coupling_epistemic_status="RELATIONAL_ENERGY_CHANNEL_CANDIDATE",
    )

    validate_zz_coupling_evolution_v10(evolution_c, initial_state=diagnostic_state)
    validate_zz_coupling_evolution_v10(evolution_d, initial_state=diagnostic_state)

    c_probe = _from_hex(evolution_c["final_concurrence_f64_hex"], "coherence_probe_concurrence")
    d_probe = _from_hex(evolution_d["final_concurrence_f64_hex"], "torsion_probe_concurrence")

    c_time_status, c_time = _channel_time(j_c)
    d_time_status, d_time = _channel_time(j_d)
    if c_time is None and d_time is None:
        rate_order = "NO_ENTANGLING_RATE"
    elif d_time is None or (c_time is not None and c_time < d_time):
        rate_order = "COHERENCE_CHANNEL_FASTER"
    elif c_time is None or (d_time is not None and d_time < c_time):
        rate_order = "TORSION_CHANNEL_FASTER"
    else:
        rate_order = "DEGENERATE_EQUAL_RATE"

    core = {
        "schema": PROBE_SCHEMA,
        "relation_id": str(energy["relation_id"]),
        "loop_id": str(path["loop_id"]),
        "qhtri_connection_derived_commitment": str(qhtri_receipt["qhtri_connection_derived_commitment"]),
        "relational_coupling_energy_commitment": coupling_commitment,
        "diagnostic_initial_state_commitment": str(diagnostic_state["joint_state_commitment"]),
        "tau_holonomy_rad_f64_hex": tau.hex(),
        "coherence_C_h_f64_hex": c_h.hex(),
        "torsion_D_h_f64_hex": d_h.hex(),
        "coherence_channel_J_C_j_f64_hex": j_c.hex(),
        "torsion_channel_J_D_j_f64_hex": j_d.hex(),
        "diagnostic_state": "PRODUCT_EQUAL_SUPERPOSITION_|+>|+>",
        "diagnostic_hamiltonian": "H_k=J_k*(sigma_z tensor sigma_z)",
        "source_quarter_action_time_s_f64_hex": source_quarter_action_time.hex(),
        "source_quarter_action_law": "t_Q=pi*hbar/(4*abs(E_R))",
        "coherence_probe_concurrence_f64_hex": c_probe.hex(),
        "torsion_probe_concurrence_f64_hex": d_probe.hex(),
        "coherence_probe_law": "C_C(t_Q)=abs(sin((pi/2)*C_h))",
        "torsion_probe_law": "C_D(t_Q)=abs(sin((pi/2)*D_h))",
        "coherence_first_maximum_status": c_time_status,
        "torsion_first_maximum_status": d_time_status,
        "coherence_first_maximum_time_s_f64_hex": _encoded_optional_float(c_time),
        "torsion_first_maximum_time_s_f64_hex": _encoded_optional_float(d_time),
        "first_maximum_law": "t_max,k=pi*hbar/(4*abs(J_k)) for J_k!=0",
        "geometry_rate_ordering": rate_order,
        "embedded_coherence_evolution": evolution_c,
        "embedded_torsion_evolution": evolution_d,
        "channel_selection_status": "OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW",
        "rate_ordering_is_channel_selection": False,
        "synchronization_entanglement_equivalence": False,
        "lambda_holonomy_to_channel_energy_status": "DERIVED_AS_V1_1_CANDIDATE_PARTITION",
        "execution_status": "RESEARCH_BINDING_ONLY",
        "canon_status": "CANDIDATE",
        "status": "DUAL_CHANNEL_ENTANGLEMENT_DIAGNOSTIC_ASSESSED",
    }
    return {**core, "dual_channel_entanglement_probe_commitment": _seal(PROBE_DOMAIN, core)}


def validate_dual_channel_entanglement_probe_v12(
    receipt: Mapping[str, Any],
    *,
    qhtri_receipt: Mapping[str, Any],
    energy: Mapping[str, Any],
    path: Mapping[str, Any],
    partition: Mapping[str, Any],
) -> bool:
    expected = build_dual_channel_entanglement_probe_v12(
        qhtri_receipt=qhtri_receipt,
        energy=energy,
        path=path,
        partition=partition,
    )
    if receipt.get("schema") != PROBE_SCHEMA:
        raise DualChannelEntanglementProbeError("unsupported dual-channel entanglement probe schema")
    for key, value in expected.items():
        if key == "dual_channel_entanglement_probe_commitment":
            continue
        if receipt.get(key) != value:
            raise DualChannelEntanglementProbeError(f"dual-channel probe mismatch: {key}")
    supplied = _hash64(
        receipt.get("dual_channel_entanglement_probe_commitment"),
        "dual_channel_entanglement_probe_commitment",
    )
    core = dict(receipt)
    core.pop("dual_channel_entanglement_probe_commitment", None)
    if supplied != _seal(PROBE_DOMAIN, core):
        raise DualChannelEntanglementProbeError("dual-channel probe commitment mismatch")
    return True
