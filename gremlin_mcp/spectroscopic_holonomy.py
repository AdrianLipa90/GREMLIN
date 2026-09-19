from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "GREMLIN_PHASENAV_SPECTROSCOPIC_HOLONOMY_V0_1"
VERSION = "0.1.0"
PHASENAV_PACKET_SCHEMA = "PHASENAV_SPECTROSCOPIC_HOLONOMY_STATE_V0_1"
EPISTEMIC_MODE = "CHYBA"
MODULUS_TOLERANCE = 1.0e-9

_STAGE_PLAN = (
    {
        "stage_id": "graph-cycle-audit",
        "species": ("SPIDER", "ANT"),
        "purpose": "verify graph counts, independent-cycle count and declared cycle basis cardinality",
    },
    {
        "stage_id": "phase-response-analysis",
        "species": ("BAT", "MOLE"),
        "purpose": "analyze phase/harmonic sensitivity and local response-model structure",
    },
    {
        "stage_id": "falsification-audit",
        "species": ("HOUND", "OWL"),
        "purpose": "test tree controls, confounds, epistemic boundaries and unsupported physical bindings",
    },
    {
        "stage_id": "identifiability-pruning",
        "species": ("ANT", "MANTIS"),
        "purpose": "scan bounded phase combinations and prune unidentifiable/dead dimensions",
    },
    {
        "stage_id": "candidate-synthesis",
        "species": ("BELZEBUB",),
        "purpose": "synthesize a candidate interpretation only after upstream checks",
    },
)


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _commit(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _strict_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _strict_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    return value


def _finite_float(value: Any, field: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def _string_list(values: Sequence[Any], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{field} must be a sequence of strings")
    out: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        text = item.strip()
        if text not in out:
            out.append(text)
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return tuple(out)


def validate_phasenav_spectroscopic_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a PhaseNav spectroscopic-holonomy packet fail-closed."""
    root = _strict_mapping(packet, "packet")
    if root.get("schema") != PHASENAV_PACKET_SCHEMA:
        raise ValueError("unsupported PhaseNav spectroscopic holonomy schema")
    if root.get("epistemic") != EPISTEMIC_MODE:
        raise ValueError("spectroscopic holonomy packet must remain epistemic=CHYBA")
    if root.get("canon_allowed") is not False:
        raise ValueError("spectroscopic holonomy packet must remain canon_allowed=false")

    graph = _strict_mapping(root.get("graph"), "graph")
    vertices = _strict_int(graph.get("vertex_count"), "graph.vertex_count", minimum=1)
    edges = _strict_int(graph.get("edge_count"), "graph.edge_count", minimum=0)
    components = _strict_int(
        graph.get("component_count"), "graph.component_count", minimum=1
    )
    if components > vertices:
        raise ValueError("graph.component_count cannot exceed graph.vertex_count")
    beta = edges - vertices + components
    if beta < 0:
        raise ValueError("graph counts imply a negative first Betti number")
    declared_beta = _strict_int(graph.get("beta_1"), "graph.beta_1", minimum=0)
    if declared_beta != beta:
        raise ValueError("graph.beta_1 does not equal E - V + C")

    phases_raw = root.get("cycle_phases")
    paths_raw = root.get("cycle_edge_potentials")
    holonomies_raw = root.get("cycle_holonomies")
    if not isinstance(phases_raw, Sequence) or isinstance(phases_raw, (str, bytes)):
        raise ValueError("cycle_phases must be a sequence")
    if not isinstance(paths_raw, Sequence) or isinstance(paths_raw, (str, bytes)):
        raise ValueError("cycle_edge_potentials must be a sequence")
    if not isinstance(holonomies_raw, Sequence) or isinstance(holonomies_raw, (str, bytes)):
        raise ValueError("cycle_holonomies must be a sequence")
    if len(phases_raw) != beta or len(paths_raw) != beta or len(holonomies_raw) != beta:
        raise ValueError("cycle coordinate cardinality must equal beta_1")

    phases = tuple(
        _finite_float(value, f"cycle_phases[{index}]")
        for index, value in enumerate(phases_raw)
    )

    normalized_paths: list[tuple[float, ...]] = []
    for index, path in enumerate(paths_raw):
        if not isinstance(path, Sequence) or isinstance(path, (str, bytes)):
            raise ValueError(f"cycle_edge_potentials[{index}] must be a sequence")
        normalized_paths.append(
            tuple(
                _finite_float(value, f"cycle_edge_potentials[{index}]")
                for value in path
            )
        )

    normalized_holonomies: list[dict[str, float]] = []
    for index, item in enumerate(holonomies_raw):
        row = _strict_mapping(item, f"cycle_holonomies[{index}]")
        real = _finite_float(row.get("real"), f"cycle_holonomies[{index}].real")
        imag = _finite_float(row.get("imag"), f"cycle_holonomies[{index}].imag")
        modulus = _finite_float(
            row.get("modulus"), f"cycle_holonomies[{index}].modulus"
        )
        actual = math.hypot(real, imag)
        if abs(actual - modulus) > MODULUS_TOLERANCE:
            raise ValueError("declared holonomy modulus does not match real/imag")
        if abs(actual - 1.0) > MODULUS_TOLERANCE:
            raise ValueError("spectroscopic holonomy must have unit modulus")
        normalized_holonomies.append(
            {"real": real, "imag": imag, "modulus": modulus}
        )

    claims = _strict_mapping(root.get("claims"), "claims")
    if claims.get("computational_graph_holonomy") is not True:
        raise ValueError("computational_graph_holonomy claim must be true")
    forbidden_claims = (
        "physical_gauge_field",
        "physical_substrate",
        "physical_nonlocal_signalling",
        "hypercharge_identification",
        "weak_boson_identification",
    )
    for key in forbidden_claims:
        if claims.get(key) is not False:
            raise ValueError(f"unsupported physical claim must remain false: {key}")

    normalized = {
        "schema": PHASENAV_PACKET_SCHEMA,
        "version": str(root.get("version") or ""),
        "epistemic": EPISTEMIC_MODE,
        "canon_allowed": False,
        "graph": {
            "vertex_count": vertices,
            "edge_count": edges,
            "component_count": components,
            "beta_1": beta,
        },
        "cycle_edge_potentials": [list(path) for path in normalized_paths],
        "cycle_phases": list(phases),
        "cycle_holonomies": normalized_holonomies,
        "claims": {
            "computational_graph_holonomy": True,
            **{key: False for key in forbidden_claims},
        },
    }
    normalized["packet_commitment_sha256"] = _commit(normalized)
    return normalized


def build_spectroscopic_inverse_plan(
    packet: Mapping[str, Any],
    observables: Sequence[str],
) -> dict[str, Any]:
    """Build a deterministic GREMLIN Bestiary plan over a validated PhaseNav packet."""
    normalized = validate_phasenav_spectroscopic_packet(packet)
    obs = _string_list(observables, "observables")
    beta = int(normalized["graph"]["beta_1"])

    stages = [
        {
            "stage_id": row["stage_id"],
            "species": list(row["species"]),
            "purpose": row["purpose"],
        }
        for row in _STAGE_PLAN
    ]

    inverse_problem = {
        "unknowns": [f"Phi_{index + 1}" for index in range(beta)],
        "unknown_count": beta,
        "observables": list(obs),
        "observable_count": len(obs),
        "expected_jacobian_shape": [len(obs), beta],
        "expected_fisher_shape": [beta, beta],
        "full_local_identifiability_rank_target": beta,
        "tree_control": beta == 0,
        "tree_phase_parameter_forbidden": beta == 0,
        "rank_gate": (
            "NO_PHASE_INVERSE_PROBLEM_FOR_TREE"
            if beta == 0
            else "REQUIRE_RANK_J_EQUALS_BETA_1_FOR_FULL_LOCAL_IDENTIFIABILITY"
        ),
    }

    physical_binding_gates = [
        "molecular/electronic Hamiltonian binding",
        "dipole operator and optical selection rules",
        "vibronic and environmental response model",
        "experimental observable calibration",
        "physical substrate identification",
    ]

    core = {
        "packet_commitment_sha256": normalized["packet_commitment_sha256"],
        "inverse_problem": inverse_problem,
        "stages": stages,
        "physical_binding_gates": physical_binding_gates,
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "CANDIDATE_PLAN",
        "epistemic": EPISTEMIC_MODE,
        "canon_allowed": False,
        "phasenav_packet": normalized,
        "inverse_problem": inverse_problem,
        "stages": stages,
        "species_union": [
            species
            for row in stages
            for species in row["species"]
            if species not in {
                prior
                for earlier in stages[: stages.index(row)]
                for prior in earlier["species"]
            }
        ],
        "physical_binding_gates": physical_binding_gates,
        "plan_commitment_sha256": _commit(core),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
            "raphael_decree_required_for_mutation": True,
        },
        "claims": {
            "phase_graph_mathematics_consumed": True,
            "physical_gauge_field_established": False,
            "physical_nonlocal_signalling_established": False,
            "hypercharge_identification_established": False,
            "weak_boson_identification_established": False,
            "proof_of_consciousness": False,
            "physical_substrate_identification_established": False,
        },
    }


__all__ = [
    "EPISTEMIC_MODE",
    "PHASENAV_PACKET_SCHEMA",
    "SCHEMA",
    "VERSION",
    "build_spectroscopic_inverse_plan",
    "validate_phasenav_spectroscopic_packet",
]
