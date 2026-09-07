from __future__ import annotations

import pytest

from gremlin_mcp.equation_bundle import run_equation_witness_bundle


def test_bundle_dispatches_witnesses_and_collects_failures() -> None:
    bundle = {
        "bundle_id": "SYNTHETIC-EQUATION-BUNDLE-001",
        "classification": "SYNTHETIC_VALIDATION",
        "witnesses": [
            {
                "id": "NUM-OK",
                "kind": "numeric",
                "expression": "a*b",
                "symbols": {"a": 2.0, "b": 3.0},
                "reported_value": 6.0,
            },
            {
                "id": "NUM-BAD",
                "kind": "numeric",
                "expression": "a*b",
                "symbols": {"a": 2.0, "b": 3.0},
                "reported_value": 6000.0,
            },
            {
                "id": "ID-BAD",
                "kind": "symbolic_identity",
                "lhs": "sqrt(1-x)",
                "rhs": "1-x",
                "symbols": ["x"],
            },
        ],
    }
    result = run_equation_witness_bundle(bundle)
    assert result["status"] == "AUDIT_COMPLETE"
    assert result["witness_count"] == 3
    assert result["pass_count"] == 1
    assert result["fail_count"] == 2
    assert result["unresolved_count"] == 0
    assert result["detected_issue_ids"] == ["ID-BAD", "NUM-BAD"]
    assert result["authority"]["canon_allowed"] is False


def test_bundle_preserves_source_locator_and_fails_closed_on_unknown_kind() -> None:
    bundle = {
        "bundle_id": "SYNTHETIC-EQUATION-BUNDLE-002",
        "classification": "SYNTHETIC_VALIDATION",
        "witnesses": [
            {
                "id": "DIM-1",
                "kind": "dimensional_identity",
                "lhs": "E",
                "rhs": "m*c",
                "dimensions": {
                    "E": {"M": 1, "L": 2, "T": -2},
                    "m": {"M": 1},
                    "c": {"L": 1, "T": -1},
                },
                "source_locator": "synthetic:line-4",
            }
        ],
    }
    result = run_equation_witness_bundle(bundle)
    assert result["results"][0]["source_locator"] == "synthetic:line-4"
    assert result["detected_issue_ids"] == ["DIM-1"]

    bad = {
        "bundle_id": "BAD",
        "classification": "SYNTHETIC_VALIDATION",
        "witnesses": [{"id": "X", "kind": "magic"}],
    }
    with pytest.raises(ValueError, match="unsupported witness kind"):
        run_equation_witness_bundle(bad)


def test_bundle_rejects_duplicate_witness_ids() -> None:
    bundle = {
        "bundle_id": "DUP",
        "classification": "SYNTHETIC_VALIDATION",
        "witnesses": [
            {"id": "X", "kind": "numeric", "expression": "1", "symbols": {}, "reported_value": 1},
            {"id": "X", "kind": "numeric", "expression": "1", "symbols": {}, "reported_value": 1},
        ],
    }
    with pytest.raises(ValueError, match="duplicate witness id"):
        run_equation_witness_bundle(bundle)
