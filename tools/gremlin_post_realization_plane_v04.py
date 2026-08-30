from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.gremlin_acquisition_bound_phasenav_v03 import (
    validate_acquisition_bound_phasenav_ir_v03,
)

DIM = 36
TAU = 2.0 * math.pi
PI = 3.14159265358979323846
KAPPA = math.log(2) / (24.0 * PI)
L3 = 7
L4 = 2
L5 = 5
ALPHA_M = 1.0 / ((L3 * L4) ** 2 - L3 ** 2 - L4 * L5 + L4 ** 2 * KAPPA)
L_RATIO = L4 / L3
MASS_SCALE = 10_000_000_000
MASS_QUANTUM = Decimal("0.0000000001")

PNCS_SOURCE_COMMIT = "83a06b9398bab09052c2c2124974897cc31a461f"
PNCS_REALIZATION_SCHEMA = "PNCS_EXACT_36D_REALIZATION_V0_18"
PNCS_BINDING_SCHEMA = "PNCS_EXACT_36D_BINDING_V0_18"
PNCS_MASS_SCHEMA = "PNCS_SEMANTIC_MASS_REALIZATION_V0_19"
PNCS_MASS_BINDING_SCHEMA = "PNCS_SEMANTIC_MASS_BINDING_V0_19"
PNCS_MASS_CONTRACT_ID = "PNV_SEMANTIC_MASS_V1"
PNCS_MASS_RUNTIME_SOURCE_SHA256 = "0b4df86cd01db313ea46ebac0eceee9cf6df0673391edd1a3fb2667c30464a32"
PNCS_MASS_RUNTIME_SOURCE_LOCATOR = "NOEMA_LIBRARY:file_00000000ea0c8210b0ff0db8ea94071a:v1:pnv_runtime.py"
PNCS_COST_SCHEMA = "PNCS_MASS_AWARE_GRAPH_COST_V0_21"
PNCS_COST_RECEIPT_SCHEMA = "PNCS_MASS_AWARE_GRAPH_COST_RECEIPT_V0_21"
PNCS_COST_CONTRACT_ID = "PNCS_MASS_AWARE_GRAPH_COST_V0_21"

POST_SCHEMA = "GREMLIN_POST_REALIZATION_ADMISSION_V0_4"
POST_DOMAIN = b"GREMLIN-POST-REALIZATION-ADMISSION/v0.4\x00"
LIVE_ROOT = Path("/dev/shm/ciel_noema")

