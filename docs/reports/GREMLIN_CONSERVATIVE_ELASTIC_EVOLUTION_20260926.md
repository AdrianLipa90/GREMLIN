# GREMLIN Conservative Elastic Evolution Audit
Date: 2026-09-26
Status: NUMERICAL_REFERENCE_PASS

A conservative linearized reference evolution has been attached to the GL(3)
hyperelastic field.

Equation:

    u_tt
      =c^2u_xx
       -(eta/rho0)u_xxxx.

The finite-difference force is paired with its exact discrete Hamiltonian, and
time stepping uses velocity-Verlet.

Independent replay:

    7/7 PASS.

Observed:
- max relative energy deviation over 5000 steps: 1.74663e-6;
- max momentum deviation over 2000 steps: 3.77476e-15.

One verification threshold was corrected after replay:
the absolute Fourier residual gate 1e-10 was replaced by a scale-aware
float64 bound because the D4/dx^4 stencil amplifies cancellation. The
underlying operator was not changed.

This gate validates conservative numerical structure, not a production 3D
nonlinear solver.
