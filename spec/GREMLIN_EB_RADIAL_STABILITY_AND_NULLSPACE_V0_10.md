# GREMLIN EB Radial Stability and Nullspace v0.10

Status: CANDIDATE_ONLY / CHYBA / DERIVED_AFTER_TYPED_RADIAL_ADMISSION / PHYSICAL_CARRIER_BINDING_OPEN

## Scope

This gate extends GREMLIN v0.9 from circular balance to radial stability while keeping every non-Keplerian radial contribution explicit.

Define:

    W(r) = U_I(r) + Q_rho(r) + V_trap(r) + mu_int(r)
    U_I = g_I Xi_I
    g_I = alpha_I/kappa_E
    A_G = C_mu H_Phi^EB eta_G

No term is silently absorbed into U_I.

## Circular and epicyclic equations

The admitted circular branch is

    Omega^2 = A_G/r^3 + W'/(m_I r).

For

    V_eff = -m_I A_G/r + W(r) + L_eff^2/(2 m_I r^2),

the small-radial-perturbation frequency is

    kappa_r^2 = A_G/r^3 + (W'' + 3 W'/r)/m_I.

Subtracting gives

    kappa_r^2 - Omega^2
      = (W'' + 2 W'/r)/m_I
      = Delta_3 W / m_I.

The source amplitude A_G cancels exactly.

## Information-channel isolation

Only after independently declared controls are removed may the residual be attributed to the informational potential:

    m_I (kappa_r^2 - Omega^2)
      - Delta_3(Q_rho + V_trap + mu_int)
      = g_I Delta_3 Xi_I.

Hence, when Delta_3 Xi_I != 0,

    g_I
      = [m_I(kappa_r^2-Omega^2)-Delta_3 controls]
        / Delta_3 Xi_I.

If Delta_3 Xi_I = 0, the precession route is non-identifying and must fail closed.

## Exact radial harmonic nullspace

For r>0,

    Delta_3 U = U'' + 2 U'/r = 0

has

    U(r) = u0 - lambda/r.

Then

    U'  =  lambda/r^2
    U'' = -2 lambda/r^3
    Delta_3 U = 0.

The inverse-radius term still changes the circular orbit:

    (1/(m_I r)) U' = lambda/(m_I r^3),

which is exactly degenerate with

    A_G -> A_G + lambda/m_I.

Therefore circular orbit plus radial precession cannot distinguish this potential from a source-strength shift.

## Firewalls

The gate does not promote:

- U_I -> physical gravity;
- U_I -> g_mu_nu;
- EB-condensate physical identity;
- any unmeasured Q_rho, trap or interaction term to zero;
- Delta_3 W to Delta_3 U_I unless controls are independently subtracted.

## Executable surface

Implementation: tools/gremlin_eb_radial_stability_nullspace_v010.py

Tests: tests/test_gremlin_eb_radial_stability_nullspace_v010.py

Parent: spec/GREMLIN_EB_CONDENSATE_ORBITAL_PHASE_BRIDGE_V0_9.md
