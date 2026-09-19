import numpy as np
import pytest

from tools.gremlin_cross_modal_relational_evidence_v01 import (
    CrossModalEvidenceError,
    EvidenceProvenance,
    PhaseIdentifiability,
    ResidualChannel,
    build_cross_modal_report,
    covariance_chi_square,
    packet_payload,
)


PROV = EvidenceProvenance(
    repository="AdrianLipa90/Orbital-Eclipse-Spectroscopy",
    branch="integrate/relational-phase-observation-v0.1",
    commit="a" * 40,
    schema="OES_H1_HOLONOMY_RESPONSE_IDENTIFIABILITY_V0_1",
    receipt="github-actions:reference",
)


def _channel(
    name="orbital",
    observed=1.0,
    predicted=0.0,
    sigma=1.0,
    *,
    independently_constrained=True,
    circular_fit=False,
):
    return ResidualChannel(
        name=name,
        observed=observed,
        predicted=predicted,
        sigma=sigma,
        provenance=PROV,
        independently_constrained=independently_constrained,
        circular_fit=circular_fit,
    )


def _phase(
    *,
    phase_count=2,
    cycle_rank=2,
    jacobian_rank=2,
    fisher_rank=2,
):
    return PhaseIdentifiability(
        phase_count=phase_count,
        cycle_rank=cycle_rank,
        jacobian_rank=jacobian_rank,
        fisher_rank=fisher_rank,
    )


def test_consistent_packet_without_source_binding_stays_non_attributable():
    report = build_cross_modal_report(
        [_channel(observed=1.5, sigma=1.0)],
        phase_identifiability=_phase(),
        required_source_bindings_admitted=False,
    )
    assert report.consistency_state == "CONSISTENT"
    assert report.residual_resolved
    assert not report.source_attribution_admissible


def test_consistent_resolved_packet_can_open_candidate_source_routing_only_with_bindings():
    report = build_cross_modal_report(
        [_channel(observed=1.5, sigma=1.0)],
        phase_identifiability=_phase(),
        required_source_bindings_admitted=True,
    )
    assert report.consistency_state == "CONSISTENT"
    assert report.source_attribution_admissible


def test_rank_deficiency_forces_underdetermined():
    report = build_cross_modal_report(
        [_channel(observed=0.1, sigma=1.0)],
        phase_identifiability=_phase(jacobian_rank=1, fisher_rank=1),
        required_source_bindings_admitted=True,
    )
    assert report.consistency_state == "UNDERDETERMINED"
    assert not report.phase_fully_identifiable
    assert not report.source_attribution_admissible


def test_unconstrained_known_sector_forces_underdetermined():
    report = build_cross_modal_report(
        [_channel(independently_constrained=False)],
        phase_identifiability=_phase(),
        required_source_bindings_admitted=True,
    )
    assert report.consistency_state == "UNDERDETERMINED"
    assert not report.known_sectors_independently_constrained
    assert not report.source_attribution_admissible


def test_circular_fit_forces_underdetermined():
    report = build_cross_modal_report(
        [_channel(circular_fit=True)],
        phase_identifiability=_phase(),
        required_source_bindings_admitted=True,
    )
    assert report.consistency_state == "UNDERDETERMINED"
    assert report.circular_fit_present
    assert not report.source_attribution_admissible


def test_large_normalized_residual_is_inconsistent():
    report = build_cross_modal_report(
        [_channel(observed=4.0, predicted=0.0, sigma=1.0)],
        phase_identifiability=_phase(),
        per_channel_sigma_threshold=3.0,
        required_source_bindings_admitted=True,
    )
    assert report.consistency_state == "INCONSISTENT"
    assert not report.source_attribution_admissible


def test_covariance_chi_square_matches_direct_linear_algebra():
    residual = np.array([1.0, -0.5])
    covariance = np.array([[2.0, 0.3], [0.3, 1.0]])
    expected = float(residual @ np.linalg.inv(covariance) @ residual)
    assert covariance_chi_square(residual, covariance) == pytest.approx(expected)


def test_packet_hash_is_deterministic_and_no_physical_source_is_selected():
    kwargs = dict(
        channels=[
            _channel(name="orbital", observed=1.2, sigma=1.0),
            _channel(name="spectral", observed=0.4, sigma=0.5),
        ],
        phase_identifiability=_phase(),
        required_source_bindings_admitted=True,
    )
    p1 = packet_payload(**kwargs)
    p2 = packet_payload(**kwargs)
    assert p1["packet_sha256"] == p2["packet_sha256"]
    assert len(p1["packet_sha256"]) == 64
    assert p1["physical_source_selected"] is False


def test_zero_cycle_rank_does_not_require_phase_response_rank():
    phase = _phase(
        phase_count=1,
        cycle_rank=0,
        jacobian_rank=0,
        fisher_rank=0,
    )
    report = build_cross_modal_report(
        [_channel(observed=0.1, sigma=1.0)],
        phase_identifiability=phase,
    )
    assert report.phase_fully_identifiable
    assert report.consistency_state == "CONSISTENT"


@pytest.mark.parametrize(
    "call",
    [
        lambda: build_cross_modal_report([], phase_identifiability=_phase()),
        lambda: build_cross_modal_report(
            [_channel(sigma=0.0)],
            phase_identifiability=_phase(),
        ),
        lambda: build_cross_modal_report(
            [_channel()],
            phase_identifiability=_phase(cycle_rank=3),
        ),
        lambda: covariance_chi_square([1.0, 2.0], [[1.0, 2.0], [2.0, 1.0]]),
        lambda: EvidenceProvenance(
            repository="x",
            branch="y",
            commit="bad",
            schema="s",
            receipt="r",
        ).validate(),
    ],
)
def test_fail_closed_domains(call):
    with pytest.raises(CrossModalEvidenceError):
        call()
