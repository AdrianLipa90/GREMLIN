# GREMLIN Stress–Plastic–Defect Coupling Audit
Date: 2026-09-26
Status: THERMODYNAMIC_REFERENCE_PASS

The defect layer now has a stress-coupled internal-state reference rather than
an arbitrary velocity law.

Small-strain elastic/plastic split:

    eps_e=sym(Grad u-beta_p).

Convex free energy:

    psi
      =mu|eps_e|^2
       +lambda/2[tr eps_e]^2
       +H/2|beta_p|^2.

Thermodynamic force:

    Y=sigma-H beta_p.

Onsager kinetics:

    beta_p_dot=M Y.

Exact result:

    dpsi/dtau=-M|Y|^2<=0.

Independent replay:

    8/8 PASS.

Measured:
- equilibrium force norm 2.68e-16;
- exact-step semigroup residual 9.97e-18;
- dissipation-identity finite-difference relative error 1.28e-6.

Defect content is diagnosed by

    alpha=Curl beta_p.

This closes a thermodynamically admissible small-strain coupling only. It does
not promote a finite-strain F=F_e F_p theory, yield criterion, slip-system
model or Peach-Koehler kinetics.
