import numpy as np

from gremlin_mcp.residual_spectroscopy_v05 import analyze_residual_stack_v05


def _powerlaw(seed, alpha=1.0, runs=16, n=4096):
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n)
    amp = np.zeros_like(f)
    amp[1:] = 1.0 / (f[1:] ** (alpha / 2.0))
    rows = []
    for _ in range(runs):
        z = amp * (rng.normal(size=len(f)) + 1j * rng.normal(size=len(f)))
        x = np.fft.irfft(z, n=n)
        x = (x - x.mean()) / x.std()
        rows.append(x)
    return np.asarray(rows)


def _broken_powerlaw(seed, knee=8, runs=16, n=4096):
    rng = np.random.default_rng(seed)
    k = np.arange(n // 2 + 1)
    kk = np.maximum(k[1:], 1)
    power = np.where(
        kk <= knee,
        kk ** (-2.0),
        (knee ** (-0.3 + 2.0)) * kk ** (-0.3),
    )
    amp = np.zeros_like(k, dtype=float)
    amp[1:] = np.sqrt(power)
    rows = []
    for _ in range(runs):
        z = amp * (rng.normal(size=len(k)) + 1j * rng.normal(size=len(k)))
        x = np.fft.irfft(z, n=n)
        x = (x - x.mean()) / x.std()
        rows.append(x)
    return np.asarray(rows)


def _line(seed, fbin, amplitude, runs=16, n=4096):
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(runs, n))
    t = np.arange(n)
    for i in range(runs):
        raw[i] += amplitude * np.sin(2 * np.pi * fbin * t / n + 0.2 * i)
    return raw


def test_v05_recovers_low_frequency_feature_hidden_by_v04_difference_bias():
    raw = _line(601, fbin=3.0, amplitude=0.2)
    out = analyze_residual_stack_v05(raw, np.zeros_like(raw))
    assert out["classification"] == "UNRESOLVED_LOW_FREQUENCY_SPECTRAL_FEATURE_CANDIDATE"
    gate = out["metrics"]["crossfit_low_frequency_feature_gate"]
    assert gate["pass"] is True
    assert gate["median_discovery_bin"] <= 5


def test_v05_powerlaw_background_stays_colored_background():
    raw = _powerlaw(602, alpha=1.5)
    out = analyze_residual_stack_v05(raw, np.zeros_like(raw))
    assert out["classification"] == "STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"
    assert out["metrics"]["crossfit_low_frequency_feature_gate"]["pass"] is False


def test_v05_spectral_knee_is_preserved_as_feature_not_called_line():
    raw = _broken_powerlaw(603, knee=8)
    out = analyze_residual_stack_v05(raw, np.zeros_like(raw))
    assert out["classification"] in {
        "UNRESOLVED_LOW_FREQUENCY_SPECTRAL_FEATURE_CANDIDATE",
        "STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE",
        "UNRESOLVED_RESIDUAL",
    }
    assert out["classification"] != "UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"


def test_v05_high_frequency_line_keeps_v04_narrowband_path():
    raw = _line(604, fbin=137.5, amplitude=0.2)
    out = analyze_residual_stack_v05(raw, np.zeros_like(raw))
    assert out["classification"] == "UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"


def test_v05_white_noise_remains_nonstructured():
    raw = np.random.default_rng(605).normal(size=(16, 4096))
    out = analyze_residual_stack_v05(raw, np.zeros_like(raw))
    assert out["classification"] == "STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"
    assert out["metrics"]["crossfit_low_frequency_feature_gate"]["pass"] is False
