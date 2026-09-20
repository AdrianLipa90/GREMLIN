import hashlib
import json

import numpy as np
import pytest

from tools.gremlin_cross_modal_relational_evidence_v01 import EvidenceProvenance
from tools.gremlin_identifiability_measurement_design_v01 import (
    IndependentMeasurement,
    MeasurementDesignError,
    MeasurementSignature,
    correlated_measurement_block_update,
    independent_measurement_update,
    measurement_design_payload,
    rank_independent_measurements,
    verify_measurement_design_payload,
)
from tools.gremlin_source_family_signature_identifiability_v01 import (
    SourceFamilySignature,
)


PROV = EvidenceProvenance(
    repository="AdrianLipa90/GREMLIN",
    branch="integrate/relational-phase-observation-v0.1",
    commit="a" * 40,
    schema="GREMLIN_MEASUREMENT_DESIGN_TEST_V0_1",
    receipt="pytest:measurement-design",
)


def _source(name, values):
    return SourceFamilySignature(
        name=name,
        values=tuple(values),
        provenance=PROV,
        normalization="unit candidate amplitude",
    )


def _measurement(name, source_signature, variance=1.0):
    return IndependentMeasurement(
        signature=MeasurementSignature(
            name=name,
            source_signature=tuple(source_signature),
            provenance=PROV,
        ),
        variance=variance,
    )


def test_independent_channel_that_probes_nullspace_increases_rank():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
    ]
    candidate = _measurement("channel_b", [0.0, 1.0])

    report = independent_measurement_update(
        signatures,
        [[1.0]],
        candidate,
    )

    assert report.state_before == "UNDERDETERMINED"
    assert report.rank_before == 1
    assert report.rank_after == 2
    assert report.rank_gain == 1
    assert report.nullity_before == 1
    assert report.nullity_after == 0
    assert report.nullspace_power == pytest.approx(1.0)
    assert report.state_after == "IDENTIFIABLE"


def test_independent_redundant_channel_does_not_reduce_nullity():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
    ]
    candidate = _measurement("duplicate_a", [2.0, 0.0], variance=4.0)

    report = independent_measurement_update(
        signatures,
        [[1.0]],
        candidate,
    )

    assert report.rank_gain == 0
    assert report.rank_after == 1
    assert report.nullity_after == 1
    assert report.nullspace_power == pytest.approx(0.0)
    assert report.state_after == "UNDERDETERMINED"


def test_scalar_channel_increases_rank_by_at_most_one():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
        _source("source_c", [0.0]),
    ]
    candidate = _measurement("mixed_new", [0.0, 1.0, 1.0])

    report = independent_measurement_update(
        signatures,
        [[1.0]],
        candidate,
    )

    assert report.rank_before == 1
    assert report.rank_after == 2
    assert report.rank_gain == 1
    assert report.nullity_after == 1


def test_d_optimal_gain_matches_matrix_determinant_lemma():
    signatures = [
        _source("source_a", [1.0, 0.0]),
        _source("source_b", [0.0, 2.0]),
    ]
    candidate = _measurement("new", [1.0, 1.0], variance=2.0)

    report = independent_measurement_update(
        signatures,
        np.eye(2),
        candidate,
    )

    s = np.array([[1.0, 0.0], [0.0, 2.0]])
    g = s.T @ s
    w = np.array([1.0, 1.0]) / np.sqrt(2.0)
    expected = np.log1p(w @ np.linalg.inv(g) @ w)

    assert report.state_before == "IDENTIFIABLE"
    assert report.d_optimal_gain == pytest.approx(expected)
    assert report.e_optimal_gain >= 0.0


def test_e_optimal_policy_prefers_channel_that_strengthens_weak_direction():
    signatures = [
        _source("strong", [10.0, 0.0]),
        _source("weak", [0.0, 1.0]),
    ]
    candidates = [
        _measurement("measure_strong_again", [1.0, 0.0]),
        _measurement("measure_weak", [0.0, 1.0]),
    ]

    ranked = rank_independent_measurements(
        signatures,
        np.eye(2),
        candidates,
        policy="E_OPTIMAL",
    )

    assert ranked[0][0] == "measure_weak"
    assert ranked[0][1].e_optimal_gain > ranked[1][1].e_optimal_gain


def test_rank_then_nullspace_policy_prefers_rank_restoring_channel():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
    ]
    candidates = [
        _measurement("redundant", [1.0, 0.0]),
        _measurement("rank_restoring", [0.0, 1.0]),
    ]

    ranked = rank_independent_measurements(
        signatures,
        [[1.0]],
        candidates,
        policy="RANK_THEN_NULLSPACE",
    )

    assert ranked[0][0] == "rank_restoring"
    assert ranked[0][1].rank_gain == 1
    assert ranked[1][1].rank_gain == 0


