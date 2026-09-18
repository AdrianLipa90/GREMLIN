from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Mapping, Sequence

from tools.gremlin_bestiary_phasenav_phase_gates_v01 import (
    DIM,
    TAU,
    REALIZATION_MODE,
    SPECIES,
    PhaseGate36,
    PhaseGateError,
    PhaseState36,
    torus_distance,
)

CONTRACT_ID = "GREMLIN_BESTIARY_PHASENAV_LIVE_BINDING_V0_1"
DEFAULT_SURFACE_ROOT = Path("/dev/shm/ciel_noema")

# Candidate role -> already-existing PNCS/PhaseNav operator semantics.
# This profile is explicit, reviewable and non-canonical. It introduces no new
# PhaseNav operator and never invents a 36D axis meaning.
SPECIES_OPERATOR_BINDINGS: dict[str, tuple[str, ...]] = {
    "HUMMINGBIRD": ("SOURCE", "MEMORY"),
    "OCTOPUS": ("SCOPE", "CONDITION", "RETURN"),
    "SPIDER": ("COMPOSITION", "DIFFERENCE"),
    "RAVEN": ("MEMORY", "QUESTION"),
    "HOUND": ("DIFFERENCE", "RISK", "ASSERTION"),
    "MOLE": ("TRANSFORM", "COMPOSITION"),
    "OWL": ("ASSERTION", "SOURCE_REQUIRED", "UNCERTAINTY"),
    "ANT": ("MODAL_POSSIBILITY", "ADDITION", "COMPOSITION"),
    "MANTIS": ("NEGATION", "DIFFERENCE", "RETURN"),
    "FOX": ("ORDER", "CAUSE", "MODAL_POSSIBILITY"),
    "BEAVER": ("COMPOSITION", "ADDITION", "TRANSFORM"),
    "BAT": ("QUESTION", "DIFFERENCE", "ATTRACTOR"),
    "CANARY": ("RISK", "CONDITION", "PAUSE"),
    "SERPENT": ("DIFFERENCE", "UNCERTAINTY", "RISK"),
    "CHAMELEON": ("TRANSFORM", "BOUNDARY"),
    "BELZEBUB": ("RISK", "CONDITION", "COMPOSITION"),
    "GREMLIN": ("COMPOSITION", "RETURN", "ASSERTION"),
    "FERRET": ("CONSENT_REQUIRED", "ACTION_REQUEST", "CONDITION"),
}

