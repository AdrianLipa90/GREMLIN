# GREMLIN Saint-Venant / Linearized Einstein Audit
Date: 2026-09-26
Status: EXACT_LINEAR_BRIDGE_PASS / NONLINEAR_FIREWALL_NEXT

The spatial deformation and curvature stacks meet exactly at first order:

    inc(epsilon)
      =G_spatial^(1)[delta+2epsilon].

With project convention alpha=Curl beta_p and compatible total distortion:

    G_spatial^(1)
      =-sym Curl(alpha^T).

Independent residuals are at ~1e-16.

Critical boundary:
this does not mean Curl E or alpha alone is a nonlinear curvature observable.
A locally rotated flat triad can have nonzero raw Curl while its metric and
Riemann curvature remain flat.

Next gate:
nonlinear coframe incompatibility firewall using a pure local-rotation flat
control against the nonflat conformal reference.
