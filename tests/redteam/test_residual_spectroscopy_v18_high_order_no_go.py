import numpy as np

from gremlin_mcp.residual_spectroscopy_v18 import nonlinear_run_dependence_audit_v18


def test_v18_low_order_feature_bank_misses_high_order_chebyshev_dependence():
    # Intentional no-go reproducer. x1 is a deterministic polynomial
    # (Chebyshev T7) of x0, but the finite feature bank {x,x2,x3,absx}
    # does not reject at the strict nonlinear alpha.
    rng=np.random.default_rng(181807)
    runs,n=16,512
    phi=rng.uniform(0,2*np.pi,size=n)
    raw=rng.normal(size=(runs,n))
    raw[0]=np.sqrt(2.0)*np.cos(phi)
    raw[1]=np.sqrt(2.0)*np.cos(7.0*phi)

    out=nonlinear_run_dependence_audit_v18(
        raw,20,null_count=255,iaaft_iterations=10,alpha=0.005
    )

    assert out["invalidates_crossfit"] is False
    assert out["monte_carlo_p"]>0.5
