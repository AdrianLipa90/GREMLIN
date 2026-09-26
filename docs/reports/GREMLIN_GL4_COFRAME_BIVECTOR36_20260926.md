# GREMLIN GL(4) Coframe / Bivector36 Audit
Date: 2026-09-26
Status: KINEMATIC_GL4_PASS

The 36-coefficient carrier now has a controlled 4D interpretation:

    rho_36(A)=Lambda^2 A.

It exactly contains the previous GL(3), SO(3) and SO(2) sectors.

For Lorentz transformations, the induced six-dimensional metric is

    G=diag(-1,-1,-1,+1,+1,+1),

so the Lorentz image sits inside SO(3,3).

Independent numerical crosschecks are at ~1e-15 residual scale.

A critical inverse limitation is explicit:

    Lambda^2(A)=Lambda^2(-A).

Therefore Bivector36 does not uniquely reconstruct the underlying coframe
without an extra Z2 witness.

Next gate:
connection/holonomy kinematics with exact pure-gauge negative controls before
any curvature promotion.
