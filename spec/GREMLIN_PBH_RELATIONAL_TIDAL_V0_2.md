# GREMLIN PBH Relational Tidal Gate v0.2

Status: `FAIL-CLOSED / POINT-MASS EIGENSHAPE REQUIRED / NO PBH IDENTITY CLAIM`

The leading gravitational signature of a sufficiently distant point mass is

```math
T = \mu(3uu^T-I),\qquad \mu = GM/r^3.
```

The v0.1 gate compared fitted source axes and amplitudes, but any generic symmetric tensor could still be projected onto a best-fit point-mass shape.  v0.2 closes that loophole.

For a genuine leading-order point-mass tide, the tensor must satisfy all of:

- symmetry;
- trace compatibility with zero;
- positive fitted `mu`;
- small residual after projection onto `mu(3uu^T-I)`;
- a near-degenerate pair of transverse eigenvalues;
- eigenvalue pattern consistent with `(-mu,-mu,+2mu)`.

The implementation therefore computes an explicit symmetric 3x3 eigendecomposition and emits:

```text
eigenvalues_ascending
axis_sign_degenerate
mu_fit
symmetry_error
trace_ratio
point_mass_shape_residual
transverse_eigenvalue_split_over_mu
passes
```

A multi-layer packet is promoted only to `RELATIONAL_POINT_MASS_CANDIDATE` when every independent fitted tensor passes its own point-mass eigenshape checks.  Otherwise it remains `RELATIONAL_TENSOR_ONLY`.

This gate deliberately does **not** convert likelihood-ratio improvement to Gaussian sigma.  Null calibration belongs to the upstream astrometric inference layer.

Required independent layers remain:

1. major-planet ranging / ephemeris residuals;
2. Pluto / large-TNO astrometric residuals;
3. detached-TNO secular dynamics only as a later degeneracy/consistency layer.

Gravity alone cannot distinguish a PBH from a dark planet with identical mass and trajectory.