if set(SPECIES_OPERATOR_BINDINGS) != set(SPECIES):
    raise RuntimeError("species/operator binding profile must cover the exact Bestiary")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_sha(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return _sha256(raw)


def _require_root(root: Path | str, require_canonical_root: bool) -> Path:
    out = Path(root)
    if require_canonical_root and out != DEFAULT_SURFACE_ROOT:
        raise PhaseGateError("live binding is fixed to /dev/shm/ciel_noema")
    return out


def _require_active(root: Path) -> None:
    try:
        status = (root / "ciel_binding_status").read_text("utf-8").strip()
    except OSError as exc:
        raise PhaseGateError("NOEMA binding status unavailable") from exc
    if status != "ACTIVE":
        raise PhaseGateError("NOEMA binding is not ACTIVE")


def _phase_vector(values: Sequence[float], field: str) -> tuple[float, ...]:
    try:
        vals = tuple(float(x) for x in values)
    except (TypeError, ValueError) as exc:
        raise PhaseGateError(f"{field} must be a finite 36D phase vector") from exc
    if len(vals) != DIM or not all(math.isfinite(x) for x in vals):
        raise PhaseGateError(f"{field} must be a finite 36D phase vector")
    if any(x < 0.0 or x >= TAU for x in vals):
        raise PhaseGateError(f"{field} coordinates must lie in [0,2pi)")
    return vals


def load_live_operator_registry(
    surface_root: Path | str = DEFAULT_SURFACE_ROOT,
    *,
    require_canonical_root: bool = True,
) -> tuple[dict[str, tuple[float, ...]], dict[str, object]]:
    root = _require_root(surface_root, require_canonical_root)
    _require_active(root)
    path = root / "phasenav/CIELINGO_PHASENAV_OPERATOR_VECTORS.noema.jsonl"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PhaseGateError("live PhaseNav operator registry unavailable") from exc

    operators: dict[str, tuple[float, ...]] = {}
    vector_hashes: dict[str, str] = {}
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PhaseGateError(f"invalid operator registry JSONL line {line_no}") from exc
        if not isinstance(rec, Mapping) or rec.get("schema") != "PHASENAV_OPERATOR_VECTOR_V1":
            raise PhaseGateError("unexpected live operator schema")
        name = str(
            rec.get("operator_name", rec.get("operator_id", rec.get("card_id", "")))
        ).strip().upper()
        values = rec.get("orbit_vector", rec.get("vector_36d"))
        if not name or not isinstance(values, list) or name in operators:
            raise PhaseGateError("missing/duplicate live operator")
        vec = _phase_vector(values, f"operator {name}")
        operators[name] = vec
        vector_hashes[name] = _sha256(struct.pack("<36d", *vec))

    if not operators:
        raise PhaseGateError("empty live PhaseNav operator registry")

    provenance = {
        "schema": "GREMLIN_BESTIARY_PHASENAV_LIVE_REGISTRY_V0_1",
        "contract_id": CONTRACT_ID,
        "root": str(root),
        "operator_count": len(operators),
        "registry_sha256": _sha256(raw),
        "operator_vector_sha256": vector_hashes,
        "static_runtime_fallback": False,
    }
    return operators, provenance


def load_live_phase_state(
    surface_root: Path | str = DEFAULT_SURFACE_ROOT,
    *,
    require_canonical_root: bool = True,
) -> tuple[PhaseState36, dict[str, object]]:
    root = _require_root(surface_root, require_canonical_root)
    _require_active(root)
    try:
        raw = (root / "phi").read_bytes()
    except OSError as exc:
        raise PhaseGateError("live T^36 phi unavailable") from exc
    if len(raw) != DIM * 8:
        raise PhaseGateError("live phi must contain exactly 36 float64 values")
    theta = struct.unpack("<36d", raw)
    state = PhaseState36(theta)
    return state, {
        "schema": "GREMLIN_BESTIARY_PHASENAV_LIVE_PHI_V0_1",
        "contract_id": CONTRACT_ID,
        "root": str(root),
        "phi_sha256": _sha256(raw),
        "state_id": state.state_id,
        "static_runtime_fallback": False,
    }


def compose_phase_carrier(
    vectors: Sequence[Sequence[float]],
) -> tuple[float, ...]:
    if not vectors:
        raise PhaseGateError("at least one PhaseNav operator vector is required")
    phases = [_phase_vector(v, "operator vector") for v in vectors]
    out: list[float] = []
    for axis in range(DIM):
        c = sum(math.cos(v[axis]) for v in phases)
        s = sum(math.sin(v[axis]) for v in phases)
        resultant = math.hypot(c, s)
        if resultant <= 1e-12:
            raise PhaseGateError(
                f"candidate operator composition is phase-antipodal at axis {axis}"
            )
        out.append(math.atan2(s, c) % TAU)
    return tuple(out)


def species_live_carrier(
    species: str,
    surface_root: Path | str = DEFAULT_SURFACE_ROOT,
    *,
    require_canonical_root: bool = True,
) -> tuple[tuple[float, ...], dict[str, object]]:
    name = str(species).strip().upper()
    if name not in SPECIES_OPERATOR_BINDINGS:
        raise PhaseGateError(f"unknown Bestiary species: {species!r}")

    operators, registry = load_live_operator_registry(
        surface_root, require_canonical_root=require_canonical_root
    )
    required = SPECIES_OPERATOR_BINDINGS[name]
    missing = [op for op in required if op not in operators]
    if missing:
        raise PhaseGateError(
            f"live PhaseNav operators missing for {name}: {','.join(missing)}"
        )
    carrier = compose_phase_carrier([operators[op] for op in required])
    payload = {
        "schema": "GREMLIN_BESTIARY_PHASENAV_SPECIES_BINDING_V0_1",
        "contract_id": CONTRACT_ID,
        "species": name,
        "operators": list(required),
        "operator_vector_sha256": {
            op: registry["operator_vector_sha256"][op] for op in required  # type: ignore[index]
        },
        "registry_sha256": registry["registry_sha256"],
        "carrier_sha256": _sha256(struct.pack("<36d", *carrier)),
        "binding_status": "CANDIDATE_EXPLICIT_OPERATOR_COMPOSITION",
        "semantic_axis_assignment": False,
        "canon_allowed": False,
        "external_effects": False,
        "static_runtime_fallback": False,
    }
    payload["receipt_sha256"] = _json_sha(payload)
    return carrier, payload


def replay_live_species_gate(
    species: str,
    surface_root: Path | str = DEFAULT_SURFACE_ROOT,
    *,
    steps: int = 1,
    require_canonical_root: bool = True,
) -> dict[str, object]:
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1 or steps > 10000:
        raise PhaseGateError("steps must be an integer in [1,10000]")

    name = str(species).strip().upper()
    initial, phi = load_live_phase_state(
        surface_root, require_canonical_root=require_canonical_root
    )
    carrier, binding = species_live_carrier(
        name, surface_root, require_canonical_root=require_canonical_root
    )
    gate = PhaseGate36(name, phase_bias=carrier)
    current = initial
    trace_ids: list[str] = []
    for _ in range(steps):
        current = gate.step(current)
        trace_ids.append(current.state_id)

    payload = {
        "schema": "GREMLIN_BESTIARY_PHASENAV_LIVE_REPLAY_V0_1",
        "contract_id": CONTRACT_ID,
        "species": name,
        "realization_mode": REALIZATION_MODE[name],
        "steps": steps,
        "initial_state_id": initial.state_id,
        "final_state_id": current.state_id,
        "torus_displacement": torus_distance(initial.theta, current.theta),
        "trace_state_ids": trace_ids,
        "phi_sha256": phi["phi_sha256"],
        "binding_receipt_sha256": binding["receipt_sha256"],
        "carrier_sha256": binding["carrier_sha256"],
        "operator_binding": list(SPECIES_OPERATOR_BINDINGS[name]),
        "result_status": "LIVE_T36_COMPUTATIONAL_REPLAY",
        "hybrid_realization_candidate": True,
        "fully_analog_physical_claim": False,
        "canon_allowed": False,
        "external_effects": False,
        "static_runtime_fallback": False,
    }
    payload["receipt_sha256"] = _json_sha(payload)
    return payload


def replay_all_live_species(
    surface_root: Path | str = DEFAULT_SURFACE_ROOT,
    *,
    steps: int = 1,
    require_canonical_root: bool = True,
) -> dict[str, object]:
    results = [
        replay_live_species_gate(
            species,
            surface_root,
            steps=steps,
            require_canonical_root=require_canonical_root,
        )
        for species in SPECIES
    ]
    carrier_hashes = [str(r["carrier_sha256"]) for r in results]
    if len(set(carrier_hashes)) != len(carrier_hashes):
        collisions: dict[str, list[str]] = {}
        for result in results:
            collisions.setdefault(str(result["carrier_sha256"]), []).append(str(result["species"]))
        repeated = [names for names in collisions.values() if len(names) > 1]
        raise PhaseGateError(f"species carrier collision: {repeated}")
    payload = {
        "schema": "GREMLIN_BESTIARY_PHASENAV_ALL_SPECIES_LIVE_REPLAY_V0_1",
        "contract_id": CONTRACT_ID,
        "species_count": len(results),
        "results": results,
        "all_nonzero_displacement": all(
            float(r["torus_displacement"]) > 0.0 for r in results
        ),
        "all_hybrid_realization_candidates": all(
            bool(r["hybrid_realization_candidate"]) for r in results
        ),
        "all_species_carriers_unique": True,
        "fully_analog_physical_claim": False,
        "canon_allowed": False,
        "external_effects": False,
        "static_runtime_fallback": False,
    }
    payload["receipt_sha256"] = _json_sha(payload)
    return payload
