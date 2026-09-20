# GREMLIN EB-Condensate Orbital Phase Bridge v0.9

Status: `CANDIDATE_ONLY / CHYBA / EXACT_COMPOSITION_AFTER_TYPED_INPUTS / PHYSICAL_EB_BINDING_OPEN`

## 1. Purpose

This gate connects four already separated surfaces without collapsing their epistemic status:

1. RFC finite Euler-closed phase/Noether Hamiltonian `H_Phi^EB`;
2. GREMLIN role-separated orbital source/coupling kernel;
3. informational phase mechanics `Xi_I -> U_I -> phase/force/lens`;
4. a possible condensate realization carrying density, phase and current.

The label `EB-condensate` does not by itself identify a physical condensate with the RFC Euler-closed `EB` carrier. That realization is an explicit source-binding gate.

## 2. Existing exact/conditional parents

RFC RF-S22 supplies, on its admitted matched-H branch,

```text
E_G = H_Phi^EB.
```

GREMLIN orbit-source identifiability v0.8 supplies

```text
mu_source = C_mu * E_Sigma
omega^2 = mu_source * eta_G / r^3
eta_G = q_coupling / m_inertial
```

with `C_mu` and one factor of the source/coupling split independently required.

Composing only these declared interfaces gives

```text
mu_source = C_mu * H_Phi^EB
```

when the RFC integrated generator source is the admitted `E_Sigma`.

This is an exact algebraic composition after those parent inputs are admitted. It does not determine `C_mu`.

## 3. Informational-potential orbital term

The phase-optics repository supplies

```text
U_I = (alpha_I/kappa_E) Xi_I
dU_I/dr = (alpha_I/kappa_E) dXi_I/dr.
```

If a source-owned carrier Lagrangian admits `U_I(r)` as an additional radial potential energy term, circular balance becomes

```text
omega^2
 = C_mu H_Phi^EB eta_G / r^3
 + (1/(m_I r)) dU_I/dr
```

or

```text
omega^2
 = C_mu H_Phi^EB eta_G / r^3
 + alpha_I/(m_I r kappa_E) dXi_I/dr.
```

Everything after the Lagrangian admission is derived. Admission of the term to a physical carrier remains OPEN.

## 4. Condensate phase branch

For a condensate-like phase field

```text
Psi = sqrt(rho) exp(i S/eta_phi),
```

the standard Madelung mechanical momentum is represented by

```text
p_mech = grad(S) - A_B.
```

For an azimuthal winding `n in Z` and Berry/connection holonomy

```text
gamma_B = integral A_B.dl / eta_phi,
```

define

```text
q_eff = n - gamma_B/(2*pi).
```

On the adiabatic azimuthal branch where no additional connection-curvature force is omitted,

```text
v_theta = eta_phi q_eff/(m_I r)
omega_phase = eta_phi q_eff/(m_I r^2).
```

The condensate quantum-pressure coordinate is retained explicitly:

```text
Q_rho = -(eta_phi^2/(2m_I)) Delta sqrt(rho)/sqrt(rho).
```

Any radial derivative of `Q_rho`, interaction chemical potential, trap potential or other condensate term belongs in the declared total radial potential. It must not be silently absorbed into `U_I`.

## 5. EB orbital closure equation

Equating the phase-winding angular rate with the source-plus-information circular balance gives

```text
eta_phi^2 q_eff^2/(m_I^2 r^4)
 =
 C_mu H_Phi^EB eta_G/r^3
 + alpha_I/(m_I r kappa_E) dXi_I/dr.
```

Equivalently,

```text
R_EB =
 eta_phi^2 q_eff^2/m_I^2
 - C_mu H_Phi^EB eta_G r
 - alpha_I r^3/(m_I kappa_E) dXi_I/dr
 = 0.
```

This is the principal dependency equation for the GREMLIN investigation.

On the pure-source branch `dXi_I/dr=0`,

```text
r
 = eta_phi^2 q_eff^2
   /(m_I^2 C_mu H_Phi^EB eta_G).
```

This is a conditional radius relation, not a universal orbital quantisation claim.

## 6. Known versus suspected graph

```text
RFC Noether current / occupation              DERIVED / CONDITIONAL PARENTS
        |
        v
RFC H_Phi^EB and E_G=H_Phi^EB               DERIVED CONDITIONAL
        |
        | C_mu explicit
        v
GREMLIN mu_source=C_mu H_Phi^EB              CONDITIONAL COMPOSITION
        |
        +------------------+
        |                  |
        v                  v
Kepler source term      Xi_I -> U_I           DERIVED MODEL FUNCTIONAL
        |                  |
        +--------+---------+
                 v
      orbital circular balance               DERIVED AFTER LAGRANGIAN ADMISSION
                 ^
                 |
rho, phase, current -> q_eff / Q_rho          STANDARD CONDENSATE MECHANICS
                 ^
                 |
physical EB-condensate/source map             OPEN / CANDIDATE
```

GREMLIN must not promote an arrow merely because both endpoint equations exist.

## 7. Cross-domain observables

The same admitted phase/potential state can be interrogated through distinct downstream surfaces:

```text
orbital:      omega(r), r, precession, stability
optical:      grad Phi, Hess Phi, convergence, shear, caustics
spectral:     dPhi/domega, d2Phi/domega2, line/receiver response
chemical:     Delta E_n, forces, Hessians, transition shifts
```

Independent agreement is evidential only when the downstream routes are constructed without fitting one route to the other.

## 8. Firewalls

OPEN inputs remain:

- physical identification of an EB-condensate state with the RFC Euler-closed phase carrier;
- source-owned map from condensate observables to the RFC relational/current state;
- `C_mu` source coefficient;
- `eta_G=q_coupling/m_inertial` physical ownership;
- informational-potential admission to the orbital Lagrangian;
- `U_I -> g_mu_nu` metric binding;
- complete condensate radial potential including interaction, trap and quantum-pressure gradients.

No gravitational-lensing claim follows from this gate alone.

## 9. Executable surface

Implementation:

`tools/gremlin_eb_condensate_orbital_phase_bridge_v09.py`

Tests:

`tests/test_gremlin_eb_condensate_orbital_phase_bridge_v09.py`

The implementation evaluates only the equations declared above and fails closed on invalid domains.
