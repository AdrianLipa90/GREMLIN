from __future__ import annotations

import math

import pytest

from tools.gremlin_orbit_source_coupling_identifiability_v08 import (
    FAIL_UNSOURCED_FACTORIZATION,
    PASS_EXACT_IDENTIFIABILITY,
    OrbitSourceIdentifiabilityError,
    candidate_mu_from_extensive_source,
    conversion_required_for_mu,
    extensive_source_energy,
    infer_eta_given_mu,
    infer_mu_given_eta,
    orbit_strength,
    rescale_factorization,
    resolve_factorization,
    role_kernel_omega,
)


def test_k_orb_round_trip_from_role_kernel() -> None:
    mu = 7.5
    q = 3.0
    m = 2.0
    r = 4.0
    omega = role_kernel_omega(mu, q, m, r)
    expected = mu * (q / m)
    assert orbit_strength(omega, r) == pytest.approx(expected, rel=1e-14, abs=1e-14)


def test_positive_rescaling_preserves_observable_product() -> None:
    mu = 12.0
    eta = 0.25
    k = mu * eta
    for lam in (0.125, 0.5, 1.0, 2.0, 16.0):
        witness = rescale_factorization(mu, eta, lam)
        assert witness.product == pytest.approx(k, rel=1e-15, abs=1e-15)
        assert witness.orbit_strength == pytest.approx(k, rel=1e-15, abs=1e-15)


def test_independent_mu_reconstructs_eta_uniquely() -> None:
    k = 9.0
    mu = 3.0
    assert infer_eta_given_mu(k, mu) == pytest.approx(3.0)

    omega = math.sqrt(k / 8.0)
    result = resolve_factorization(
        omega,
        2.0,
        mu_source=mu,
        mu_source_profile_id="RFC_SOURCE_TEST",
    )
    assert result.admitted is True
    assert result.status == PASS_EXACT_IDENTIFIABILITY
    assert result.eta_g == pytest.approx(3.0)
    assert result.eta_g_profile_id == "RECONSTRUCTED_FROM_ORBIT_AND_SOURCE"


def test_independent_eta_reconstructs_mu_uniquely() -> None:
    k = 10.0
    eta = 2.5
    assert infer_mu_given_eta(k, eta) == pytest.approx(4.0)

    omega = math.sqrt(k)
    result = resolve_factorization(
        omega,
        1.0,
        eta=eta,
        eta_g_profile_id="COUPLING_TEST",
    )
    assert result.admitted is True
    assert result.status == PASS_EXACT_IDENTIFIABILITY
    assert result.mu_source == pytest.approx(4.0)
    assert result.mu_source_profile_id == "RECONSTRUCTED_FROM_ORBIT_AND_ETA"


def test_unsourced_factorization_fails_closed_without_eta_default() -> None:
    result = resolve_factorization(2.0, 3.0)
    assert result.admitted is False
    assert result.status == FAIL_UNSOURCED_FACTORIZATION
    assert result.mu_source is None
    assert result.eta_g is None


def test_explicit_unit_eta_is_allowed_only_with_profile_id() -> None:
    with pytest.raises(OrbitSourceIdentifiabilityError):
        resolve_factorization(2.0, 1.0, eta=1.0)

    result = resolve_factorization(
        2.0,
        1.0,
        eta=1.0,
        eta_g_profile_id="EXPLICIT_UNIT_ETA_TEST",
    )
    assert result.mu_source == pytest.approx(4.0)


def test_double_supplied_factorization_must_match_orbit() -> None:
    result = resolve_factorization(
        2.0,
        1.0,
        mu_source=8.0,
        eta=0.5,
        mu_source_profile_id="SOURCE_TEST",
        eta_g_profile_id="ETA_TEST",
    )
    assert result.admitted is True
    assert result.residual == pytest.approx(0.0)

    with pytest.raises(OrbitSourceIdentifiabilityError):
        resolve_factorization(
            2.0,
            1.0,
            mu_source=8.0,
            eta=1.0,
            mu_source_profile_id="SOURCE_TEST",
            eta_g_profile_id="ETA_TEST",
        )


def test_rfc_extensive_source_adapter_keeps_conversion_explicit() -> None:
    extensive = extensive_source_energy([2.0, 3.0], [5.0, 7.0])
    assert extensive == pytest.approx(31.0)

    mu = candidate_mu_from_extensive_source(extensive, 0.25)
    assert mu == pytest.approx(7.75)
    assert conversion_required_for_mu(extensive, mu) == pytest.approx(0.25)


def test_invalid_domain_rejected() -> None:
    with pytest.raises(OrbitSourceIdentifiabilityError):
        orbit_strength(0.0, 1.0)
    with pytest.raises(OrbitSourceIdentifiabilityError):
        orbit_strength(1.0, -1.0)
    with pytest.raises(OrbitSourceIdentifiabilityError):
        rescale_factorization(1.0, 1.0, 0.0)
    with pytest.raises(OrbitSourceIdentifiabilityError):
        extensive_source_energy([], [])
