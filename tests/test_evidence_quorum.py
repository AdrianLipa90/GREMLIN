import pytest

from gremlin_mcp.evidence_quorum import (
    CONFLICT_DEFER_TO_HOUND,
    QUORUM_INSUFFICIENT,
    QUORUM_SUFFICIENT,
    assess_family_quorum,
)
from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT


def _row(evidence_id, family, stance, confidence=1.0):
    return {
        "evidence_id": evidence_id,
        "source_family": family,
        "stance": stance,
        "payload_commitment": f"payload:{evidence_id}",
        "credibility": confidence,
    }


def test_two_records_from_same_family_do_not_form_two_family_quorum():
    result = assess_family_quorum(
        [_row("a", "fam-1", SUPPORT), _row("b", "fam-1", SUPPORT)],
        min_unipolar_families=2,
    )
    assert result["state"] == QUORUM_INSUFFICIENT
    assert result["support_family_count"] == 1
    assert result["quorum_satisfied"] is False


def test_two_distinct_support_families_clear_quorum():
    result = assess_family_quorum(
        [_row("a", "fam-1", SUPPORT), _row("b", "fam-2", SUPPORT)],
        min_unipolar_families=2,
    )
    assert result["state"] == QUORUM_SUFFICIENT
    assert result["support_family_count"] == 2
    assert result["quorum_satisfied"] is True


def test_conflict_is_never_resolved_by_family_majority():
    result = assess_family_quorum(
        [
            _row("a", "fam-1", SUPPORT),
            _row("b", "fam-2", SUPPORT),
            _row("c", "fam-3", SUPPORT),
            _row("d", "fam-4", CONTRADICT),
        ],
        min_unipolar_families=2,
    )
    assert result["state"] == CONFLICT_DEFER_TO_HOUND
    assert result["conflict_present"] is True
    assert result["quorum_gate_applicable"] is False
    assert result["quorum_satisfied"] is None


def test_high_confidence_single_family_cannot_substitute_for_diversity():
    result = assess_family_quorum(
        [_row("a", "fam-1", SUPPORT, confidence=0.999)],
        min_unipolar_families=2,
    )
    assert result["state"] == QUORUM_INSUFFICIENT
    assert result["confidence_policy"] == "CONFIDENCE_METADATA_DOES_NOT_SUBSTITUTE_FOR_FAMILY_DIVERSITY"


def test_quorum_minimum_is_bounded_fail_closed():
    with pytest.raises(ValueError, match="min_unipolar_families"):
        assess_family_quorum([_row("a", "fam-1", SUPPORT)], min_unipolar_families=99)


def test_quorum_minimum_does_not_coerce_bool_float_or_string():
    for value in (True, 2.0, "2"):
        with pytest.raises(ValueError, match="must be an integer"):
            assess_family_quorum(
                [_row("a", "fam-1", SUPPORT)],
                min_unipolar_families=value,  # type: ignore[arg-type]
            )


def test_quorum_rejects_non_mapping_evidence_rows():
    with pytest.raises(ValueError, match="only objects"):
        assess_family_quorum([_row("a", "fam-1", SUPPORT), "bad-row"])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="iterable of objects"):
        assess_family_quorum("not-evidence")  # type: ignore[arg-type]


def test_quorum_rejects_unknown_stance_instead_of_silently_dropping_it():
    with pytest.raises(ValueError, match="unsupported evidence stance"):
        assess_family_quorum([_row("a", "fam-1", "UNRESOLVED")])


def test_quorum_rejects_non_string_family_instead_of_coercing():
    with pytest.raises(ValueError, match="source_family must be a string"):
        assess_family_quorum([_row("a", 123, SUPPORT)])
