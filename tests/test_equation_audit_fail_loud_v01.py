from __future__ import annotations

import pytest

from gremlin_mcp.equation_audit import (
    audit_derivation_claim,
    audit_dimensional_identity,
    audit_numeric_formula_claim,
    audit_symbolic_identity,
)


def test_numeric_audit_rejects_string_and_boolean_numbers() -> None:
    with pytest.raises(ValueError, match="numeric symbol x must be a finite number"):
        audit_numeric_formula_claim(expression="x", symbols={"x": "1.0"}, reported_value=1.0)  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="numeric symbol x must be a finite number"):
        audit_numeric_formula_claim(expression="x", symbols={"x": True}, reported_value=1.0)  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="reported_value must be a finite number"):
        audit_numeric_formula_claim(expression="1", symbols={}, reported_value="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="rel_tol must be a finite number"):
        audit_numeric_formula_claim(expression="1", symbols={}, reported_value=1.0, rel_tol="1e-9")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="abs_tol must be a finite number"):
        audit_numeric_formula_claim(expression="1", symbols={}, reported_value=1.0, abs_tol=False)  # type: ignore[arg-type]


def test_numeric_audit_rejects_non_string_expression_and_non_mapping_symbols() -> None:
    with pytest.raises(ValueError, match="expression must be a string"):
        audit_numeric_formula_claim(expression=123, symbols={}, reported_value=1.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="symbols must be an object"):
        audit_numeric_formula_claim(expression="1", symbols=[("x", 1.0)], reported_value=1.0)  # type: ignore[arg-type]


def test_zero_computed_nonzero_reported_value_produces_finite_json_receipt() -> None:
    result = audit_numeric_formula_claim(expression="0", symbols={}, reported_value=1.0)
    assert result["status"] == "FAIL"
    assert result["relative_error"] is None
    assert isinstance(result["audit_commitment"], str)
    assert len(result["audit_commitment"]) == 64


def test_dimensions_reject_non_string_keys_and_string_powers() -> None:
    with pytest.raises(ValueError, match="dimension symbol must be a string"):
        audit_dimensional_identity("x", "x", dimensions={1: {"L": 1}})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="dimension axis for x must be a string"):
        audit_dimensional_identity("x", "x", dimensions={"x": {1: 1}})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="dimension power x.L must be a finite number"):
        audit_dimensional_identity("x", "x", dimensions={"x": {"L": "1"}})  # type: ignore[dict-item]


def test_symbolic_audit_rejects_string_container_non_string_names_and_duplicates() -> None:
    with pytest.raises(ValueError, match="symbols must be an iterable of strings"):
        audit_symbolic_identity("x", "x", symbols="x")
    with pytest.raises(ValueError, match="symbols must be a string"):
        audit_symbolic_identity("x", "x", symbols=[1])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="duplicate names"):
        audit_symbolic_identity("x", "x", symbols=["x", "x"])


def test_derivation_fields_and_assumptions_do_not_stringify() -> None:
    with pytest.raises(ValueError, match="equation must be a string"):
        audit_derivation_claim(equation=123, target="x", claimed_expression="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="target must be a string"):
        audit_derivation_claim(equation="x=1", target=1, claimed_expression="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="claimed_expression must be a string"):
        audit_derivation_claim(equation="x=1", target="x", claimed_expression=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="assumptions must be an object"):
        audit_derivation_claim(equation="x=1", target="x", claimed_expression="1", assumptions=[("x", "real")])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="assumption for x must be a string"):
        audit_derivation_claim(equation="x=1", target="x", claimed_expression="1", assumptions={"x": True})  # type: ignore[dict-item]
