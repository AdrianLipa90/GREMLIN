# GREMLIN GL(3) Hyperelastic Field Dynamics Audit
Date: 2026-09-26
Status: OBJECTIVE_FIELD_DYNAMICS_PASS

## Result

The calibrated GL(3) deformation carrier now has an objective continuum
dynamics.

Stored energy:

    W(F)
      =mu/2[tr(F^T F)-3-2ln det F]
       +lambda/2[ln det F]^2.

First Piola stress:

    P
      =mu(F-F^{-T})
       +lambda ln(det F)F^{-T}.

Rigid rotations have exactly zero stored energy/stress, and left rotations do
not change the energy.

Spatial regularization:

    eta/2 |Grad F|^2

gives the field equation

    rho0 u_tt
      =Div P
       -eta Delta^2 u

for constant eta with F=I+Grad u.

Linear dispersions:

    omega_L^2
      =[(lambda+2mu)/rho0]k^2
       +(eta/rho0)k^4,

    omega_T^2
      =[mu/rho0]k^2
       +(eta/rho0)k^4.

Compatibility is tracked independently by

    alpha=Curl F.

Independent algebraic replay:

    7/7 PASS.

This is continuum mechanics. It is not promoted to gravity or spacetime
curvature.
