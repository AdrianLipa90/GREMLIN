import numpy as np

from gremlin_mcp.joint_family_null_v15 import joint_family_round_v15


def test_v15_target_derived_raw_copy_passes_without_candidate_bank_provenance_gate():
    # Intentional failure reproducer for v0.15's input contract.
    # The joint family null controls the supplied family statistically, but it
    # cannot detect that a candidate was manufactured from the target itself.
    rng=np.random.default_rng(151500)
    raw=rng.normal(size=(8,128))
    candidates={"leak_raw":raw.copy()}
    candidates.update({
        f"noise_{j}":rng.normal(size=raw.shape)
        for j in range(7)
    })
    metadata={
        name:{"null_policy":"run_permutation"}
        for name in candidates
    }

    out=joint_family_round_v15(
        raw,
        np.zeros_like(raw),
        candidates,
        metadata,
        null_count=127,
        familywise_alpha=0.05,
    )

    score=out["scores"]["leak_raw"]

    # v0.15 currently accepts this target-derived candidate. The test pins the
    # gap so a later candidate-bank seal repair cannot erase the counterexample.
    assert score["decision"]=="PASS"
    assert score["conservative_holdout_gain"]==1.0
    assert score["familywise_monte_carlo_p"]==0.0078125
