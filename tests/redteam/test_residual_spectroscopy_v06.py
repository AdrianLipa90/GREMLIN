import numpy as np

from gremlin_mcp.residual_spectroscopy_v05 import analyze_residual_stack_v05
from gremlin_mcp.residual_spectroscopy_v06 import analyze_residual_stack_v06


def _cubic(seed, amp=5.0, runs=16, n=2048):
    rng=np.random.default_rng(seed)
    x=np.linspace(-1.0,1.0,n)
    base=x**3
    return np.asarray([
        amp*base+rng.normal(size=n)
        for _ in range(runs)
    ])


def _line(seed, *, k, amp, runs=16, n=2048):
    rng=np.random.default_rng(seed)
    t=np.arange(n)
    return np.asarray([
        rng.normal(size=n)+amp*np.sin(2*np.pi*k*t/n+0.2*i)
        for i in range(runs)
    ])


def test_v05_cubic_trend_reproducer_is_mistyped_as_narrowband():
    raw=_cubic(50000)
    out=analyze_residual_stack_v05(
        raw,np.zeros_like(raw),ordered_runs=False
    )
    assert out["legacy_v04_classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    assert out["classification"]=="UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE"
    assert out["metrics"]["crossfit_narrowband_gate"]["median_discovery_bin"]==1.0


def test_v06_cubic_trend_is_preserved_as_low_frequency_ambiguity():
    for seed in range(30):
        raw=_cubic(50000+seed)
        out=analyze_residual_stack_v06(
            raw,np.zeros_like(raw),ordered_runs=False
        )
        assert out["classification"]=="LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE"
        audit=out["metrics"]["trend_ambiguity_audit"]
        assert audit["low_frequency_ambiguous"] is True
        assert audit["median_discovery_bin"]<audit["trend_ambiguity_cycles"]
        assert out["policy"]["ambiguity_is_not_noise"] is True


def test_v06_real_low_frequency_line_is_also_kept_ambiguous_not_discarded():
    raw=_line(7,k=1.5,amp=1.0)
    out=analyze_residual_stack_v06(
        raw,np.zeros_like(raw),ordered_runs=False
    )
    assert out["legacy_v05_classification"]=="UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE"
    assert out["classification"]=="LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE"


def test_v06_high_frequency_line_keeps_narrowband_taxonomy():
    raw=_line(11,k=137.5,amp=0.25)
    out=analyze_residual_stack_v06(
        raw,np.zeros_like(raw),ordered_runs=False
    )
    assert out["classification"]=="UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE"
    assert out["metrics"]["trend_ambiguity_audit"]["low_frequency_ambiguous"] is False


def test_v06_white_and_ar1_controls_do_not_gain_narrowband_labels():
    white=np.random.default_rng(13).normal(size=(16,2048))
    out=analyze_residual_stack_v06(white,np.zeros_like(white))
    assert out["classification"]=="STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE"

    rng=np.random.default_rng(17)
    eps=rng.normal(size=(16,2048))
    ar=np.zeros_like(eps)
    for j in range(ar.shape[1]):
        ar[:,j]=eps[:,j] if j==0 else 0.8*ar[:,j-1]+eps[:,j]
    out2=analyze_residual_stack_v06(ar,np.zeros_like(ar))
    assert out2["classification"]=="STOCHASTIC_COLORED_BACKGROUND_COMPATIBLE"


def test_v06_sensitivity_policy_is_explicitly_nonuniversal():
    raw=_line(19,k=137.5,amp=0.25,n=1024)
    out=analyze_residual_stack_v06(raw,np.zeros_like(raw))
    audit=out["metrics"]["trend_ambiguity_audit"]
    assert audit["samples_per_run"]==1024
    assert audit["runs"]==16
    assert out["policy"]["sensitivity_threshold_not_universal_across_sample_count_or_background"] is True
