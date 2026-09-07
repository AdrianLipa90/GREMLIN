from __future__ import annotations

import hashlib
import json
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _run_witness(witness: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(witness.get("kind") or "").strip()
    if kind == "numeric":
        result = audit_numeric_formula_claim(
            expression=str(witness["expression"]),
            symbols=dict(witness.get("symbols") or {}),
            reported_value=float(witness["reported_value"]),
            rel_tol=float(witness.get("rel_tol", 1e-9)),
            abs_tol=float(witness.get("abs_tol", 0.0)),
        )
    elif kind == "dimensional_identity":
        result = audit_dimensional_identity(
            str(witness["lhs"]),
            str(witness["rhs"]),
            dimensions=dict(witness.get("dimensions") or {}),
        )
    elif kind == "symbolic_identity":
        result = audit_symbolic_identity(
            str(witness["lhs"]),
            str(witness["rhs"]),
            symbols=list(witness.get("symbols") or []),
        )
    elif kind == "derivation":
        result = audit_derivation_claim(
            equation=str(witness["equation"]),
            target=str(witness["target"]),
            claimed_expression=str(witness["claimed_expression"]),
            assumptions=dict(witness.get("assumptions") or {}),
        )
    else:
        raise ValueError(f"unsupported witness kind: {kind}")
    return result


def run_equation_witness_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    bundle_id = str(bundle.get("bundle_id") or "").strip()
    if not bundle_id:
        raise ValueError("bundle_id must be non-empty")
    classification = str(bundle.get("classification") or "").strip()
    if not classification:
        raise ValueError("classification must be non-empty")

    witnesses = list(bundle.get("witnesses") or [])
    ids = [str(row.get("id") or "").strip() for row in witnesses]
    if any(not witness_id for witness_id in ids):
        raise ValueError("witness id must be non-empty")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate witness id")

    rows: list[dict[str, Any]] = []
    for witness in witnesses:
        witness_id = str(witness["id"]).strip()
        audit = _run_witness(witness)
        rows.append(
            {
                "id": witness_id,
                "kind": str(witness["kind"]),
                "source_locator": witness.get("source_locator"),
                "source_excerpt": witness.get("source_excerpt"),
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