def test_correlated_restatement_adds_zero_conditional_information():
    signatures = [
        _source("source_a", [1.0, 0.0]),
        _source("source_b", [0.0, 1.0]),
    ]
    candidate = [
        MeasurementSignature(
            name="correlated_copy",
            source_signature=(0.8, 0.0),
            provenance=PROV,
        )
    ]
    covariance = np.eye(2)
    candidate_covariance = np.array([[1.0]])
    cross_covariance = np.array([[0.8], [0.0]])

    report = correlated_measurement_block_update(
        signatures,
        covariance,
        candidate,
        candidate_covariance,
        cross_covariance,
    )

    assert np.asarray(report.delta_gram) == pytest.approx(np.zeros((2, 2)))
    assert report.rank_gain == 0
    assert report.e_optimal_gain == pytest.approx(0.0)
    assert report.d_optimal_gain == pytest.approx(0.0)


def test_independent_correlated_block_matches_direct_fisher_update():
    signatures = [
        _source("source_a", [1.0, 0.0]),
        _source("source_b", [0.0, 1.0]),
    ]
    block = [
        MeasurementSignature(
            name="m1",
            source_signature=(1.0, 1.0),
            provenance=PROV,
        ),
        MeasurementSignature(
            name="m2",
            source_signature=(2.0, -1.0),
            provenance=PROV,
        ),
    ]
    omega = np.array([[2.0, 0.3], [0.3, 1.5]])
    cross = np.zeros((2, 2))

    report = correlated_measurement_block_update(
        signatures,
        np.eye(2),
        block,
        omega,
        cross,
    )

    q = np.array([[1.0, 1.0], [2.0, -1.0]])
    expected = q.T @ np.linalg.inv(omega) @ q

    assert np.asarray(report.delta_gram) == pytest.approx(expected)


def test_correlated_block_can_increase_rank_by_block_dimension():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
        _source("source_c", [0.0]),
    ]
    block = [
        MeasurementSignature(
            name="m_b",
            source_signature=(0.0, 1.0, 0.0),
            provenance=PROV,
        ),
        MeasurementSignature(
            name="m_c",
            source_signature=(0.0, 0.0, 1.0),
            provenance=PROV,
        ),
    ]

    report = correlated_measurement_block_update(
        signatures,
        [[1.0]],
        block,
        np.eye(2),
        np.zeros((1, 2)),
    )

    assert report.rank_before == 1
    assert report.rank_after == 3
    assert report.rank_gain == 2
    assert report.state_after == "IDENTIFIABLE"


def test_measurement_design_payload_hash_and_declared_policy():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
    ]
    candidates = [
        _measurement("redundant", [1.0, 0.0]),
        _measurement("rank_restoring", [0.0, 1.0]),
    ]

    payload = measurement_design_payload(
        signatures,
        [[1.0]],
        candidates,
        policy="RANK_THEN_NULLSPACE",
    )

    assert payload["selected_candidate"] == "rank_restoring"
    assert payload["physical_source_selected"] is False
    assert payload["selection_is_physical_experiment_verdict"] is False
    verify_measurement_design_payload(payload)

    payload["candidates"][0]["variance"] = 99.0
    with pytest.raises(MeasurementDesignError, match="packet_sha256 mismatch"):
        verify_measurement_design_payload(payload)


def test_rank_deficient_geometry_rejects_e_optimal_policy():
    signatures = [
        _source("source_a", [1.0]),
        _source("source_b", [0.0]),
    ]
    with pytest.raises(MeasurementDesignError, match="RANK_THEN_NULLSPACE"):
        rank_independent_measurements(
            signatures,
            [[1.0]],
            [_measurement("new", [0.0, 1.0])],
            policy="E_OPTIMAL",
        )


def test_full_rank_geometry_rejects_rank_only_policy():
    signatures = [
        _source("source_a", [1.0, 0.0]),
        _source("source_b", [0.0, 1.0]),
    ]
    with pytest.raises(MeasurementDesignError, match="E_OPTIMAL or D_OPTIMAL"):
        rank_independent_measurements(
            signatures,
            np.eye(2),
            [_measurement("new", [1.0, 1.0])],
            policy="RANK_THEN_NULLSPACE",
        )


@pytest.mark.parametrize(
    "call",
    [
        lambda: independent_measurement_update(
            [_source("source_a", [1.0])],
            [[1.0]],
            _measurement("bad_variance", [1.0], variance=0.0),
        ),
        lambda: correlated_measurement_block_update(
            [_source("source_a", [1.0])],
            [[1.0]],
            [
                MeasurementSignature(
                    name="m1",
                    source_signature=(1.0,),
                    provenance=PROV,
                )
            ],
            [[1.0]],
            [[2.0]],
        ),
        lambda: correlated_measurement_block_update(
            [_source("source_a", [1.0])],
            [[1.0]],
            [
                MeasurementSignature(
                    name="same",
                    source_signature=(1.0,),
                    provenance=PROV,
                ),
                MeasurementSignature(
                    name="same",
                    source_signature=(1.0,),
                    provenance=PROV,
                ),
            ],
            np.eye(2),
            np.zeros((1, 2)),
        ),
        lambda: rank_independent_measurements(
            [_source("source_a", [1.0])],
            [[1.0]],
            [_measurement("m1", [1.0])],
            policy="NOT_A_POLICY",
        ),
        lambda: MeasurementSignature(
            name="m",
            source_signature=(1.0, 2.0),
            provenance=PROV,
        ).validate(1),
    ],
)
def test_fail_closed_domains(call):
    with pytest.raises(MeasurementDesignError):
        call()
