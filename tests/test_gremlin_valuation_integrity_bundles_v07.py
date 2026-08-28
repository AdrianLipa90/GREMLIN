from __future__ import annotations

import copy

import pytest

from tools.gremlin_valuation_integrity_bundles_v07 import (
    CONTRADICTION_TERM,
    RECURSIVE_INTEGRITY_TERM,
    RECURSIVE_REENTRY_TERM,
    ValuationIntegrityError,
    build_contradiction_bundle_v07,
    build_contradiction_item_v07,
    build_kaku_valuation_binding_v07,
    build_recursive_integrity_bundle_v07,
    build_recursive_integrity_evidence_v07,
    build_valuation_item_v07,
    build_valuation_profile_v07,
    validate_contradiction_bundle_v07,
    validate_contradiction_item_v07,
    validate_kaku_valuation_binding_v07,
    validate_recursive_integrity_bundle_v07,
    validate_recursive_integrity_evidence_v07,
    validate_valuation_item_v07,
    validate_valuation_profile_v07,
)

H1 = "11" * 32
H2 = "22" * 32
H3 = "33" * 32
H4 = "44" * 32
H5 = "55" * 32


def valuation(option_id: str, value: float, scale: str = "declared:unit-v1") -> dict:
    return build_valuation_item_v07(
        option_id=option_id,
        value=value,
        scale_id=scale,
        source_ref=f"source:{option_id}",
        epistemic_status="DECLARED",
    )


def contradiction(cid: str = "c-1", left_id: str = "goal-a", right_id: str = "constraint-b") -> dict:
    return build_contradiction_item_v07(
        contradiction_id=cid,
        left_id=left_id,
        left_kind="GOAL",
        left_commitment=H1,
        right_id=right_id,
        right_kind="CONSTRAINT",
        right_commitment=H2,
        criterion_ref="criterion:compatibility",
        evidence_refs=["evidence:1"],
        epistemic_status="EVIDENCED",
    )


def recursive_evidence(aspect: str, state: str = "EVIDENCED", commitment: str = H3) -> dict:
    return build_recursive_integrity_evidence_v07(
        aspect=aspect,
        state=state,
        source_ref=f"source:{aspect.lower()}",
        source_commitment=commitment,
        epistemic_status="EVIDENCED" if state == "EVIDENCED" else "OPEN",
    )


def complete_recursive_evidence() -> list[dict]:
    return [
        recursive_evidence("TRAVERSE_CONTRADICTION", commitment=H1),
        recursive_evidence("REENTER_RELATIONAL_LOOP", commitment=H2),
        recursive_evidence("DISTINCTION_PRESERVATION", commitment=H3),
        recursive_evidence("FRAGMENTATION_CONTROL", commitment=H4),
    ]


def test_valuation_item_is_finite_deterministic_and_closed() -> None:
    a = valuation("a", 0.25)
    b = valuation("a", 0.25)
    assert a == b
    assert validate_valuation_item_v07(a)
    assert float.fromhex(a["value_f64_hex"]) == 0.25
    assert a["truth_authority"] is False
    assert a["epistemic_support_authority"] is False
    assert a["vector_bound"] is False
    assert a["execution_admitted"] is False
    assert a["canon_allowed"] is False

    with pytest.raises(ValuationIntegrityError):
        valuation("nan", float("nan"))


def test_valuation_profile_requires_one_declared_scale_and_canonical_order() -> None:
    profile = build_valuation_profile_v07(
        comparison_set_id="set:1",
        items=[valuation("z", 0.9), valuation("a", -0.1)],
        criterion_ref="criterion:preference",
    )
    assert validate_valuation_profile_v07(profile)
    assert [item["option_id"] for item in profile["items"]] == ["a", "z"]
    assert profile["normalization"] == "DECLARED_SCALE_PRESERVED"
    assert profile["cross_scale_comparison_allowed"] is False

    with pytest.raises(ValuationIntegrityError):
        build_valuation_profile_v07(
            comparison_set_id="set:bad-scale",
            items=[valuation("a", 0.1, "scale:A"), valuation("b", 0.2, "scale:B")],
            criterion_ref="criterion:preference",
        )

    with pytest.raises(ValuationIntegrityError):
        build_valuation_profile_v07(
            comparison_set_id="set:dup",
            items=[valuation("a", 0.1), valuation("a", 0.2)],
            criterion_ref="criterion:preference",
        )


