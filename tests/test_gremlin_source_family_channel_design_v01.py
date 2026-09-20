import numpy as np
import pytest

from tools.gremlin_cross_modal_relational_evidence_v01 import EvidenceProvenance
from tools.gremlin_source_family_channel_design_v01 import (
    CandidateMeasurementChannel,
    SourceFamilyChannelDesignError,
    channel_design_payload,
    evaluate_candidate_channel,
    evaluate_candidate_channel_set,
    greedy_channel_plan,
    verify_channel_design_payload,
)
from tools.gremlin_source_family_signature_identifiability_v01 import (
    SourceFamilySignature,
)


PROV = EvidenceProvenance(
    repository="AdrianLipa90/GREMLIN",
    branch="integrate/source-family-channel-design-v0.1",
    commit="a" * 40,
    schema="GREMLIN_SOURCE_FAMILY_CHANNEL_DESIGN_TEST_V0_1",
    receipt="pytest:channel-design",
)


def _sig(name, values):
    return SourceFamilySignature(
        name=name,
        values=tuple(values),
        provenance=PROV,
        normalization="unit candidate amplitude",
    )


def _channel(name, response, sigma=1.0, *, independent=True):
    return CandidateMeasurementChannel(
        name=name,
        source_response=tuple(response),
        sigma=sigma,
        provenance=PROV,
        normalization="unit candidate amplitude response",
        independent_of_existing=independent,
        feasibility_note="NOT_ASSESSED",
    )


def test_single_channel_rank_lift_matches_nullspace_projection():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
    ]
    lifting = _channel("difference_probe", [1.0, -1.0])
    blind = _channel("sum_probe", [2.0, 2.0])

    lift_eval = evaluate_candidate_channel(
        signatures,
        [[1.0]],
        lifting,
    )
    blind_eval = evaluate_candidate_channel(
        signatures,
        [[1.0]],
        blind,
    )

    assert lift_eval.current_rank == 1
    assert lift_eval.augmented_rank == 2
    assert lift_eval.rank_gain == 1
    assert lift_eval.nullspace_projection_norm > 0.0
    assert lift_eval.classification == "RANK_LIFTING"

    assert blind_eval.current_rank == 1
    assert blind_eval.augmented_rank == 1
    assert blind_eval.rank_gain == 0
    assert blind_eval.nullspace_projection_norm == pytest.approx(0.0, abs=1e-12)
    assert blind_eval.classification == "NULLSPACE_BLIND"


def test_two_channels_cover_two_dimensional_nullspace():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
        _sig("source_c", [1.0]),
    ]
    channels = [
        _channel("ab_difference", [1.0, -1.0, 0.0]),
        _channel("ac_difference", [1.0, 0.0, -1.0]),
    ]

    report = evaluate_candidate_channel_set(
        signatures,
        [[1.0]],
        channels,
    )

    assert report.current_rank == 1
    assert report.current_nullity == 2
    assert report.rank_gain == 2
    assert report.nullspace_coverage_rank == 2
    assert report.augmented_rank == 3
    assert report.full_nullspace_covered


def test_one_scalar_channel_cannot_remove_two_dimensional_nullspace():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
        _sig("source_c", [1.0]),
    ]
    report = evaluate_candidate_channel_set(
        signatures,
        [[1.0]],
        [_channel("one_probe", [1.0, -1.0, 0.0])],
    )
    assert report.current_nullity == 2
    assert report.rank_gain == 1
    assert not report.full_nullspace_covered


def test_conditioning_channel_improves_nearly_collinear_full_rank_design():
    epsilon = 1e-6
    signatures = [
        _sig("source_a", [1.0, 0.0]),
        _sig("source_b", [1.0, epsilon]),
    ]
    candidate = _channel("orthogonal_probe", [0.0, 1.0])

    evaluation = evaluate_candidate_channel(
        signatures,
        np.eye(2),
        candidate,
        rank_rtol=1e-14,
        max_condition_number=1e8,
    )

    assert evaluation.current_rank == 2
    assert evaluation.augmented_rank == 2
    assert evaluation.rank_gain == 0
    assert evaluation.condition_after < evaluation.condition_before
    assert evaluation.smallest_singular_after > evaluation.smallest_singular_before
    assert evaluation.classification == "CONDITION_IMPROVING"