_CONTENT_ID_RE = re.compile(
    r"^pncs:(?:def|class|file|cluster|subsystem|daemon|low-orchestrator|high-orchestrator|system):sha256:[0-9a-f]{64}$"
)
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTRACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,191}$")
_OPERATOR_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class GremlinPostRealizationError(ValueError):
    pass


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, Mapping):
        return {str(k): _jsonable(value[k]) for k in sorted(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GremlinPostRealizationError("non-finite canonical float")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise GremlinPostRealizationError(f"unsupported canonical value type: {type(value).__name__}")


def _compact_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_compact_json(value).encode("utf-8")).hexdigest()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _typed_id(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{_sha(value)}"


def _hash64(value: Any, field: str) -> str:
    text = str(value)
    if not _DIGEST_RE.fullmatch(text):
        raise GremlinPostRealizationError(f"{field} must be lowercase SHA-256")
    return text


def _nonempty(value: Any, field: str) -> str:
    text = str(value)
    if not text:
        raise GremlinPostRealizationError(f"{field} must be non-empty")
    return text


def _contract(value: Any, field: str) -> str:
    text = str(value)
    if not _CONTRACT_RE.fullmatch(text):
        raise GremlinPostRealizationError(f"{field} must be a stable contract identifier")
    return text


def _content_id(value: Any) -> str:
    text = str(value)
    if not _CONTENT_ID_RE.fullmatch(text):
        raise GremlinPostRealizationError("content_id must be an existing typed PNCS SHA-256 content ID")
    return text


def _finite36(values: Sequence[Any], field: str) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != DIM:
        raise GremlinPostRealizationError(f"{field} must contain exactly 36 values")
    out = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in out):
        raise GremlinPostRealizationError(f"{field} contains non-finite values")
    return out


def _phase36(values: Sequence[Any]) -> tuple[float, ...]:
    out = _finite36(values, "phase36")
    for i, value in enumerate(out):
        if value < 0.0 or value >= TAU:
            raise GremlinPostRealizationError(f"phase36[{i}] must be in [0,2pi)")
    return out


def _runtime_sin(x: float) -> float:
    x = float(x) % (2.0 * PI)
    s = 0.0
    t = x
    for n in range(1, 30, 2):
        s += t
        t *= -x * x / ((n + 1) * (n + 2))
    return s


def _runtime_cos(x: float) -> float:
    x = float(x) % (2.0 * PI)
    s = 0.0
    t = 1.0
    for n in range(0, 30, 2):
        s += t
        t *= -x * x / ((n + 1) * (n + 2))
    return s


def phase_order_parameter_v19(phase36: Sequence[Any]) -> float:
    phase = _phase36(phase36)
    s = math.fsum(_runtime_sin(value) for value in phase)
    c = math.fsum(_runtime_cos(value) for value in phase)
    return math.hypot(s, c) / DIM


def semantic_mass_v19(phase_index: Any, phase36: Sequence[Any]) -> float:
    if isinstance(phase_index, bool) or not isinstance(phase_index, int) or phase_index < 1:
        raise GremlinPostRealizationError("phase_index must be an explicit positive integer")
    r_k = phase_order_parameter_v19(phase36)
    return round(KAPPA * (1.0 + ALPHA_M * phase_index) + L_RATIO * r_k, 10)


def _mass_units(value: Any) -> int:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise GremlinPostRealizationError("semantic mass must be finite") from exc
    if not math.isfinite(f) or f < 0.0:
        raise GremlinPostRealizationError("semantic mass must be finite and non-negative")
    try:
        d = Decimal(str(f))
    except InvalidOperation as exc:
        raise GremlinPostRealizationError("invalid semantic mass") from exc
    q = d.quantize(MASS_QUANTUM)
    if d != q:
        raise GremlinPostRealizationError("mass must be a PNCS v0.19 10-decimal value")
    return int(q * MASS_SCALE)


def _realization_records(evidence: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], tuple[float, ...], tuple[float, ...]]:
    if not isinstance(evidence, Mapping):
        raise GremlinPostRealizationError("KAKU realization evidence must be a mapping")
    content_id = _content_id(evidence.get("content_id"))
    vector36 = _finite36(evidence.get("vector36"), "vector36")
    phase36 = _phase36(evidence.get("phase36"))
    basis_id = _contract(evidence.get("basis_id"), "basis_id")
    derivation_id = _contract(evidence.get("derivation_id"), "derivation_id")
    source_digest = _hash64(evidence.get("source_digest_sha256"), "source_digest_sha256")
    source_locator = _nonempty(evidence.get("source_locator"), "source_locator")

    realization_payload = {
        "schema": PNCS_REALIZATION_SCHEMA,
        "content_id": content_id,
        "basis_id": basis_id,
        "derivation_id": derivation_id,
        "space": "T^36",
        "coordinate_semantics": "phase_angles_radians",
        "coordinate_range": "[0,2π)",
        "phase36": list(phase36),
        "phase36_sha256": _sha(list(phase36)),
    }
    realization_id = _typed_id("pncs:realization36", realization_payload)
    binding_payload = {
        "schema": PNCS_BINDING_SCHEMA,
        "realization_id": realization_id,
        "content_id": content_id,
        "basis_id": basis_id,
        "derivation_id": derivation_id,
        "phase36_sha256": realization_payload["phase36_sha256"],
        "source_digest_sha256": source_digest,
        "source_locator": source_locator,
        "epistemic_operator": "CHYBA",
        "canon_allowed": False,
    }
    binding_id = _typed_id("pncs:binding36", binding_payload)
    return (
        {**realization_payload, "realization_id": realization_id},
        {**binding_payload, "binding_id": binding_id},
        vector36,
        phase36,
    )


