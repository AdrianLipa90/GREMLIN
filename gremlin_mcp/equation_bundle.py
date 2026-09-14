from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from gremlin_mcp.equation_audit import (
    audit_derivation_claim,
    audit_dimensional_identity,
    audit_numeric_formula_claim,
    audit_symbolic_identity,
)

SCHEMA = "GREMLIN_EQUATION_WITNESS_BUNDLE_V0_1"
VERSION = "0.1.0"


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("equation witness bundle data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty(value, field)


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return dict(value)


def _mapping_list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{field} must contain only objects")
    return [dict(row) for row in value]


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return [_nonempty(item, field) for item in value]


def _number(value: Any, field: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    if nonnegative and number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def _run_witness(witness: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(witness, Mapping):
        raise ValueError("witness must be an object")
    kind = _nonempty(witness.get("kind"), "witness kind")
    if kind == "numeric":
        symbols = _mapping(witness.get("symbols"), "numeric witness symbols")
        expression = _nonempty(witness.get("expression"), "numeric witness expression")
        reported_value = _number(witness.get("reported_value"), "reported_value")
        rel_tol = _number(witness.get("rel_tol", 1e-9), "rel_tol", nonnegative=True)
        abs_tol = _number(witness.get("abs_tol", 0.0), "abs_tol", nonnegative=True)
        result = audit_numeric_formula_claim(
            expression=expression,
            symbols=symbols,
            reported_value=reported_value,
            rel_tol=rel_tol,
            abs_tol=abs_tol,
        )
    elif kind == "dimensional_identity":
        result = audit_dimensional_identity(
            _nonempty(witness.get("lhs"), "dimensional witness lhs"),
            _nonempty(witness.get("rhs"), "dimensional witness rhs"),
            dimensions=_mapping(witness.get("dimensions"), "dimensional witness dimensions"),
        )
    elif kind == "symbolic_identity":
        result = audit_symbolic_identity(
            _nonempty(witness.get("lhs"), "symbolic witness lhs"),
            _nonempty(witness.get("rhs"), "symbolic witness rhs"),
            symbols=_string_list(witness.get("symbols"), "symbolic witness symbols"),
        )
    elif kind == "derivation":
        result = audit_derivation_claim(
            equation=_nonempty(witness.get("equation"), "derivation equation"),
            target=_nonempty(witness.get("target"), "derivation target"),
            claimed_expression=_nonempty(witness.get("claimed_expression"), "claimed_expression"),
            assumptions=_mapping(witness.get("assumptions"), "derivation assumptions"),
        )
    else:
        raise ValueError(f"unsupported witness kind: {kind}")
    if not isinstance(result, Mapping):
        raise RuntimeError("equation audit returned a non-object result")
    status = result.get("status")
    if status not in {"PASS", "FAIL", "UNRESOLVED"}:
        raise RuntimeError(f"equation audit returned unsupported status: {status!r}")
    return dict(result)


def run_equation_witness_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise ValueError("bundle must be an object")
    bundle_id = _nonempty(bundle.get("bundle_id"), "bundle_id")
    classification = _nonempty(bundle.get("classification"), "classification")

    witnesses = _mapping_list(bundle.get("witnesses"), "witnesses")
    ids = [_nonempty(row.get("id"), "witness id") for row in witnesses]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate witness id")

    rows: list[dict[str, Any]] = []
    for witness_id, witness in zip(ids, witnesses):
        audit = _run_witness(witness)
        kind = _nonempty(witness.get("kind"), "witness kind")
        rows.append(
            {
                "id": witness_id,
                "kind": kind,
                "source_locator": _optional_text(witness.get("source_locator"), "source_locator"),
                "source_excerpt": _optional_text(witness.get("source_excerpt"), "source_excerpt"),
                "audit": audit,
                "status": audit["status"],
            }
        )

    detected = sorted(row["id"] for row in rows if row["status"] == "FAIL")
    unresolved = sorted(row["id"] for row in rows if row["status"] == "UNRESOLVED")
    pass_count = sum(row["status"] == "PASS" for row in rows)
    fail_count = sum(row["status"] == "FAIL" for row in rows)

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "bundle_id": bundle_id,
        "classification": classification,
        "status": "AUDIT_COMPLETE",
        "witness_count": len(rows),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unresolved_count": len(unresolved),
        "detected_issue_ids": detected,
        "unresolved_issue_ids": unresolved,
        "results": rows,
        "scope_boundary": [
            "STRUCTURED_WITNESSES_ONLY",
            "FAIL_MEANS_WITNESS_INCONSISTENCY_NOT_GLOBAL_PAPER_REJECTION",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["bundle_commitment"] = _commit(b"GREMLIN-EQUATION-BUNDLE/v0.1", core)
    return core
