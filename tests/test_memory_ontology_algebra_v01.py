from fractions import Fraction
import math

import pytest

from gremlin_mcp.memory_ontology_algebra import (
    BehavioralInverseWitness,
    HistoryStep,
    HistoricalTrace,
    IntegerPath,
    MemoryOntologyAlgebraError,
    TernaryPath,
    TypedMorphism,
    associate_prime_codes,
    build_memory_ontology_handoff,
    certified_behavioral_core,
    decode_prime_word,
    dissociate_prime_code,
    encode_prime_word,
    memory_ontology_manifest,
    path_boundary,
    path_holonomy,
    path_phase,
    prime_position_shift,
)


def test_source_manifest_is_bound_to_merged_memory_ontology_main():
    manifest = memory_ontology_manifest()
    assert manifest["source"]["main_commit"] == "c0973d26cc64c0d9018b67707e5708e084017ad8"
    assert manifest["source"]["blobs"]["final_receipt"] == "7402cc9c3ce8c5d2ba61942f709fb2c26f8e4e77"
    assert manifest["claims"]["canon_allowed"] is False
    assert len(manifest["manifest_sha256"]) == 64\n    assert all(len(v) == 40 for v in manifest["source"]["blobs"].values())


def test_prime_word_roundtrip_preserves_order():
    word = (2, 1, 4, 3)
    code = encode_prime_word(word)
    assert decode_prime_word(code) == word
    assert encode_prime_word((1, 2)) != encode_prime_word((2, 1))


def test_prime_hilbert_association_and_declared_cut_dissociation():
    left = encode_prime_word((2, 3, 1))
    right = encode_prime_word((4, 1))
    joined = associate_prime_codes(left, right)
    assert joined == left * prime_position_shift(right, 3)
    a, b = dissociate_prime_code(joined, 3)
    assert a == left and b == right


def test_historical_roundtrip_is_not_erased_by_behavioral_quotient_source_layer():
    f = HistoryStep("e", "a", "b", 1, inverse_edge_id="e^-1")
    r = HistoryStep("e^-1", "b", "a", 2, inverse_edge_id="e")
    trace = HistoricalTrace("memory:m", (f, r))
    hist = trace.historical_signature()
    beh = trace.behavioral_quotient().behavioral_signature()
    assert hist["steps"] != []
    assert hist["prime_lineage_code"] != 1
    assert beh["reduced_path"] == []
    assert hist["commitment"] != beh["commitment"]


def test_equal_symbol_is_not_enough_for_false_cancellation():
    a = HistoryStep("e1", "a", "b", 7, inverse_edge_id="e1^-1")
    b = HistoryStep("e2", "b", "c", 7, inverse_edge_id="e2^-1")
    trace = HistoricalTrace("memory:m", (a, b))
    assert len(trace.behavioral_quotient().reduced_steps) == 2


def test_endpoint_reversal_without_explicit_inverse_edge_is_not_cancelled():
    a = HistoryStep("e1", "a", "b", 3)
    b = HistoryStep("e2", "b", "a", 4)
    trace = HistoricalTrace("memory:m", (a, b))
    assert len(trace.behavioral_quotient().reduced_steps) == 2


def morph(mid, src, dst, *, error=0, invertible=True, lineage=(1,), ssec="S", tsec="S"):
    return TypedMorphism(
        mid,
        src,
        dst,
        "route_choice",
        "EXACT",
        error,
        100,
        ssec,
        tsec,
        lineage=lineage,
        invertible_on_declared_image=invertible,
    )


def witness(fid="f", iid="g"):
    return BehavioralInverseWitness(
        "w:1", fid, iid, "TEST", "receipt:test", True, True, True
    )


def test_behavioral_and_historical_signatures_are_separate():
    a = morph("a", "x", "y", lineage=(1,))
    b = morph("b", "x", "y", lineage=(2, 3))
    assert a.behavioral_signature() == b.behavioral_signature()
    assert a.historical_signature() != b.historical_signature()


def test_unwitnessed_invertible_arrow_is_excluded_from_core():
    f = morph("f", "x", "y")
    core = certified_behavioral_core((f,), ())
    assert core["morphism_ids"] == []
    assert core["excluded_unwitnessed_invertible_ids"] == ["f"]


def test_exact_inverse_pair_enters_core():
    f = morph("f", "x", "y", ssec="A", tsec="B")
    g = morph("g", "y", "x", ssec="B", tsec="A")
    core = certified_behavioral_core((f, g), (witness(),))
    assert core["morphism_ids"] == ["f", "g"]
    assert core["inverse_pairs"] == [("f", "g")]


def test_nonzero_error_inverse_pair_fails_closed():
    f = morph("f", "x", "y", error=Fraction(1, 100))
    g = morph("g", "y", "x")
    with pytest.raises(MemoryOntologyAlgebraError):
        certified_behavioral_core((f, g), (witness(),))


def test_ternary_composition_stays_exact_or_lifts_without_mod3():
    a = TernaryPath((1, 0, -1))
    b = TernaryPath((-1, 1, 0))
    c = a.compose(b)
    assert isinstance(c, TernaryPath)
    assert c.coeffs == (0, 1, -1)
    overflow = TernaryPath((1,)).compose(TernaryPath((1,)))
    assert isinstance(overflow, IntegerPath)
    assert overflow.coeffs == (2,)
    assert overflow.coeffs != (-1,)


def test_boundary_and_u1_holonomy_are_exact_on_path_sector():
    incidence = (
        (-1, 0, 1),
        (1, -1, 0),
        (0, 1, -1),
    )
    cycle = TernaryPath((1, 1, 1))
    assert path_boundary(incidence, cycle) == (0, 0, 0)
    theta = (0.2, -0.4, 0.9)
    a = TernaryPath((1, 0, 0))
    b = TernaryPath((0, -1, 1))
    c = a.compose(b)
    assert isinstance(c, TernaryPath)
    assert abs(path_holonomy(c, theta) - path_holonomy(a, theta) * path_holonomy(b, theta)) < 1e-12
    assert 0 <= path_phase(c, theta) < 2 * math.pi


def test_handoff_routes_to_memory_ontology_bestiary_roles_and_stays_candidate_only():
    fstep = HistoryStep("e", "a", "b", 1, inverse_edge_id="e^-1")
    rstep = HistoryStep("e^-1", "b", "a", 2, inverse_edge_id="e")
    trace = HistoricalTrace("memory:m", (fstep, rstep))
    f = morph("f", "x", "y", ssec="A", tsec="B")
    g = morph("g", "y", "x", ssec="B", tsec="A")
    out = build_memory_ontology_handoff(
        subject_id="memory:m",
        generation_id="gen:1",
        task_id="task:1",
        historical_trace=trace,
        morphisms=(f, g),
        witnesses=(witness(),),
    )
    assert out["analysis_route_mask"] == ["SPIDER", "RAVEN", "HOUND", "MOLE", "OWL", "MANTIS"]
    assert out["memory_followup_roles"] == ["ELEPHANT", "BEES"]
    assert out["synthesis_role"] == "BELZEBUB"
    assert out["aggregate_role"] == "GREMLIN"
    assert out["historical_signature"]["steps"]
    assert out["behavioral_signature"]["reduced_path"] == []
    assert out["execution_semantics"]["silent_mod3"] is False
    assert out["canon_allowed"] is False
    assert len(out["handoff_sha256"]) == 64
