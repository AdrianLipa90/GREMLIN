from __future__ import annotations

import pytest

from gremlin_mcp.equation_bundle import run_equation_witness_bundle


def _numeric_witness(**overrides):
    row = {
        "id": "W-1",
        "kind": "numeric",
        "expression": "x + 1",
        "symbols": {"x": 1.0},
        "reported_value": 2.0,
        "rel_tol": 1e-9,
        "abs_tol": 0.0,
        "source_locator": "fixture:Eq. (1)",
        "source_excerpt": "Eq. (1): y = x + 1 ~= 2",
    }
    row.update(overrides)
    return row


def _bundle(witnesses=None, **overrides):
    bundle = {
        "bundle_id": "bundle-1",
        "classification": "CANDIDATE",
        "witnesses": [_numeric_witness()] if witnesses is None else witnesses,
    }
    bundle.update(overrides)
    return bundle


def test_bundle_must_be_mapping() -> None:
    with pytest.raises(ValueError, match="bundle must be an object"):
        run_equation_witness_bundle("bad")  # type: ignore[arg-type]


def test_bundle_id_and_classification_do_not_stringify() -> None:
    with pytest.raises(ValueError, match="bundle_id must be a string"):
        run_equation_witness_bundle(_bundle(bundle_id=123))
    with pytest.raises(ValueError, match="classification must be a string"):
        run_equation_witness_bundle(_bundle(classification=True))


def test_witnesses_must_be_list_of_objects() -> None:
    with pytest.raises(ValueError, match="witnesses must be a list"):
        run_equation_witness_bundle(_bundle(witnesses="bad"))
    with pytest.raises(ValueError, match="witnesses must contain only objects"):
        run_equation_witness_bundle(_bundle(witnesses=["bad"]))


def test_witness_id_and_kind_do_not_stringify() -> None:
    with pytest.raises(ValueError, match="witness id must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(id=123)]))
    with pytest.raises(ValueError, match="witness kind must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(kind=1)]))


def test_numeric_fields_do_not_coerce_strings_or_booleans() -> None:
    for field, value, pattern in (
        ("reported_value", "2.0", "reported_value must be a finite number"),
        ("reported_value", True, "reported_value must be a finite number"),
        ("rel_tol", "1e-9", "rel_tol must be a finite number"),
        ("abs_tol", False, "abs_tol must be a finite number"),
    ):
        with pytest.raises(ValueError, match=pattern):
            run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(**{field: value})]))


def test_numeric_expression_and_symbols_require_exact_types() -> None:
    with pytest.raises(ValueError, match="numeric witness expression must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(expression=123)]))
    with pytest.raises(ValueError, match="numeric witness symbols must be an object"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(symbols=[("x", 1.0)])]))


def test_symbolic_symbols_must_be_list_of_strings() -> None:
    witness = {
        "id": "W-S",
        "kind": "symbolic_identity",
        "lhs": "x + x",
        "rhs": "2*x",
        "symbols": "x",
    }
    with pytest.raises(ValueError, match="symbolic witness symbols must be a list"):
        run_equation_witness_bundle(_bundle(witnesses=[witness]))

    witness["symbols"] = ["x", 1]
    with pytest.raises(ValueError, match="symbolic witness symbols must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[witness]))


def test_optional_source_metadata_does_not_stringify() -> None:
    with pytest.raises(ValueError, match="source_locator must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(source_locator=123)]))
    with pytest.raises(ValueError, match="source_excerpt must be a string"):
        run_equation_witness_bundle(_bundle(witnesses=[_numeric_witness(source_excerpt=["Eq"])]))


def test_duplicate_witness_ids_fail_loud() -> None:
    a = _numeric_witness(id="dup")
    b = _numeric_witness(id="dup", expression="x + 2", reported_value=3.0)
    with pytest.raises(ValueError, match="duplicate witness id"):
        run_equation_witness_bundle(_bundle(witnesses=[a, b]))
