from __future__ import annotations

from gremlin_mcp.equation_extract import propose_equation_witnesses


def test_extracts_numeric_formula_when_all_symbols_are_declared() -> None:
    text = """
    a = 2.0
    b = 3.0
    c = 5.0
    Eq. (1): q = a*b/c ~= 1.2
    """
    result = propose_equation_witnesses(text, source_id="synthetic:1")
    numeric = [row for row in result["witness_proposals"] if row["kind"] == "numeric"]
    assert len(numeric) == 1
    assert numeric[0]["expression"] == "a*b/c"
    assert numeric[0]["reported_value"] == 1.2
    assert numeric[0]["symbols"] == {"a": 2.0, "b": 3.0, "c": 5.0}
    assert numeric[0]["epistemic_status"] == "CANDIDATE_WITNESS"
    assert result["authority"]["canon_allowed"] is False


def test_unresolved_numeric_formula_stays_candidate_and_is_not_executable() -> None:
    text = "Eq. (2): z = alpha*x**2 ~= 4.0"
    result = propose_equation_witnesses(text, source_id="synthetic:2")
    unresolved = result["unresolved_proposals"]
    assert len(unresolved) == 1
    assert unresolved[0]["kind"] == "numeric"
    assert unresolved[0]["missing_symbols"] == ["alpha", "x"]
    assert result["witness_proposals"] == []


def test_repeated_definitions_generate_symbolic_identity_candidate() -> None:
    text = """
    Eq. (3): y = 4*pi*k*x**2/c**5
    Eq. (4): y = 2*k*x**2/c**5
    """
    result = propose_equation_witnesses(text, source_id="synthetic:3")
    symbolic = [row for row in result["witness_proposals"] if row["kind"] == "symbolic_identity"]
    assert len(symbolic) == 1
    assert symbolic[0]["lhs"] == "4*pi*k*x**2/c**5"
    assert symbolic[0]["rhs"] == "2*k*x**2/c**5"
    assert symbolic[0]["symbols"] == ["c", "k", "x"]
    assert symbolic[0]["source_locator"] == "synthetic:3:Eq. (3) <-> Eq. (4)"


def test_equal_repeated_definitions_do_not_create_false_conflict_candidate() -> None:
    text = """
    Eq. (5): y = a+b
    Eq. (6): y = a + b
    """
    result = propose_equation_witnesses(text, source_id="synthetic:4")
    assert not [row for row in result["witness_proposals"] if row["kind"] == "symbolic_identity"]


def test_unicode_scientific_notation_and_math_symbols_are_normalized_conservatively() -> None:
    text = """
    G = 6.674 × 10^-11
    h = 6.626 × 10^-34
    c = 2.998 × 10^8
    Eq. (7): K = 4*pi*G*h/c^5 ≈ 2.052 × 10^-95
    """
    result = propose_equation_witnesses(text, source_id="synthetic:5")
    numeric = [row for row in result["witness_proposals"] if row["kind"] == "numeric"]
    assert len(numeric) == 1
    assert numeric[0]["expression"] == "4*pi*G*h/c**5"
    assert numeric[0]["reported_value"] == 2.052e-95
    assert numeric[0]["symbols"]["G"] == 6.674e-11


def test_extracts_numeric_substitution_from_relation_chain_without_external_constants() -> None:
    text = "Eq. (9): (k*a*b)/(x**5) = (4*(6e-2)*(2e-3))/((3e1)**5) ≈ 1e-9"
    result = propose_equation_witnesses(text, source_id="synthetic:chain")
    numeric = [row for row in result["witness_proposals"] if row["kind"] == "numeric"]
    assert len(numeric) == 1
    assert numeric[0]["expression"] == "(4*(6e-2)*(2e-3))/((3e1)**5)"
    assert numeric[0]["reported_value"] == 1e-9
    assert numeric[0]["symbols"] == {}
    assert numeric[0]["source_locator"] == "synthetic:chain:Eq. (9)"
    assert numeric[0]["extraction_basis"] == "FINAL_NUMERIC_SUBSTITUTION_BEFORE_APPROXIMATION"


def test_relation_chain_with_unbound_symbols_remains_unresolved() -> None:
    text = "Eq. (10): lhs = alpha*3 ≈ 6"
    result = propose_equation_witnesses(text, source_id="synthetic:chain-unresolved")
    unresolved = [row for row in result["unresolved_proposals"] if row["kind"] == "numeric"]
    assert len(unresolved) == 1
    assert unresolved[0]["missing_symbols"] == ["alpha"]


def test_ignores_prose_equality_and_does_not_execute_function_calls() -> None:
    text = """
    The conclusion is that x = important for the interpretation.
    Eq. (8): z = __import__('os').system('echo nope') ~= 0
    """
    result = propose_equation_witnesses(text, source_id="synthetic:6")
    assert result["witness_proposals"] == []
    assert result["rejected_spans"]


def test_fail_closed_for_empty_text() -> None:
    result = propose_equation_witnesses("", source_id="synthetic:empty")
    assert result["status"] == "NO_TEXT_FAIL_CLOSED"
    assert result["witness_proposals"] == []