def test_kaku_valuation_binds_exactly_one_option_and_keeps_vector_closed() -> None:
    profile = build_valuation_profile_v07(
        comparison_set_id="set:kaku",
        items=[valuation("left", -0.2), valuation("right", 0.4)],
        criterion_ref="criterion:choice",
    )
    binding = build_kaku_valuation_binding_v07(kaku_id="KAKU:17", option_id="right", profile=profile)
    assert validate_kaku_valuation_binding_v07(binding)
    assert binding["option_id"] == "right"
    assert binding["vector_synthesis_allowed"] is False
    assert binding["vector_bound"] is False

    with pytest.raises(ValuationIntegrityError):
        build_kaku_valuation_binding_v07(kaku_id="KAKU:17", option_id="missing", profile=profile)


def test_valuation_commitment_tamper_fails_closed() -> None:
    item = valuation("a", 0.25)
    tampered = copy.deepcopy(item)
    tampered["value_f64_hex"] = float(0.75).hex()
    with pytest.raises(ValuationIntegrityError):
        validate_valuation_item_v07(tampered)


def test_contradiction_is_declared_binary_incompatibility_with_evidence() -> None:
    item = contradiction()
    assert validate_contradiction_item_v07(item)
    assert item["semantic_term_id"] == CONTRADICTION_TERM
    assert item["relation"] == "DECLARED_INCOMPATIBILITY"
    assert len(item["endpoints"]) == 2
    assert item["severity_scalar_present"] is False
    assert item["vector_bound"] is False

    with pytest.raises(ValuationIntegrityError):
        build_contradiction_item_v07(
            contradiction_id="c:no-evidence",
            left_id="a",
            left_kind="GOAL",
            left_commitment=H1,
            right_id="b",
            right_kind="CONSTRAINT",
            right_commitment=H2,
            criterion_ref="criterion:x",
            evidence_refs=[],
            epistemic_status="OPEN",
        )

    with pytest.raises(ValuationIntegrityError):
        build_contradiction_item_v07(
            contradiction_id="c:bad-kind",
            left_id="a",
            left_kind="UNKNOWN",
            left_commitment=H1,
            right_id="b",
            right_kind="CONSTRAINT",
            right_commitment=H2,
            criterion_ref="criterion:x",
            evidence_refs=["evidence:1"],
            epistemic_status="OPEN",
        )


def test_contradiction_endpoint_order_is_canonical() -> None:
    forward = contradiction(cid="c:canonical", left_id="z", right_id="a")
    reverse = build_contradiction_item_v07(
        contradiction_id="c:canonical",
        left_id="a",
        left_kind="CONSTRAINT",
        left_commitment=H2,
        right_id="z",
        right_kind="GOAL",
        right_commitment=H1,
        criterion_ref="criterion:compatibility",
        evidence_refs=["evidence:1"],
        epistemic_status="EVIDENCED",
    )
    assert forward == reverse


def test_contradiction_bundle_counts_conflicts_without_scalarizing_load() -> None:
    c2 = build_contradiction_item_v07(
        contradiction_id="c-2",
        left_id="prediction-c",
        left_kind="PREDICTION",
        left_commitment=H3,
        right_id="commitment-d",
        right_kind="COMMITMENT",
        right_commitment=H4,
        criterion_ref="criterion:compatibility",
        evidence_refs=["evidence:2"],
        epistemic_status="EVIDENCED",
    )
    bundle = build_contradiction_bundle_v07(radical_id="RADICAL:1", items=[c2, contradiction()])
    assert validate_contradiction_bundle_v07(bundle)
    assert bundle["declared_conflict_count"] == 2
    assert bundle["contradiction_load_scalar_present"] is False
    assert bundle["scalarization_status"] == "UNRESOLVED"
    assert bundle["vector_bound"] is False

    with pytest.raises(ValuationIntegrityError):
        build_contradiction_bundle_v07(radical_id="RADICAL:1", items=[contradiction(), contradiction()])


