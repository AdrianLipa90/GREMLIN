import numpy as np

from gremlin_mcp.residual_spectroscopy_v09 import analyze_residual_stack_v09


def _transient(seed, *, runs=16, n=2048, amp=0.8, k=137.5, start=5, length=3):
    rng=np.random.default_rng(seed)
    raw=rng.normal(size=(runs,n))
    t=np.arange(n)
    for i in range(start,min(runs,start+length)):
        raw[i]+=amp*np.sin(2*np.pi*k*t/n+0.2*i)
    return raw


def test_v09_three_run_transient_cohort_is_recovered():
    raw=_transient(340001,length=3)
    out=analyze_residual_stack_v09(
        raw,np.zeros_like(raw),ordered_runs=True
    )
    assert out["classification"]=="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"
    gate=out["metrics"]["transient_cohort_gate"]
    assert gate["cohort_pass"] is True
    assert gate["largest_cluster_length"]>=2
    assert set(gate["largest_cluster"]).issubset({5,6,7})


def test_v09_same_data_without_order_cannot_claim_cohort():
    raw=_transient(340001,length=3)
    out=analyze_residual_stack_v09(
        raw,np.zeros_like(raw),ordered_runs=False
    )
    assert out["classification"]!="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"
    gate=out["metrics"]["transient_cohort_gate"]
    assert gate["ordered_runs"] is False
    assert gate["cohort_pass"] is False


def test_v09_single_run_event_is_not_promoted_to_cohort():
    raw=_transient(340001,length=1)
    out=analyze_residual_stack_v09(
        raw,np.zeros_like(raw),ordered_runs=True
    )
    assert out["classification"]!="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"
    assert out["metrics"]["transient_cohort_gate"]["single_run_anomalies_are_diagnostic_only"] is True


def test_v09_white_noise_seed_bank_has_no_transient_cohort():
    for seed in range(20):
        raw=np.random.default_rng(350000+seed).normal(size=(16,2048))
        out=analyze_residual_stack_v09(
            raw,np.zeros_like(raw),ordered_runs=True
        )
        assert out["classification"]!="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"


def test_v09_ar1_seed_bank_has_no_transient_cohort():
    for seed in range(10):
        rng=np.random.default_rng(360000+seed)
        eps=rng.normal(size=(16,2048))
        raw=np.zeros_like(eps)
        for j in range(raw.shape[1]):
            raw[:,j]=eps[:,j] if j==0 else 0.8*raw[:,j-1]+eps[:,j]
        out=analyze_residual_stack_v09(
            raw,np.zeros_like(raw),ordered_runs=True
        )
        assert out["classification"]!="UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE"


def test_v09_policy_preserves_transient_without_physical_promotion():
    raw=_transient(340001,length=3)
    out=analyze_residual_stack_v09(
        raw,np.zeros_like(raw),ordered_runs=True
    )
    assert out["policy"]["transient_structure_not_required_to_be_global_persistent"] is True
    assert out["policy"]["transient_cohort_candidate_is_not_physical_attribution"] is True
    assert out["policy"]["time_fluctuation_claim_allowed"] is False
