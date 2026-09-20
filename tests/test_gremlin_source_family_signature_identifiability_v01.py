import hashlib
import json

import numpy as np
import pytest

from tools.gremlin_cross_modal_relational_evidence_v01 import EvidenceProvenance
from tools.gremlin_source_family_signature_identifiability_v01 import (
    SourceFamilyIdentifiabilityError,
    SourceFamilySignature,
    analyze_source_family_signatures,
    signature_geometry,
    source_family_payload,
    verify_source_family_payload,
    weighted_gram_matrix,
)


PROV = EvidenceProvenance(
    repository="AdrianLipa90/GREMLIN",
    branch="integrate/relational-phase-observation-v0.1",
    commit="a" * 40,
    schema="GREMLIN_SOURCE_SIGNATURE_TEST_V0_1",
    receipt="pytest:source-family-signature",
)


def _sig(name, values, normalization="unit candidate amplitude"):
    return SourceFamilySignature(
        name=name,
        values=tuple(values),
        provenance=PROV,
        normalization=normalization,
    )


def test_full_rank_geometry_recovers_candidate_amplitudes_and_heldout():
    signatures = [
        _sig("information", [1.0, 0.0, 1.0]),
        _sig("holonomy", [0.0, 1.0, 1.0]),
    ]
    true_a = np.array([2.0, -1.0])
    s = np.column_stack([sig.values for sig in signatures])
    residual = s @ true_a

    heldout_signatures = [
        _sig("information", [2.0, 0.0]),
        _sig("holonomy", [0.0, 3.0]),
    ]
    sh = np.column_stack([sig.values for sig in heldout_signatures])
    heldout_residual = sh @ true_a

    report = analyze_source_family_signatures(
        signatures,
        residual,
        np.eye(3),
        heldout_signatures=heldout_signatures,
        heldout_residual=heldout_residual,
        heldout_covariance=np.eye(2),
        heldout_independent=True,
        cross_modal_source_routing_admissible=True,
    )

    assert report.geometry.state == "IDENTIFIABLE"
    assert report.geometry.rank == 2
    assert report.geometry.nullity == 0
    assert report.amplitudes == pytest.approx(tuple(true_a))
    assert report.fit_chi_square == pytest.approx(0.0, abs=1e-12)
    assert report.heldout_chi_square == pytest.approx(0.0, abs=1e-12)
    assert report.heldout_delta_chi_square > 0.0
    assert report.route == "ALLOW_CANDIDATE_SOURCE_FAMILY_TESTS"
    assert report.physical_source_selected is False


def test_pairwise_collinear_signatures_are_underdetermined():
    signatures = [
        _sig("source_a", [1.0, 2.0, 3.0]),
        _sig("source_b", [-2.0, -4.0, -6.0]),
    ]
    geometry, _, _, _ = signature_geometry(
        signatures,
        np.eye(3),
    )
    assert geometry.state == "UNDERDETERMINED"
    assert geometry.rank == 1
    assert geometry.nullity == 1
    assert geometry.pairwise_degeneracy_classes == (("source_a", "source_b"),)
    assert len(geometry.nullspace_basis) == 1

    report = analyze_source_family_signatures(
        signatures,
        [1.0, 2.0, 3.0],
        np.eye(3),
        cross_modal_source_routing_admissible=True,
    )
    assert report.amplitudes is None
    assert report.route == "REQUEST_MORE_INDEPENDENT_CHANNELS"


def test_higher_order_degeneracy_is_detected_without_pairwise_collinearity():
    signatures = [
        _sig("source_a", [1.0, 0.0, 0.0]),
        _sig("source_b", [0.0, 1.0, 0.0]),
        _sig("source_c", [1.0, 1.0, 0.0]),
    ]
    geometry, _, _, _ = signature_geometry(
        signatures,
        np.eye(3),
    )
    assert geometry.state == "UNDERDETERMINED"
    assert geometry.rank == 2
    assert geometry.nullity == 1
    assert geometry.pairwise_degeneracy_classes == ()
    relation = np.asarray(geometry.nullspace_basis[0])
    s = np.column_stack([sig.values for sig in signatures])
    assert s @ relation == pytest.approx(np.zeros(3), abs=1e-12)


def test_full_rank_but_nearly_collinear_signatures_are_ill_conditioned():
    epsilon = 1e-10
    signatures = [
        _sig("source_a", [1.0, 0.0]),
        _sig("source_b", [1.0, epsilon]),
    ]
    geometry, _, _, _ = signature_geometry(
        signatures,
        np.eye(2),
        max_condition_number=1e8,
        rank_rtol=1e-14,
    )
    assert geometry.rank == 2
    assert geometry.state == "ILL_CONDITIONED"
    assert geometry.condition_number > geometry.max_condition_number

    report = analyze_source_family_signatures(
        signatures,
        [1.0, 1.0],
        np.eye(2),
        max_condition_number=1e8,
        rank_rtol=1e-14,
    )
    assert report.amplitudes is None
    assert report.route == "REQUEST_BETTER_CONDITIONING"