def _mass_binding_record(
    *,
    realization: Mapping[str, Any],
    binding: Mapping[str, Any],
    phase_index: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(phase_index, bool) or not isinstance(phase_index, int) or phase_index < 1:
        raise GremlinPostRealizationError("phase_index must be an explicit positive integer")
    phase36 = realization["phase36"]
    r_k = phase_order_parameter_v19(phase36)
    mass = semantic_mass_v19(phase_index, phase36)
    mass_payload = {
        "schema": PNCS_MASS_SCHEMA,
        "content_id": realization["content_id"],
        "realization_id": realization["realization_id"],
        "phase_index": phase_index,
        "mass_contract_id": PNCS_MASS_CONTRACT_ID,
        "runtime_source_sha256": PNCS_MASS_RUNTIME_SOURCE_SHA256,
        "kappa": KAPPA,
        "alpha_m": ALPHA_M,
        "l3": L3,
        "l4": L4,
        "l5": L5,
        "l_ratio": L_RATIO,
        "order_parameter_R": r_k,
        "semantic_mass": mass,
    }
    mass_realization_id = _typed_id("pncs:mass", mass_payload)
    mass_binding_payload = {
        "schema": PNCS_MASS_BINDING_SCHEMA,
        "mass_realization_id": mass_realization_id,
        "content_id": realization["content_id"],
        "realization_id": realization["realization_id"],
        "realization_binding_id": binding["binding_id"],
        "phase_index": phase_index,
        "mass_contract_id": PNCS_MASS_CONTRACT_ID,
        "runtime_source_sha256": PNCS_MASS_RUNTIME_SOURCE_SHA256,
        "runtime_source_locator": PNCS_MASS_RUNTIME_SOURCE_LOCATOR,
        "semantic_mass": mass,
        "epistemic_operator": "CHYBA",
        "canon_allowed": False,
    }
    mass_binding_id = _typed_id("pncs:mass-binding", mass_binding_payload)
    return (
        {**mass_payload, "mass_realization_id": mass_realization_id},
        {**mass_binding_payload, "mass_binding_id": mass_binding_id},
    )


def operator_stability_bound(ir: Mapping[str, Any]) -> dict[str, Any]:
    base = ir["scalar_admitted_phasenav_ir_v02"]["phasenav_ir"]
    terms = base["terms"]
    rows = []
    total = 0.0
    for term in terms:
        ell = tuple(int(v) for v in term["ell"])
        gain = float.fromhex(str(term["gain_f64_hex"]))
        norm_sq = sum(v * v for v in ell)
        contribution = abs(gain) * norm_sq
        total += contribution
        rows.append(
            {
                "source_ref": str(term.get("source_ref", "")),
                "ell_norm_sq": norm_sq,
                "gain_f64_hex": gain.hex(),
                "lipschitz_contribution_f64_hex": contribution.hex(),
            }
        )
    if not math.isfinite(total):
        raise GremlinPostRealizationError("operator stability bound is non-finite")
    return {
        "contract": "GREMLIN_QHTRI_CHARACTER_LIPSCHITZ_BOUND_V0_2",
        "source_doc": "docs/QHTRI_TORUS_CHARACTER_KERNEL_V0_2.md",
        "terms": rows,
        "L_character_f64_hex": total.hex(),
    }


def validate_runtime_context(context: Mapping[str, Any]) -> bool:
    if not isinstance(context, Mapping):
        raise GremlinPostRealizationError("runtime_context must be a mapping")
    if context.get("surface_root") != str(LIVE_ROOT):
        raise GremlinPostRealizationError("runtime cost surface must be /dev/shm/ciel_noema")
    _hash64(context.get("operator_registry_sha256"), "operator_registry_sha256")
    _hash64(context.get("tether_receipt_sha256"), "tether_receipt_sha256")
    operators = context.get("live_operator_ids")
    if not isinstance(operators, list) or not operators or len(set(map(str, operators))) != len(operators):
        raise GremlinPostRealizationError("live_operator_ids must be unique and non-empty")
    for op in operators:
        if not _OPERATOR_RE.fullmatch(str(op)):
            raise GremlinPostRealizationError(f"invalid operator ID in runtime context: {op}")
    status = context.get("witness_status")
    if status not in {"LIVE_NOEMA_ACTIVE", "TEST_FIXTURE_ONLY"}:
        raise GremlinPostRealizationError("unsupported runtime witness_status")
    if context.get("static_runtime_fallback") is not False:
        raise GremlinPostRealizationError("static runtime fallback is forbidden")
    return True


def capture_live_runtime_context() -> dict[str, Any]:
    root = LIVE_ROOT
    if not root.is_dir():
        raise GremlinPostRealizationError("live NOEMA surface is absent")
    if (root / "ciel_binding_status").read_text(encoding="utf-8").strip() != "ACTIVE":
        raise GremlinPostRealizationError("NOEMA binding is not ACTIVE")
    tether = json.loads((root / "tether_runtime_status.json").read_text(encoding="utf-8"))
    if tether.get("status") != "ACTIVE":
        raise GremlinPostRealizationError("NOEMA tether is not ACTIVE")
    tether_receipt = _hash64(tether.get("receipt_sha256"), "tether receipt")

    registry_path = root / "phasenav/CIELINGO_PHASENAV_OPERATOR_VECTORS.noema.jsonl"
    raw = registry_path.read_bytes()
    operators: list[str] = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("schema") != "PHASENAV_OPERATOR_VECTOR_V1":
            raise GremlinPostRealizationError(f"unexpected live operator schema at line {line_no}")
        op = str(rec.get("operator_name", rec.get("operator_id", rec.get("card_id", "")))).strip().upper()
        orbit = rec.get("orbit_vector", rec.get("vector_36d"))
        if not _OPERATOR_RE.fullmatch(op) or not isinstance(orbit, list) or len(orbit) != DIM:
            raise GremlinPostRealizationError(f"invalid live operator entry at line {line_no}")
        _finite36(orbit, f"live operator {op}")
        if op in operators:
            raise GremlinPostRealizationError(f"duplicate live operator: {op}")
        operators.append(op)
    context = {
        "surface_root": str(root),
        "operator_registry_sha256": _sha_bytes(raw),
        "tether_receipt_sha256": tether_receipt,
        "live_operator_ids": sorted(operators),
        "witness_status": "LIVE_NOEMA_ACTIVE",
        "static_runtime_fallback": False,
    }
    validate_runtime_context(context)
    return context


def _validate_relation_bindings(
    relation_bindings: Sequence[Mapping[str, Any]],
    required_relation_ids: Sequence[str],
    kaku_ids: set[str],
) -> list[list[str]]:
    if not isinstance(relation_bindings, Sequence) or isinstance(relation_bindings, (str, bytes)):
        raise GremlinPostRealizationError("relation_bindings must be a sequence")
    rows = []
    seen = set()
    for item in relation_bindings:
        if not isinstance(item, Mapping):
            raise GremlinPostRealizationError("relation binding must be a mapping")
        rid = _nonempty(item.get("relation_id"), "relation_id")
        if rid in seen:
            raise GremlinPostRealizationError(f"duplicate relation binding: {rid}")
        seen.add(rid)
        source = _nonempty(item.get("source_id"), f"{rid}.source_id")
        target = _nonempty(item.get("target_id"), f"{rid}.target_id")
        relation_type = _nonempty(item.get("relation_type"), f"{rid}.relation_type")
        if source not in kaku_ids or target not in kaku_ids:
            raise GremlinPostRealizationError(f"relation endpoint absent from Radical KAKU set: {rid}")
        rows.append([rid, source, target, relation_type])
    if set(seen) != set(map(str, required_relation_ids)):
        raise GremlinPostRealizationError("relation bindings differ from scalar-admitted Radical lineage")
    return sorted(rows)


def build_post_realization_admission_v04(
    acquisition_bound_ir: Mapping[str, Any],
    *,
    realization_evidence_by_kaku: Mapping[str, Mapping[str, Any]],
    relation_bindings: Sequence[Mapping[str, Any]],
    runtime_context: Mapping[str, Any],
) -> dict[str, Any]:
    validate_acquisition_bound_phasenav_ir_v03(acquisition_bound_ir)
    validate_runtime_context(runtime_context)

    acquired = acquisition_bound_ir["acquired_radical_v02"]
    legacy_radical = acquired["radical_admission_v01"]
    ordered_acquired = acquired["ordered_acquired_kaku"]
    kaku_ids = [str(item["kaku_packet_v01"]["kaku_id"]) for item in ordered_acquired]
    if set(realization_evidence_by_kaku) != set(kaku_ids):
        raise GremlinPostRealizationError("exact realization evidence required for every and only admitted KAKU")

    live_ops = set(map(str, runtime_context["live_operator_ids"]))
    realized = []
    basis_id: str | None = None
    for item in ordered_acquired:
        packet = item["kaku_packet_v01"]
        kid = str(packet["kaku_id"])
        operator_id = str(packet["operator_kind"])
        if operator_id not in live_ops:
            raise GremlinPostRealizationError(f"KAKU operator absent from live runtime context: {operator_id}")
        evidence = realization_evidence_by_kaku[kid]
        realization, binding, vector36, phase36 = _realization_records(evidence)
        if basis_id is None:
            basis_id = str(realization["basis_id"])
        elif realization["basis_id"] != basis_id:
            raise GremlinPostRealizationError("all Radical KAKU realizations must share one basis_id")
        phase_index = evidence.get("phase_index")
        mass_realization, mass_binding = _mass_binding_record(
            realization=realization,
            binding=binding,
            phase_index=phase_index,
        )
        mass_units = _mass_units(mass_binding["semantic_mass"])
        witness_payload = {
            "kaku_id": kid,
            "operator_id": operator_id,
            "mass_binding_id": mass_binding["mass_binding_id"],
            "semantic_mass_units": mass_units,
            "phase36_sha256": realization["phase36_sha256"],
            "realization_id": realization["realization_id"],
        }
        witness_id = _typed_id("pncs:mass-witness", witness_payload)
        realized.append(
            {
                "kaku_id": kid,
                "operator_id": operator_id,
                "direction": packet["direction"],
                "polarity_f64_hex": packet["polarity_f64_hex"],
                "vector36": list(vector36),
                "phase36": list(phase36),
                "pncs_realization_v18": realization,
                "pncs_realization_binding_v18": binding,
                "pncs_mass_realization_v19": mass_realization,
                "pncs_mass_binding_v19": mass_binding,
                "pncs_mass_witness_v21": {**witness_payload, "witness_id": witness_id},
            }
        )

    assert basis_id is not None
    edges = _validate_relation_bindings(
        relation_bindings,
        legacy_radical["relation_ids"],
        set(kaku_ids),
    )

    by_id = {item["kaku_id"]: item for item in realized}
    ordered_ids = sorted(by_id)
    witnesses = [by_id[kid]["pncs_mass_witness_v21"] for kid in ordered_ids]
    graph_payload = {
        "radical_id": legacy_radical["radical_id"],
        "basis_id": basis_id,
        "nodes": ordered_ids,
        "edges": edges,
    }
    cost_payload = {
        "schema": PNCS_COST_SCHEMA,
        "cost_contract_id": PNCS_COST_CONTRACT_ID,
        "scope": "RADICAL",
        "subject_id": legacy_radical["radical_id"],
        "graph_sha256": _sha(graph_payload),
        "ordered_witness_ids": [w["witness_id"] for w in witnesses],
        "ordered_kaku_ids": ordered_ids,
        "operator_ids": [w["operator_id"] for w in witnesses],
        "mass_units": [w["semantic_mass_units"] for w in witnesses],
        "mass_scale": MASS_SCALE,
        "node_count": len(witnesses),
        "unique_kaku_count": len(ordered_ids),
        "duplicate_node_count": 0,
        "duplicate_mass_units": 0,
        "total_mass_units": sum(w["semantic_mass_units"] for w in witnesses),
        "total_mass": float(Decimal(sum(w["semantic_mass_units"] for w in witnesses)) / MASS_SCALE),
        "semantic_identity_affected": False,
        "semantic_equivalence_from_cost": False,
    }
    cost_id = _typed_id("pncs:graph-cost", cost_payload)
    live_runtime = {
        "surface_root": runtime_context["surface_root"],
        "operator_registry_sha256": runtime_context["operator_registry_sha256"],
        "tether_receipt_sha256": runtime_context["tether_receipt_sha256"],
        "live_operator_ids": list(runtime_context["live_operator_ids"]),
        "static_runtime_fallback": False,
    }
    cost_receipt_payload = {
        "schema": PNCS_COST_RECEIPT_SCHEMA,
        "cost_id": cost_id,
        "cost": cost_payload,
        "live_runtime": live_runtime,
    }
    cost_receipt = {**cost_receipt_payload, "receipt_sha256": _sha(cost_receipt_payload)}

    stability = operator_stability_bound(acquisition_bound_ir)
    post_scalars = {
        "phase_coherence_R_k": {
            item["kaku_id"]: item["pncs_mass_realization_v19"]["order_parameter_R"]
            for item in realized
        },
        "semantic_mass": {
            item["kaku_id"]: item["pncs_mass_binding_v19"]["semantic_mass"]
            for item in realized
        },
        "mass_aware_graph_cost": cost_receipt,
        "operator_stability_bound": stability,
    }
    runtime_is_live = runtime_context.get("witness_status") == "LIVE_NOEMA_ACTIVE"
    core = {
        "schema": POST_SCHEMA,
        "candidate_id": acquisition_bound_ir["candidate_id"],
        "radical_id": acquisition_bound_ir["radical_id"],
        "acquisition_bound_ir_commitment": acquisition_bound_ir["acquisition_bound_ir_commitment"],
        "pncs_source_commit": PNCS_SOURCE_COMMIT,
        "basis_id": basis_id,
        "realized_kaku": realized,
        "radical_graph_payload": graph_payload,
        "post_realization_scalars": post_scalars,
        "runtime_context": dict(runtime_context),
        "t36_realization_present": True,
        "semantic_mass_present": True,
        "mass_aware_graph_cost_present": True,
        "operator_stability_bound_present": True,
        "post_realization_complete": True,
        "vector_bound": True,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "POST_REALIZATION_ADMITTED" if runtime_is_live else "POST_REALIZATION_REFERENCE_COMPLETE",
    }
    commitment = hashlib.blake2b(POST_DOMAIN + _compact_json(core).encode("utf-8"), digest_size=32).hexdigest()
    return {**core, "post_realization_commitment": commitment}


def validate_post_realization_admission_v04(record: Mapping[str, Any]) -> bool:
    if record.get("schema") != POST_SCHEMA:
        raise GremlinPostRealizationError("unsupported post-realization schema")
    if record.get("pncs_source_commit") != PNCS_SOURCE_COMMIT:
        raise GremlinPostRealizationError("PNCS contract source commit mismatch")
    for field in (
        "t36_realization_present",
        "semantic_mass_present",
        "mass_aware_graph_cost_present",
        "operator_stability_bound_present",
        "post_realization_complete",
        "vector_bound",
    ):
        if record.get(field) is not True:
            raise GremlinPostRealizationError(f"{field} must be true")
    if record.get("production_runtime_write") is not False:
        raise GremlinPostRealizationError("post-realization admission cannot grant production runtime write")
    if record.get("execution_admitted") is not False or record.get("canon_allowed") is not False:
        raise GremlinPostRealizationError("post-realization authority boundary violated")

    context = record.get("runtime_context")
    validate_runtime_context(context)
    expected_status = (
        "POST_REALIZATION_ADMITTED"
        if context.get("witness_status") == "LIVE_NOEMA_ACTIVE"
        else "POST_REALIZATION_REFERENCE_COMPLETE"
    )
    if record.get("status") != expected_status:
        raise GremlinPostRealizationError("post-realization status/runtime witness mismatch")

    realized = record.get("realized_kaku")
    if not isinstance(realized, list) or not realized:
        raise GremlinPostRealizationError("realized KAKU records required")
    kaku_ids = []
    basis_ids = set()
    live_ops = set(map(str, context["live_operator_ids"]))
    for item in realized:
        if not isinstance(item, Mapping):
            raise GremlinPostRealizationError("realized KAKU entry must be a mapping")
        kid = _nonempty(item.get("kaku_id"), "kaku_id")
        kaku_ids.append(kid)
        operator_id = _nonempty(item.get("operator_id"), f"{kid}.operator_id")
        if operator_id not in live_ops:
            raise GremlinPostRealizationError(f"realized operator absent from runtime context: {operator_id}")
        vector36 = _finite36(item.get("vector36"), f"{kid}.vector36")
        phase36 = _phase36(item.get("phase36"))
        realization = item.get("pncs_realization_v18")
        binding = item.get("pncs_realization_binding_v18")
        mass_realization = item.get("pncs_mass_realization_v19")
        mass_binding = item.get("pncs_mass_binding_v19")
        witness = item.get("pncs_mass_witness_v21")
        if not all(isinstance(v, Mapping) for v in (realization, binding, mass_realization, mass_binding, witness)):
            raise GremlinPostRealizationError("complete PNCS realization/mass witness chain required")
        basis_ids.add(str(realization.get("basis_id")))
        if realization.get("phase36") != list(phase36):
            raise GremlinPostRealizationError(f"{kid} phase36 differs from PNCS realization")
        if realization.get("phase36_sha256") != _sha(list(phase36)):
            raise GremlinPostRealizationError(f"{kid} phase SHA mismatch")
        expected_realization_payload = {k: realization[k] for k in (
            "schema", "content_id", "basis_id", "derivation_id", "space", "coordinate_semantics", "coordinate_range", "phase36", "phase36_sha256"
        )}
        if realization.get("schema") != PNCS_REALIZATION_SCHEMA:
            raise GremlinPostRealizationError(f"{kid} PNCS realization schema mismatch")
        _content_id(realization.get("content_id"))
        if realization.get("realization_id") != _typed_id("pncs:realization36", expected_realization_payload):
            raise GremlinPostRealizationError(f"{kid} PNCS realization ID mismatch")
        expected_binding_payload = {k: binding[k] for k in (
            "schema", "realization_id", "content_id", "basis_id", "derivation_id", "phase36_sha256", "source_digest_sha256", "source_locator", "epistemic_operator", "canon_allowed"
        )}
        if binding.get("schema") != PNCS_BINDING_SCHEMA or binding.get("binding_id") != _typed_id("pncs:binding36", expected_binding_payload):
            raise GremlinPostRealizationError(f"{kid} PNCS binding mismatch")
        if binding.get("epistemic_operator") != "CHYBA" or binding.get("canon_allowed") is not False:
            raise GremlinPostRealizationError(f"{kid} PNCS binding authority mismatch")
        phase_index = mass_binding.get("phase_index")
        expected_mass = semantic_mass_v19(phase_index, phase36)
        expected_r = phase_order_parameter_v19(phase36)
        if mass_realization.get("semantic_mass") != expected_mass or mass_realization.get("order_parameter_R") != expected_r:
            raise GremlinPostRealizationError(f"{kid} semantic mass recomputation mismatch")
        mass_payload = {k: mass_realization[k] for k in (
            "schema", "content_id", "realization_id", "phase_index", "mass_contract_id", "runtime_source_sha256", "kappa", "alpha_m", "l3", "l4", "l5", "l_ratio", "order_parameter_R", "semantic_mass"
        )}
        if mass_realization.get("mass_realization_id") != _typed_id("pncs:mass", mass_payload):
            raise GremlinPostRealizationError(f"{kid} mass realization ID mismatch")
        mass_binding_payload = {k: mass_binding[k] for k in (
            "schema", "mass_realization_id", "content_id", "realization_id", "realization_binding_id", "phase_index", "mass_contract_id", "runtime_source_sha256", "runtime_source_locator", "semantic_mass", "epistemic_operator", "canon_allowed"
        )}
        if mass_binding.get("mass_binding_id") != _typed_id("pncs:mass-binding", mass_binding_payload):
            raise GremlinPostRealizationError(f"{kid} mass binding ID mismatch")
        if mass_binding.get("semantic_mass") != expected_mass:
            raise GremlinPostRealizationError(f"{kid} mass binding value mismatch")
        witness_payload = {k: witness[k] for k in (
            "kaku_id", "operator_id", "mass_binding_id", "semantic_mass_units", "phase36_sha256", "realization_id"
        )}
        if witness.get("witness_id") != _typed_id("pncs:mass-witness", witness_payload):
            raise GremlinPostRealizationError(f"{kid} mass witness ID mismatch")
        if witness.get("semantic_mass_units") != _mass_units(expected_mass):
            raise GremlinPostRealizationError(f"{kid} mass witness units mismatch")
        if witness.get("phase36_sha256") != realization.get("phase36_sha256"):
            raise GremlinPostRealizationError(f"{kid} witness phase mismatch")
        if len(vector36) != DIM:
            raise GremlinPostRealizationError(f"{kid} vector36 mismatch")
    if len(set(kaku_ids)) != len(kaku_ids):
        raise GremlinPostRealizationError("duplicate realized KAKU")
    if len(basis_ids) != 1 or record.get("basis_id") not in basis_ids:
        raise GremlinPostRealizationError("Radical basis binding mismatch")

    graph = record.get("radical_graph_payload")
    if not isinstance(graph, Mapping):
        raise GremlinPostRealizationError("Radical graph payload required")
    if graph.get("nodes") != sorted(kaku_ids):
        raise GremlinPostRealizationError("Radical graph nodes differ from realized KAKU")

    post = record.get("post_realization_scalars")
    if not isinstance(post, Mapping):
        raise GremlinPostRealizationError("post-realization scalar block required")
    cost_receipt = post.get("mass_aware_graph_cost")
    if not isinstance(cost_receipt, Mapping):
        raise GremlinPostRealizationError("mass-aware graph cost receipt required")
    cost = cost_receipt.get("cost")
    if not isinstance(cost, Mapping) or cost.get("schema") != PNCS_COST_SCHEMA:
        raise GremlinPostRealizationError("PNCS graph cost payload required")
    if cost.get("graph_sha256") != _sha(graph):
        raise GremlinPostRealizationError("graph cost hash mismatch")
    by_id = {item["kaku_id"]: item for item in realized}
    ordered_ids = sorted(by_id)
    expected_witnesses = [by_id[kid]["pncs_mass_witness_v21"] for kid in ordered_ids]
    expected_units = [w["semantic_mass_units"] for w in expected_witnesses]
    if cost.get("ordered_witness_ids") != [w["witness_id"] for w in expected_witnesses]:
        raise GremlinPostRealizationError("graph cost witness order mismatch")
    if cost.get("mass_units") != expected_units or cost.get("total_mass_units") != sum(expected_units):
        raise GremlinPostRealizationError("graph cost mass mismatch")
    expected_cost_id = _typed_id("pncs:graph-cost", cost)
    if cost_receipt.get("cost_id") != expected_cost_id:
        raise GremlinPostRealizationError("graph cost ID mismatch")
    cost_payload = {
        "schema": PNCS_COST_RECEIPT_SCHEMA,
        "cost_id": expected_cost_id,
        "cost": cost,
        "live_runtime": cost_receipt.get("live_runtime"),
    }
    if cost_receipt.get("receipt_sha256") != _sha(cost_payload):
        raise GremlinPostRealizationError("graph cost receipt mismatch")

    stability = post.get("operator_stability_bound")
    if not isinstance(stability, Mapping):
        raise GremlinPostRealizationError("operator stability bound required")
    L = float.fromhex(str(stability.get("L_character_f64_hex")))
    if not math.isfinite(L) or L < 0.0:
        raise GremlinPostRealizationError("invalid operator stability bound")

    supplied = str(record.get("post_realization_commitment", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", supplied):
        raise GremlinPostRealizationError("invalid post-realization commitment")
    core = dict(record)
    core.pop("post_realization_commitment", None)
    expected = hashlib.blake2b(POST_DOMAIN + _compact_json(core).encode("utf-8"), digest_size=32).hexdigest()
    if supplied != expected:
        raise GremlinPostRealizationError("post-realization commitment mismatch")
    return True
