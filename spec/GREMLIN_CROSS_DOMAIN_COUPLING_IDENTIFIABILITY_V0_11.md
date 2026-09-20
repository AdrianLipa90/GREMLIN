# GREMLIN Cross-Domain Coupling Identifiability v0.11

Status: CANDIDATE_ONLY / CHYBA / EXACT_IDENTIFIABILITY_AFTER_INDEPENDENT_ADAPTERS / PHYSICAL_BINDING_OPEN

## Scope

This gate asks which parameters become identifiable when independent orbital, radial-stability, phase-optics, spectroscopy and phase-circulation readouts are combined.

Targets:

    g_I = alpha_I/kappa_E
    beta_G = C_mu eta_G
    gamma_B

C_mu and eta_G remain separate only after an independent source-only or coupling-only receipt is supplied. No downstream route is fitted to reproduce another.

## Independent g_I estimators

Precession, after explicit subtraction of Q_rho, trap and interaction curvature:

    g_I^(prec) = m_I delta_prec / Delta_3 Xi_I.

The route is undefined on Delta_3 Xi_I=0.

For the typed phase-optics relation

    H_Phi = -chi_phi g_I H_Xi,

the Frobenius projection gives

    g_I^(opt)
      = - <H_Phi,H_Xi>_F
        / [chi_phi ||H_Xi||_F^2].

A zero projected Xi Hessian is non-identifying.

For the long symmetric-path projection of U=-lambda/r after the common phase offset is removed,

    h_r = +2 chi_phi lambda/b^2
    h_t = -2 chi_phi lambda/b^2.

Thus h_r+h_t=0 outside the source while h_r-h_t != 0 for lambda != 0. The inverse-radius mode is therefore visible in optical shear.

For a non-common-mode chemistry adapter,

    g_I^(spec)
      = hbar Delta omega_mn
        / Delta <Xi_I>_mn.

If Delta <Xi_I>_mn=0, spectroscopy is common-mode and fails closed as an estimator of g_I.

## Cross-domain consistency

Independent estimators must agree within declared tolerance:

    g_I^(prec) ?= g_I^(opt) ?= g_I^(spec).

The implementation compares routes directly and does not average inconsistent routes into a fitted value.

## Orbital subtraction and beta_G

After g_I and all declared radial controls are independently supplied,

    beta_G
      = r^3/H_Phi^EB
        [Omega^2 - (g_I Xi_I' + controls')/(m_I r)].

On one frozen source/carrier branch,

    beta_G(r_1)=...=beta_G(r_N)

is a consistency test rather than a fitting target.

## Exact C_mu / eta_G rank no-go

The source contribution is

    Omega_source^2 = C_mu H_Phi^EB eta_G/r^3.

Therefore

    d Omega^2/d C_mu = H_Phi^EB eta_G/r^3
    d Omega^2/d eta_G = H_Phi^EB C_mu/r^3.

The Jacobian columns are proportional:

    col_eta = (C_mu/eta_G) col_C.

Their orbital rank is exactly one. Observables that do not separately depend on C_mu or eta_G cannot remove this degeneracy.

The factorization beta_G=C_mu eta_G must fail closed unless at least one factor has an independent provenance receipt.

## Independent Berry/holonomy lane

For phase circulation independent of orbital reconstruction,

    gamma_B
      = 2 pi n
        - (m_I/eta_phi) integral v.dl.

The executable function requires a circulation receipt identifier. Reusing the same orbital Omega without an independent phase/holonomy measurement does not create a new constraint.

## Firewalls

This gate does not establish:

- physical informational coupling;
- physical EB-condensate realization;
- metric/gravitational binding;
- C_mu or eta_G individually without an independent receipt;
- independence of an adapter merely because it has a different filename.

## Executable surface

Implementation: tools/gremlin_cross_domain_coupling_identifiability_v011.py

Tests: tests/test_gremlin_cross_domain_coupling_identifiability_v011.py

Parents:

- spec/GREMLIN_EB_CONDENSATE_ORBITAL_PHASE_BRIDGE_V0_9.md
- spec/GREMLIN_EB_RADIAL_STABILITY_AND_NULLSPACE_V0_10.md
- QHTRI phase-optics THEORY.md at c59f84ff38084d34d7b6c4a6ec8fcd4b9b75d152
- Resonant-Chemistry crosswalk at 0774e762af047e05198da40777b7f78d34da54d2