def test_recursive_integrity_complete_evidence_is_structurally_complete() -> None:
    cb = build_contradiction_bundle_v07(radical_id="RADICAL:7", items=[contradiction()])
    bundle = build_recursive_integrity_bundle_v07(
        radical_id="RADICAL:7",
        contradiction_bundle=cb,
        recursive_reentry_commitment=H5,
        evidence=complete_recursive_evidence(),
    )
    assert validate_recursive_integrity_bundle_v07(bundle)
    assert bundle["semantic_term_id"] == RECURSIVE_INTEGRITY_TERM
    assert bundle["dependency_terms"] == [RECURSIVE_REENTRY_TERM, CONTRADICTION_TERM]
    assert bundle["antecedent_state"] == "COMPLETE_EVIDENCED"
    assert bundle["missing_aspects"] == []
    assert bundle["recursive_integrity_scalar_present"] is False
    assert bundle["scalarization_status"] == "UNRESOLVED"
    assert bundle["vector_bound"] is False


def test_recursive_integrity_open_on_missing_or_unresolved_and_failed_on_failed() -> None:
    cb = build_contradiction_bundle_v07(radical_id="RADICAL:8", items=[contradiction()])

    missing = build_recursive_integrity_bundle_v07(
        radical_id="RADICAL:8",
        contradiction_bundle=cb,
        recursive_reentry_commitment=H5,
        evidence=complete_recursive_evidence()[:-1],
    )
    assert missing["antecedent_state"] == "OPEN"
    assert "FRAGMENTATION_CONTROL" in missing["missing_aspects"]

    unresolved_evidence = complete_recursive_evidence()
    unresolved_evidence[0] = recursive_evidence("TRAVERSE_CONTRADICTION", state="UNRESOLVED", commitment=H1)
    unresolved = build_recursive_integrity_bundle_v07(
        radical_id="RADICAL:8",
        contradiction_bundle=cb,
        recursive_reentry_commitment=H5,
        evidence=unresolved_evidence,
    )
    assert unresolved["antecedent_state"] == "OPEN"

    failed_evidence = complete_recursive_evidence()
    failed_evidence[2] = recursive_evidence("DISTINCTION_PRESERVATION", state="FAILED", commitment=H3)
    failed = build_recursive_integrity_bundle_v07(
        radical_id="RADICAL:8",
        contradiction_bundle=cb,
        recursive_reentry_commitment=H5,
        evidence=failed_evidence,
    )
    assert failed["antecedent_state"] == "FAILED_EVIDENCE_PRESENT"


def test_recursive_integrity_requires_same_radical_lineage() -> None:
    cb = build_contradiction_bundle_v07(radical_id="RADICAL:A", items=[contradiction()])
    with pytest.raises(ValuationIntegrityError):
        build_recursive_integrity_bundle_v07(
            radical_id="RADICAL:B",
            contradiction_bundle=cb,
            recursive_reentry_commitment=H5,
            evidence=complete_recursive_evidence(),
        )


def test_recursive_integrity_evidence_and_bundle_tamper_fail_closed() -> None:
    evidence = recursive_evidence("TRAVERSE_CONTRADICTION")
    assert validate_recursive_integrity_evidence_v07(evidence)
    tampered_evidence = copy.deepcopy(evidence)
    tampered_evidence["state"] = "FAILED"
    with pytest.raises(ValuationIntegrityError):
        validate_recursive_integrity_evidence_v07(tampered_evidence)

    cb = build_contradiction_bundle_v07(radical_id="RADICAL:9", items=[contradiction()])
    bundle = build_recursive_integrity_bundle_v07(
        radical_id="RADICAL:9",
        contradiction_bundle=cb,
        recursive_reentry_commitment=H5,
        evidence=complete_recursive_evidence(),
    )
    tampered_bundle = copy.deepcopy(bundle)
    tampered_bundle["antecedent_state"] = "OPEN"
    with pytest.raises(ValuationIntegrityError):
        validate_recursive_integrity_bundle_v07(tampered_bundle)
