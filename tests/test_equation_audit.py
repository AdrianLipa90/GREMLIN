from __future__ import annotations

import math

import pytest

from gremlin_mcp.equation_audit import (
    audit_derivation_claim,
    audit_dimensional_identity,
    audit_numeric_formula_claim,
    audit_symbolic_identity,
)


def test_numeric_formula_recomputes_and_detects_large_error() -> None:
    symbols = {"a": 2.0, "b": 3.0, "c": 5.0}
    ok = audit_numeric_formula_claim(
        expression="a*b/c",
        symbols=symbols,
        reported_value=1.2,
        rel_tol=1e-12,
    )
    assert ok["status"] == "PASS"
    assert ok["matches"] is True
    assert ok["computed_value"] == pytest.approx(1.2)

    bad = audit_numeric_formula_claim(
        expression="a*b/c",
        symbols=symbols,
        reported_value=1.2e12,
        rel_tol=1e-12,
    )
    assert bad["status"] == "FAIL"
    assert bad["matches"] is False
    assert bad["orders_of_magnitude_error"] == pytest.approx(12.0)
    assert bad["authority"]["canon_allowed"] is False


def test_numeric_formula_supports_physical_constants_without_special_cases() -> None:
    symbols = {
        "G": 6.67430e-11,
        "h": 6.62607015e-34,
        "f": 5.5e14,
        "c": 299792458.0,
    }
    result = audit_numeric_formula_claim(
        expression="4*pi*G*h*f**2/c**5",
        symbols=symbols,
        reported_value=6.94e-56,
        rel_tol=2e-3,
    )
    assert result["status"] == "PASS"
    assert result["computed_value"] == pytest.approx(6.94e-56, rel=2e-3)


def test_dimensional_identity_passes_energy_and_rejects_wrong_power() -> None:
    dimensions = {
        "E": {"M": 1, "L": 2, "T": -2},
        "m": {"M": 1},
        "c": {"L": 1, "T": -1},
    }
    good = audit_dimensional_identity("E", "m*c**2", dimensions=dimensions)
    assert good["status"] == "PASS"
    assert good["dimensionally_consistent"] is True

    bad = audit_dimensional_identity("E", "m*c", dimensions=dimensions)
    assert bad["status"] == "FAIL"
    assert bad["dimensionally_consistent"] is False


def test_symbolic_identity_distinguishes_nonidentical_expressions() -> None:
    good = audit_symbolic_identity("1 - x", "1 - x", symbols=["x"])
    assert good["status"] == "PASS"
    assert good["identical"] is True

    bad = audit_symbolic_identity("sqrt(1 - x)", "1 - x", symbols=["x"])
    assert bad["status"] == "FAIL"
    assert bad["identical"] is False


def test_derivation_audit_solves_equation_then_checks_claim() -> None:
    # Generic radial-null style algebra: -A*c^2 + v^2/A = 0 -> v = +/- A*c.
    assumptions = {"A": "positive", "c": "positive", "v": "real"}
    wrong = audit_derivation_claim(
        equation="-A*c**2 + v**2/A = 0",
        target="v",
        claimed_expression="c*sqrt(A)",
        assumptions=assumptions,
    )
    assert wrong["status"] == "FAIL"
    assert wrong["claim_matches_solution"] is False
    assert any("A*c" in candidate.replace(" ", "") or "c*A" in candidate.replace(" ", "") for candidate in wrong["derived_solutions"])

    right = audit_derivation_claim(
        equation="-A*c**2 + v**2/A = 0",
        target="v",
        claimed_expression="A*c",
        assumptions=assumptions,
    )
    assert right["status"] == "PASS"
    assert right["claim_matches_solution"] is True


def test_fail_closed_on_unknown_symbol_and_nonconstant_dimension_exponent() -> None:
    with pytest.raises(ValueError, match="unknown symbol"):
        audit_numeric_formula_claim(expression="a*z", symbols={"a": 1.0}, reported_value=1.0)

    with pytest.raises(ValueError, match="constant numeric exponent"):
        audit_dimensional_identity(
            "q",
            "x**n",
            dimensions={"q": {"L": 1}, "x": {"L": 1}, "n": {}},
        )