def test_weighted_gram_matches_direct_definition():
    signatures = [
        _sig("source_a", [1.0, 2.0]),
        _sig("source_b", [3.0, -1.0]),
    ]
    covariance = np.array([[2.0, 0.3], [0.3, 1.5]])
    s = np.column_stack([sig.values for sig in signatures])
    expected = s.T @ np.linalg.inv(covariance) @ s
    assert weighted_gram_matrix(signatures, covariance) == pytest.approx(expected)


def test_identifiable_without_holdout_requests_heldout_if_cross_modal_open():
    signatures = [
        _sig("source_a", [1.0, 0.0]),
        _sig("source_b", [0.0, 1.0]),
    ]
    report = analyze_source_family_signatures(
        signatures,
        [1.0, 2.0],
        np.eye(2),
        cross_modal_source_routing_admissible=True,
    )
    assert report.geometry.state == "IDENTIFIABLE"
    assert report.amplitudes == pytest.approx((1.0, 2.0))
    assert report.route == "REQUEST_HELD_OUT_VALIDATION"


def test_cross_modal_block_prevents_source_family_route_even_with_good_holdout():
    signatures = [
        _sig("source_a", [1.0, 0.0]),
        _sig("source_b", [0.0, 1.0]),
    ]
    heldout = [
        _sig("source_a", [2.0, 0.0]),
        _sig("source_b", [0.0, 2.0]),
    ]
    report = analyze_source_family_signatures(
        signatures,
        [1.0, 2.0],
        np.eye(2),
        heldout_signatures=heldout,
        heldout_residual=[2.0, 4.0],
        heldout_covariance=np.eye(2),
        heldout_independent=True,
        cross_modal_source_routing_admissible=False,
    )
    assert report.heldout_delta_chi_square > 0.0
    assert report.route == "NO_SOURCE_ROUTE"


def test_frozen_model_worse_than_holdout_null_stops_declared_source_family_model():
    signatures = [
        _sig("source_a", [1.0]),
    ]
    heldout = [
        _sig("source_a", [1.0]),
    ]
    report = analyze_source_family_signatures(
        signatures,
        [10.0],
        [[1.0]],
        heldout_signatures=heldout,
        heldout_residual=[0.1],
        heldout_covariance=[[1.0]],
        heldout_independent=True,
        cross_modal_source_routing_admissible=True,
    )
    assert report.amplitudes == pytest.approx((10.0,))
    assert report.heldout_delta_chi_square < 0.0
    assert report.route == "STOP_DECLARED_SOURCE_FAMILY_MODEL"


def test_non_independent_holdout_does_not_open_route():
    signatures = [_sig("source_a", [1.0])]
    heldout = [_sig("source_a", [2.0])]
    report = analyze_source_family_signatures(
        signatures,
        [1.0],
        [[1.0]],
        heldout_signatures=heldout,
        heldout_residual=[2.0],
        heldout_covariance=[[1.0]],
        heldout_independent=False,
        cross_modal_source_routing_admissible=True,
    )
    assert report.route == "REQUEST_HELD_OUT_VALIDATION"


def test_payload_hash_is_verifiable_and_tamper_detected():
    signatures = [
        _sig("source_a", [1.0, 0.0]),
        _sig("source_b", [0.0, 1.0]),
    ]
    payload = source_family_payload(
        signatures,
        [1.0, 2.0],
        np.eye(2),
    )
    assert payload["physical_source_selected"] is False
    assert len(payload["packet_sha256"]) == 64
    verify_source_family_payload(payload)

    payload["fit"]["amplitudes"][0] = 99.0
    with pytest.raises(
        SourceFamilyIdentifiabilityError,
        match="packet_sha256 mismatch",
    ):
        verify_source_family_payload(payload)


def test_zero_signature_is_reported_as_underdetermined():
    signatures = [
        _sig("zero_source", [0.0, 0.0]),
        _sig("source_b", [0.0, 1.0]),
    ]
    geometry, _, _, _ = signature_geometry(signatures, np.eye(2))
    assert geometry.state == "UNDERDETERMINED"
    assert geometry.zero_signature_names == ("zero_source",)


@pytest.mark.parametrize(
    "call",
    [
        lambda: signature_geometry([], np.eye(1)),
        lambda: signature_geometry(
            [
                _sig("same", [1.0]),
                _sig("same", [2.0]),
            ],
            np.eye(1),
        ),
        lambda: signature_geometry(
            [_sig("source_a", [1.0, 2.0])],
            [[1.0, 2.0], [2.0, 1.0]],
        ),
        lambda: analyze_source_family_signatures(
            [_sig("source_a", [1.0, 0.0])],
            [1.0],
            np.eye(2),
        ),
        lambda: analyze_source_family_signatures(
            [_sig("source_a", [1.0])],
            [1.0],
            [[1.0]],
            heldout_signatures=[_sig("wrong_name", [1.0])],
            heldout_residual=[1.0],
            heldout_covariance=[[1.0]],
            heldout_independent=True,
        ),
        lambda: SourceFamilySignature(
            name="source_a",
            values=(1.0,),
            provenance=PROV,
            normalization="",
        ).validate(),
    ],
)
def test_fail_closed_domains(call):
    with pytest.raises(SourceFamilyIdentifiabilityError):
        call()
