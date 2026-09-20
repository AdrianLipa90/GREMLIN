"""GREMLIN relational measurement channel catalog v0.1.

Typed observable catalog plus exact response-chain helpers for orbital,
phase-optics, holonomy, Bogoliubov and spectroscopy channels.

The catalog does not invent source signatures and does not grant measurement
independence merely because two observables have different names.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np

from tools.gremlin_cross_modal_relational_evidence_v01 import (
    CrossModalEvidenceError,
    EvidenceProvenance,
)
from tools.gremlin_identifiability_measurement_design_v01 import (
    IndependentMeasurement,
    MeasurementSignature,
)


SCHEMA = "GREMLIN_RELATIONAL_MEASUREMENT_CHANNEL_CATALOG_V0_1"

SOURCE_SENSITIVE_CONDITIONAL = "SOURCE_SENSITIVE_CONDITIONAL"
NUISANCE_CONTROL = "NUISANCE_CONTROL"
MODEL_CONSISTENCY = "MODEL_CONSISTENCY"
CUSTOM_RESPONSE_REQUIRED = "CUSTOM_RESPONSE_REQUIRED"


class MeasurementChannelCatalogError(ValueError):
    pass


def _finite(name: str, value: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise MeasurementChannelCatalogError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise MeasurementChannelCatalogError(f"{name} must be finite")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0.0:
        raise MeasurementChannelCatalogError(f"{name} must be > 0")
    return value


def _vector(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise MeasurementChannelCatalogError(
            f"{name} must be a non-empty one-dimensional vector"
        )
    if not np.all(np.isfinite(array)):
        raise MeasurementChannelCatalogError(f"{name} must be finite")
    return array


def _matrix(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or min(array.shape) <= 0:
        raise MeasurementChannelCatalogError(
            f"{name} must be a non-empty two-dimensional matrix"
        )
    if not np.all(np.isfinite(array)):
        raise MeasurementChannelCatalogError(f"{name} must be finite")
    return array


def _validate_provenance(provenance: EvidenceProvenance) -> None:
    try:
        provenance.validate()
    except CrossModalEvidenceError as exc:
        raise MeasurementChannelCatalogError(
            f"channel provenance invalid: {exc}"
        ) from exc


@dataclass(frozen=True)
class ChannelDefinition:
    channel_id: str
    family: str
    role: str
    response_model: str
    independence_default: bool
    upstream_repository: str
    upstream_path: str
    upstream_status: str
    physical_binding: str


CATALOG: tuple[ChannelDefinition, ...] = (
    ChannelDefinition(
        "ORBITAL_OMEGA_SQ",
        "ORBITAL",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_FIRST_DERIVATIVE",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "EXACT_CENTRAL_IDENTITY",
        "STATIONARY_CENTRAL_SCALAR_MODEL",
    ),
    ChannelDefinition(
        "EPICYCLIC_KAPPA_SQ",
        "ORBITAL",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_FIRST_SECOND_DERIVATIVE",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "EXACT_CENTRAL_IDENTITY",
        "STATIONARY_CENTRAL_SCALAR_MODEL",
    ),
    ChannelDefinition(
        "KOBS_GRADIENT",
        "ORBITAL",
        SOURCE_SENSITIVE_CONDITIONAL,
        "DERIVED_FROM_OMEGA_KAPPA",
        False,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "EXACT_DERIVED_IDENTITY",
        "STATIONARY_CENTRAL_SCALAR_MODEL",
    ),
    ChannelDefinition(
        "CENTRAL_CONSISTENCY_RESIDUAL",
        "ORBITAL",
        MODEL_CONSISTENCY,
        "CENTRAL_MODEL_FALSIFICATION",
        False,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "EXACT_FALSIFICATION_RESIDUAL",
        "NO_SOURCE_ATTRIBUTION",
    ),
    ChannelDefinition(
        "CONDENSATE_SUBTRACTED_RADIAL_RESIDUAL",
        "ORBITAL",
        SOURCE_SENSITIVE_CONDITIONAL,
        "KNOWN_SECTOR_SUBTRACTION",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "CONDITIONAL_CROSS_MODAL_RESIDUAL",
        "REQUIRES_INDEPENDENT_KNOWN_SECTOR_CONSTRAINTS",
    ),
    ChannelDefinition(
        "DENSITY_GRADIENT",
        "CONDENSATE",
        NUISANCE_CONTROL,
        "DIRECT_CONTROL_RESPONSE_REQUIRED",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "CONTROL_CHANNEL",
        "SOURCE_TO_DENSITY_MAP_REQUIRED",
    ),
    ChannelDefinition(
        "QUANTUM_PRESSURE_GRADIENT",
        "CONDENSATE",
        NUISANCE_CONTROL,
        "DIRECT_CONTROL_RESPONSE_REQUIRED",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "CONTROL_CHANNEL",
        "SOURCE_TO_DENSITY_MAP_REQUIRED",
    ),
    ChannelDefinition(
        "BOGOLIUBOV_SOUND_SPEED_SQ",
        "CONDENSATE",
        NUISANCE_CONTROL,
        "THOMAS_FERMI_CHAIN_RULE",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JP_eb_bec_orbital_bogoliubov_acoustic_bridge.md",
        "CONDITIONAL_BEC_BRIDGE",
        "PHYSICAL_BEC_AND_CALIBRATION_REQUIRED",
    ),
    ChannelDefinition(
        "BOGOLIUBOV_DISPERSION_OMEGA_SQ",
        "CONDENSATE",
        NUISANCE_CONTROL,
        "BOGOLIUBOV_SOUND_CHAIN_RULE",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JP_eb_bec_orbital_bogoliubov_acoustic_bridge.md",
        "CONDITIONAL_BEC_BRIDGE",
        "PHYSICAL_BEC_AND_CALIBRATION_REQUIRED",
    ),
    ChannelDefinition(
        "HOLONOMY_LOOP_PHASE",
        "HOLONOMY",
        SOURCE_SENSITIVE_CONDITIONAL,
        "DIRECT_SOURCE_TO_LOOP_PHASE_JACOBIAN",
        True,
        "AdrianLipa90/Resonant-Chemistry",
        "THEORY/15_RELATIONAL_HOLONOMY_SPECTROSCOPY_BRIDGE_V0_1.md",
        "EXACT_GRAPH_HOLONOMY_MATHEMATICS",
        "PHYSICAL_HOLONOMY_SOURCE_OPEN",
    ),
    ChannelDefinition(
        "HOLONOMY_SHELL_RADIUS",
        "HOLONOMY",
        SOURCE_SENSITIVE_CONDITIONAL,
        "SHELL_TAU_CHAIN_RULE",
        True,
        "AdrianLipa90/Informational-Dynamics-of-Time",
        "formalism/02JQ_radial_condensate_profile_classification.md",
        "CONDITIONAL_SHELL_RESPONSE",
        "SAME_LOOP_HOLONOMY_BINDING_REQUIRED",
    ),
    ChannelDefinition(
        "TRANSVERSE_PHASE_GRADIENT",
        "PHASE_OPTICS",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_TO_TRANSVERSE_GRADIENT",
        False,
        "AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics",
        "docs/ORBIT_EPICYCLE_PHASE_CURVATURE_BRIDGE_V0_1.md",
        "EXACT_SHARED_SCALAR_IDENTITY",
        "INDEPENDENT_READOUT_REQUIRED_FOR_NEW_INFORMATION",
    ),
    ChannelDefinition(
        "TRANSVERSE_PHASE_CURVATURE",
        "PHASE_OPTICS",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_TO_TRANSVERSE_CURVATURE",
        False,
        "AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics",
        "docs/ORBIT_EPICYCLE_PHASE_CURVATURE_BRIDGE_V0_1.md",
        "EXACT_SHARED_SCALAR_IDENTITY",
        "INDEPENDENT_READOUT_REQUIRED_FOR_NEW_INFORMATION",
    ),
    ChannelDefinition(
        "RADIAL_HESSIAN_EIGENVALUE",
        "PHASE_OPTICS",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_HESSIAN",
        False,
        "AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics",
        "docs/ORBIT_EPICYCLE_PHASE_CURVATURE_BRIDGE_V0_1.md",
        "EXACT_SHARED_SCALAR_IDENTITY",
        "INDEPENDENT_READOUT_REQUIRED_FOR_NEW_INFORMATION",
    ),
    ChannelDefinition(
        "TANGENTIAL_HESSIAN_EIGENVALUE",
        "PHASE_OPTICS",
        SOURCE_SENSITIVE_CONDITIONAL,
        "RADIAL_SCALAR_HESSIAN",
        False,
        "AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics",
        "docs/ORBIT_EPICYCLE_PHASE_CURVATURE_BRIDGE_V0_1.md",
        "EXACT_SHARED_SCALAR_IDENTITY",
        "INDEPENDENT_READOUT_REQUIRED_FOR_NEW_INFORMATION",
    ),
    ChannelDefinition(
        "SPECTRAL_LINE_FREQUENCY",
        "SPECTROSCOPY",
        SOURCE_SENSITIVE_CONDITIONAL,
        "LOOP_PHASE_CHAIN_RULE",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "EXACT_AFTER_DECLARED_PHASE_DEPENDENT_HAMILTONIAN",
        "SOURCE_TO_LOOP_PHASE_MAP_REQUIRED",
    ),
    ChannelDefinition(
        "SPECTRAL_INTENSITY",
        "SPECTROSCOPY",
        SOURCE_SENSITIVE_CONDITIONAL,
        "LOOP_PHASE_CHAIN_RULE",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "EXACT_AFTER_DECLARED_PHASE_RESPONSE",
        "SOURCE_TO_LOOP_PHASE_MAP_REQUIRED",
    ),
    ChannelDefinition(
        "SPECTRAL_LINEWIDTH",
        "SPECTROSCOPY",
        CUSTOM_RESPONSE_REQUIRED,
        "MODEL_SPECIFIC_LOOP_OR_SOURCE_JACOBIAN",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "OBSERVABLE_ADMITTED_RESPONSE_MODEL_OPEN",
        "CUSTOM_JACOBIAN_REQUIRED",
    ),
    ChannelDefinition(
        "SPECTRAL_COHERENT_BEAT",
        "SPECTROSCOPY",
        CUSTOM_RESPONSE_REQUIRED,
        "MODEL_SPECIFIC_LOOP_OR_SOURCE_JACOBIAN",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "OBSERVABLE_ADMITTED_RESPONSE_MODEL_OPEN",
        "CUSTOM_JACOBIAN_REQUIRED",
    ),
    ChannelDefinition(
        "SPECTRAL_2D_CROSS_PEAK",
        "SPECTROSCOPY",
        CUSTOM_RESPONSE_REQUIRED,
        "MODEL_SPECIFIC_LOOP_OR_SOURCE_JACOBIAN",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "OBSERVABLE_ADMITTED_RESPONSE_MODEL_OPEN",
        "CUSTOM_JACOBIAN_REQUIRED",
    ),
    ChannelDefinition(
        "SPECTRAL_PHASE_RESOLVED",
        "SPECTROSCOPY",
        CUSTOM_RESPONSE_REQUIRED,
        "MODEL_SPECIFIC_LOOP_OR_SOURCE_JACOBIAN",
        True,
        "AdrianLipa90/Orbital-Eclipse-Spectroscopy",
        "formalism/OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1.md",
        "OBSERVABLE_ADMITTED_RESPONSE_MODEL_OPEN",
        "CUSTOM_JACOBIAN_REQUIRED",
    ),
)


def catalog_entries() -> tuple[ChannelDefinition, ...]:
    return CATALOG


def channel_definition(channel_id: str) -> ChannelDefinition:
    matches = [item for item in CATALOG if item.channel_id == channel_id]
    if len(matches) != 1:
        raise MeasurementChannelCatalogError(
            f"unknown or duplicate channel_id: {channel_id}"
        )
    return matches[0]


def radial_scalar_signature_rows(
    radius: float,
    impact_parameter: float,
    dphi_dr_by_source: Sequence[float],
    d2phi_dr2_by_source: Sequence[float],
) -> dict[str, tuple[float, ...]]:
    r = _positive("radius", radius)
    b = _finite("impact_parameter", impact_parameter)
    if abs(b) > r:
        raise MeasurementChannelCatalogError(
            "|impact_parameter| must be <= radius"
        )
    first = _vector(
        dphi_dr_by_source,
        name="dphi_dr_by_source",
    )
    second = _vector(
        d2phi_dr2_by_source,
        name="d2phi_dr2_by_source",
    )
    if first.shape != second.shape:
        raise MeasurementChannelCatalogError(
            "first- and second-derivative source rows must have equal shape"
        )

    omega = first / r
    kappa = second + 3.0 * first / r
    beta2 = (b / r) ** 2

    rows = {
        "ORBITAL_OMEGA_SQ": omega,
        "EPICYCLIC_KAPPA_SQ": kappa,
        "KOBS_GRADIENT": r * r * (kappa - omega),
        "TRANSVERSE_PHASE_GRADIENT": b * omega,
        "TRANSVERSE_PHASE_CURVATURE":
            beta2 * kappa + (1.0 - 4.0 * beta2) * omega,
        "RADIAL_HESSIAN_EIGENVALUE": kappa - 3.0 * omega,
        "TANGENTIAL_HESSIAN_EIGENVALUE": omega,
    }
    return {
        key: tuple(float(x) for x in value)
        for key, value in rows.items()
    }


def spectral_chain_rule_signature(
    observable_phase_gradient: Sequence[float],
    source_to_loop_phase_jacobian,
) -> tuple[float, ...]:
    gradient = _vector(
        observable_phase_gradient,
        name="observable_phase_gradient",
    )
    jacobian = _matrix(
        source_to_loop_phase_jacobian,
        name="source_to_loop_phase_jacobian",
    )
    if jacobian.shape[0] != gradient.size:
        raise MeasurementChannelCatalogError(
            "phase Jacobian row count must match observable phase-gradient length"
        )
    return tuple(float(x) for x in gradient @ jacobian)


def spectral_line_frequency_signature(
    loop_response_m: Sequence[float],
    loop_response_n: Sequence[float],
    hbar: float,
    source_to_loop_phase_jacobian,
) -> tuple[float, ...]:
    h = _positive("hbar", hbar)
    jm = _vector(loop_response_m, name="loop_response_m")
    jn = _vector(loop_response_n, name="loop_response_n")
    if jm.shape != jn.shape:
        raise MeasurementChannelCatalogError(
            "loop response vectors must have equal shape"
        )
    phase_gradient = -(jm - jn) / h
    return spectral_chain_rule_signature(
        phase_gradient,
        source_to_loop_phase_jacobian,
    )


def holonomy_shell_signature(
    dr_dtau: float,
    source_to_tau: Sequence[float],
) -> tuple[float, ...]:
    susceptibility = _finite("dr_dtau", dr_dtau)
    tau_row = _vector(source_to_tau, name="source_to_tau")
    return tuple(float(x) for x in susceptibility * tau_row)


def thomas_fermi_sound_speed_signature(
    mass: float,
    source_to_mu_c: Sequence[float],
    source_to_u_ext: Sequence[float],
    source_to_u_i: Sequence[float],
) -> tuple[float, ...]:
    m = _positive("mass", mass)
    q_mu = _vector(source_to_mu_c, name="source_to_mu_c")
    q_ext = _vector(source_to_u_ext, name="source_to_u_ext")
    q_i = _vector(source_to_u_i, name="source_to_u_i")
    if not (q_mu.shape == q_ext.shape == q_i.shape):
        raise MeasurementChannelCatalogError(
            "Thomas-Fermi source rows must have equal shape"
        )
    return tuple(float(x) for x in (q_mu - q_ext - q_i) / m)


def bogoliubov_dispersion_signature(
    wave_number: float,
    sound_speed_sq_signature: Sequence[float],
) -> tuple[float, ...]:
    k = _finite("wave_number", wave_number)
    q_cs = _vector(
        sound_speed_sq_signature,
        name="sound_speed_sq_signature",
    )
    return tuple(float(x) for x in (k * k) * q_cs)


@dataclass(frozen=True)
class CatalogMeasurementInstance:
    channel_id: str
    source_names: tuple[str, ...]
    source_signature: tuple[float, ...]
    variance: float
    provenance: EvidenceProvenance
    response_model_id: str
    independence_declared: bool
    independence_evidence: str
    epistemic: str = "CHYBA"

    def validate(self) -> ChannelDefinition:
        definition = channel_definition(self.channel_id)
        if not self.source_names:
            raise MeasurementChannelCatalogError(
                "source_names must be non-empty"
            )
        if len(set(self.source_names)) != len(self.source_names):
            raise MeasurementChannelCatalogError(
                "source_names must be unique"
            )
        signature = _vector(
            self.source_signature,
            name="source_signature",
        )
        if signature.size != len(self.source_names):
            raise MeasurementChannelCatalogError(
                "source_signature length must match source_names"
            )
        _positive("variance", self.variance)
        _validate_provenance(self.provenance)
        if not str(self.response_model_id).strip():
            raise MeasurementChannelCatalogError(
                "response_model_id must be non-empty"
            )
        if not isinstance(self.independence_declared, bool):
            raise MeasurementChannelCatalogError(
                "independence_declared must be boolean"
            )
        if self.independence_declared and not str(
            self.independence_evidence
        ).strip():
            raise MeasurementChannelCatalogError(
                "independence_evidence is required when independence is declared"
            )
        if definition.role == MODEL_CONSISTENCY and self.independence_declared:
            raise MeasurementChannelCatalogError(
                "MODEL_CONSISTENCY channels cannot be promoted to "
                "source-family Fisher rows"
            )
        if (
            not definition.independence_default
            and self.independence_declared
            and "INDEPENDENT_READOUT" not in self.independence_evidence
        ):
            raise MeasurementChannelCatalogError(
                "derived channel independence requires explicit "
                "INDEPENDENT_READOUT evidence"
            )
        if not str(self.epistemic).strip():
            raise MeasurementChannelCatalogError(
                "epistemic must be non-empty"
            )
        return definition

    def to_independent_measurement(self) -> IndependentMeasurement:
        self.validate()
        if not self.independence_declared:
            raise MeasurementChannelCatalogError(
                "channel is not declared independent; use a joint covariance "
                "block instead"
            )
        return IndependentMeasurement(
            signature=MeasurementSignature(
                name=self.channel_id,
                source_signature=self.source_signature,
                provenance=self.provenance,
            ),
            variance=float(self.variance),
        )

    def as_mapping(self) -> dict:
        definition = self.validate()
        return {
            "schema": SCHEMA,
            "catalog_definition": asdict(definition),
            "channel_id": self.channel_id,
            "source_names": list(self.source_names),
            "source_signature": [float(x) for x in self.source_signature],
            "variance": float(self.variance),
            "provenance": asdict(self.provenance),
            "response_model_id": self.response_model_id,
            "independence_declared": self.independence_declared,
            "independence_evidence": self.independence_evidence,
            "epistemic": self.epistemic,
            "physical_source_selected": False,
        }
