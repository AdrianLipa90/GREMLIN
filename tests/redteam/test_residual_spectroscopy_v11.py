import numpy as np

from gremlin_mcp.residual_spectroscopy_v10 import analyze_residual_stack_v10
from gremlin_mcp.residual_spectroscopy_v11 import analyze_residual_stack_v11


def _ar1(seed, runs=16, n=128, phi=0.8):
    rng = np.random.default_rng(seed)
    eps = rng.normal(size=(runs, n))
    out = np.zeros_like(eps)
    for j in range(n):
        out[:, j] = eps[:, j] if j == 0 else phi * out[:, j - 1] + eps[:, j]
    return out


def _one_over_f(seed, runs=16, n=256):
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n)
    amp = np.ones_like(f)
    amp[0] = 0.0
    amp[1:] = 1.0 / np.sqrt(f[1:])
    rows = []
    for _ in range(runs):
        z = amp * np.exp(1j * rng.uniform(0, 2 * np.pi, len(f)))
        x = np.fft.irfft(z, n=n)
        x = (x - x.mean()) / x.std()
        rows.append(x)
    return np.asarray(rows)


def _shared(kind, seed=4242, runs=16, n=256, rho=0.2):
    rng = np.random.default_rng(seed)
    if kind == "white":
        common = rng.normal(size=n)
        indep = rng.normal(size=(runs, n))
    elif kind == "ar1":
        common = _ar1(seed + 1, 1, n)[0]
        indep = _ar1(seed + 2, runs, n)
    else:
        raise ValueError(kind)
    return np.sqrt(rho) * common[None, :] + np.sqrt(1.0 - rho) * indep


def test_v10_false_invalidates_independent_short_ar1():
    raw = _ar1(123, n=128)
    old = analyze_residual_stack_v10(raw, np.zeros_like(raw))
    assert old["classification"] == "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"

    new = analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=True,
        run_dependence_null_count=255,
    )
    audit = new["metrics"]["run_dependence_surrogate_audit"]
    assert new["classification"] != "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    assert audit["zero_lag_monte_carlo_p"] > 0.05
    assert audit["circular_monte_carlo_p"] > 0.05


def test_v10_false_invalidates_independent_one_over_f():
    raw = _one_over_f(123, n=256)
    old = analyze_residual_stack_v10(raw, np.zeros_like(raw))
    assert old["classification"] == "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"

    new = analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=True,
        run_dependence_null_count=255,
    )
    audit = new["metrics"]["run_dependence_surrogate_audit"]
    assert new["classification"] != "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    assert min(
        audit["zero_lag_monte_carlo_p"],
        audit["circular_monte_carlo_p"],
    ) > audit["per_metric_alpha"]


def test_v11_detects_shared_white_background_realization():
    raw = _shared("white")
    out = analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=True,
        run_dependence_null_count=255,
    )
    audit = out["metrics"]["run_dependence_surrogate_audit"]
    assert out["classification"] == "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    assert audit["invalidates_crossfit"] is True
    assert min(
        audit["zero_lag_monte_carlo_p"],
        audit["circular_monte_carlo_p"],
    ) <= audit["per_metric_alpha"]


def test_v11_detects_shared_ar1_background_realization():
    raw = _shared("ar1")
    out = analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=True,
        run_dependence_null_count=255,
    )
    audit = out["metrics"]["run_dependence_surrogate_audit"]
    assert out["classification"] == "RUN_DEPENDENCE_INVALIDATES_CROSSFIT"
    assert audit["invalidates_crossfit"] is True


def test_v11_fails_closed_if_null_resolution_cannot_resolve_alpha_split():
    raw = np.random.default_rng(7).normal(size=(16, 128))
    try:
        analyze_residual_stack_v11(
            raw,
            np.zeros_like(raw),
            run_dependence_stationarity_declared=True,
            run_dependence_alpha=0.01,
            run_dependence_null_count=127,
        )
    except ValueError as exc:
        assert "cannot resolve alpha/2" in str(exc)
    else:
        raise AssertionError("under-resolved run-dependence null was accepted")


def test_v11_without_stationarity_declaration_refuses_calibrated_dependence_claim():
    raw = np.random.default_rng(8).normal(size=(16, 128))
    out = analyze_residual_stack_v11(
        raw,
        np.zeros_like(raw),
        run_dependence_stationarity_declared=False,
    )
    assert (
        out["metrics"]["run_dependence_audit_status"]
        == "UNCALIBRATED_STATIONARITY_NOT_DECLARED"
    )
    assert (
        out["metrics"]["run_dependence_surrogate_audit"]["invalidates_crossfit"]
        is None
    )
    assert out["policy"]["run_dependence_audit_calibrated"] is False
