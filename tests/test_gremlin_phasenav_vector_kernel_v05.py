import numpy as np

from tools.gremlin_phasenav_vector_kernel_bench_v05 import (
    TOL,
    make_case,
    scalar_batch,
    vector_batch,
)


def test_case_deterministic_hash():
    *_, digest = make_case()
    assert digest == "ec74ebfa41cae35b78cf1b90249d53d6978fc17a0575699f7707a6487686c802"


def test_vector_matches_scalar_prefix():
    theta, ell, tau, gain, _ = make_case()
    ref = scalar_batch(theta[:32], ell, tau, gain)
    potential, force = vector_batch(theta[:32], ell, tau, gain)

    max_potential_error = max(abs(ref[i][0] - float(potential[i])) for i in range(32))
    max_force_error = max(
        abs(ref[i][1][j] - float(force[i, j]))
        for i in range(32)
        for j in range(36)
    )

    assert max_potential_error <= TOL
    assert max_force_error <= TOL
    assert np.isfinite(potential).all()
    assert np.isfinite(force).all()