def test_greedy_plan_selects_rank_lifting_channel_before_nullspace_blind_channel():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
    ]
    plan = greedy_channel_plan(
        signatures,
        [[1.0]],
        [
            _channel("z_blind", [1.0, 1.0]),
            _channel("a_lifting", [1.0, -1.0]),
        ],
        max_channels=1,
    )

    assert plan.selected_channels == ("a_lifting",)
    assert plan.initial_rank == 1
    assert plan.final_rank == 2
    assert plan.full_rank_reached
    assert plan.conditioning_gate_passed
    assert plan.route == "PROPOSE_RANK_LIFTING_MEASUREMENT"
    assert plan.physical_source_selected is False
    assert plan.experimental_feasibility_asserted is False


def test_greedy_plan_reports_no_available_rank_breaker():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
    ]
    plan = greedy_channel_plan(
        signatures,
        [[1.0]],
        [
            _channel("blind_1", [1.0, 1.0]),
            _channel("blind_2", [2.0, 2.0]),
        ],
    )

    assert plan.selected_channels == ()
    assert plan.final_rank == plan.initial_rank == 1
    assert plan.route == "NO_AVAILABLE_CHANNEL_BREAKS_DEGENERACY"


def test_channel_design_payload_binds_parent_geometry_and_detects_tampering():
    signatures = [
        _sig("source_a", [1.0]),
        _sig("source_b", [1.0]),
    ]
    channels = [
        _channel("difference_probe", [1.0, -1.0]),
    ]

    payload = channel_design_payload(
        signatures,
        [[2.0]],
        channels,
    )

    assert payload["physical_source_selected"] is False
    assert payload["experimental_feasibility_asserted"] is False
    assert payload["parent_input"]["covariance"] == [[2.0]]
    assert payload["parent_input"]["signatures"][0]["values"] == [1.0]
    assert payload["greedy_plan"]["selected_channels"] == ("difference_probe",)
    verify_channel_design_payload(payload)

    payload["parent_input"]["covariance"][0][0] = 99.0
    with pytest.raises(
        SourceFamilyChannelDesignError,
        match="packet_sha256 mismatch",
    ):
        verify_channel_design_payload(payload)


def test_payload_hash_detects_candidate_channel_tampering():
    payload = channel_design_payload(
        [
            _sig("source_a", [1.0]),
            _sig("source_b", [1.0]),
        ],
        [[1.0]],
        [_channel("difference_probe", [1.0, -1.0])],
    )
    payload["candidate_channels"][0]["source_response"][0] = 123.0
    with pytest.raises(
        SourceFamilyChannelDesignError,
        match="packet_sha256 mismatch",
    ):
        verify_channel_design_payload(payload)


@pytest.mark.parametrize(
    "call",
    [
        lambda: evaluate_candidate_channel(
            [_sig("a", [1.0]), _sig("b", [1.0])],
            [[1.0]],
            _channel("bad_length", [1.0]),
        ),
        lambda: evaluate_candidate_channel(
            [_sig("a", [1.0]), _sig("b", [1.0])],
            [[1.0]],
            _channel("zero_sigma", [1.0, -1.0], sigma=0.0),
        ),
        lambda: evaluate_candidate_channel(
            [_sig("a", [1.0]), _sig("b", [1.0])],
            [[1.0]],
            _channel(
                "correlated",
                [1.0, -1.0],
                independent=False,
            ),
        ),
        lambda: evaluate_candidate_channel_set(
            [_sig("a", [1.0]), _sig("b", [1.0])],
            [[1.0]],
            [],
        ),
        lambda: greedy_channel_plan(
            [_sig("a", [1.0]), _sig("b", [1.0])],
            [[1.0]],
            [
                _channel("same", [1.0, -1.0]),
                _channel("same", [-1.0, 1.0]),
            ],
        ),
    ],
)
def test_fail_closed_domains(call):
    with pytest.raises(SourceFamilyChannelDesignError):
        call()
