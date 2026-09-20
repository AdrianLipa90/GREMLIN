# GREMLIN Endogenous EB Condensate Normal Modes v0.12

Status: CANDIDATE_SAME_CARRIER_BRIDGE / EXACT_AFTER_DECLARED_HARD_LOCK / PHYSICAL_BINDING_OPEN

## Scope

This gate distinguishes a frozen/external EB source from an endogenous same-carrier EB source and exposes the linear normal-mode problem without inventing mixed physical couplings.

The declared candidate bridge is

chi = q_eff theta + chi_0

or, with an explicit clock factor,

D_tau chi = q_eff zeta_tau Omega.

The hard-lock branch is an assumption of this gate. It is not promoted to a physical identity.

Parents:
- GREMLIN EB condensate orbital phase bridge v0.9;
- GREMLIN EB radial stability/nullspace v0.10;
- GREMLIN cross-domain coupling identifiability v0.11;
- GREMLIN radial-medium identifiability v0.1 on current main;
- RFC RF-S22 matched-H branch.

## 1. Endogenous EB budget

With

H_Phi^EB = (I_phi/2) q_eff^2 zeta_tau^2 Omega^2

and

mu_source = C_mu H_Phi^EB,

define

Lambda_EB =
C_mu eta_G I_phi q_eff^2 zeta_tau^2 / (2 r^3).

For a winding carrier

Omega = eta_phi q_eff / (m_I r^2).

The radial circular-balance budget is

1 = Lambda_EB + sum_j Lambda_j,

where

Lambda_j = V_j' / (m_I r Omega^2).

The executable gate never normalizes a non-closing budget silently.

## 2. Pure hard-lock branch

When all extra radial gradients vanish and Omega is non-zero,

Lambda_EB = 1,

so

r_*^3 =
(C_mu eta_G I_phi q_eff^2 zeta_tau^2)/2.

For fixed zeta_tau this gives the branch fingerprint

r_* ~ |q_eff|^(2/3),
|Omega_*| ~ |q_eff|^(-1/3),
H_Phi^EB ~ |q_eff|^(4/3).

These are conditional same-carrier scalings, not universal orbit quantization.

## 3. External versus endogenous radial stability

For a frozen/external inverse-radius source, the ordinary pure-source branch has

kappa_ext^2 = Omega^2.

For the endogenous hard-lock source the radial source strength changes with the orbit because

H_Phi^EB ~ Omega^2 ~ r^(-4).

Before using the equilibrium budget, the exact hard-lock radial stiffness is

kappa_end^2 =
(3 - 6 Lambda_EB) Omega^2
+ V_rad''/m_I.

After enforcing

1 = Lambda_EB + V_rad'/(m_I r Omega^2),

the same expression becomes

kappa_end^2 =
-3 Omega^2
+ [V_rad'' + 6 V_rad'/r]/m_I.

Therefore the pure endogenous branch has

kappa_end^2 = -3 Omega^2.

The existence condition Lambda_EB=1 is not a stability condition.

## 4. Stabilization gate

Define

S =
[V_rad'' + 6 V_rad'/r] / (m_I Omega^2).

Then

kappa_end^2/Omega^2 = S - 3,

so radial stability requires

S > 3.

When V_rad is decomposed into independently sourced terms this is equivalent to summing their declared curvature/gradient contributions. No missing term is silently set to zero.

## 5. Stationary-central cross-check and derivative firewall

Current main contains the exact stationary-central identity

kappa_epi^2 = 4 Omega^2 + r d(Omega^2)/dr.

Two derivatives must not be conflated.

Along the fixed-q winding constraint,

Omega = eta_phi q_eff/(m_I r^2),

so

d ln(Omega^2)/d ln r = -4.

That derivative describes the fixed-winding trajectory constraint.

For the pure endogenous source at fixed branch parameters, however, the source acceleration scales as r^(-6). The circular-family force law is therefore

Omega_circ^2 ~ r^(-7),

so

d ln(Omega_circ^2)/d ln r = -7.

The stationary-central identity then gives

kappa_epi^2 = 4 Omega^2 - 7 Omega^2 = -3 Omega^2,

exactly matching the endogenous feedback calculation.

Therefore the BELZEBUB-style central-consistency residual is

B_end = 0

for the correctly declared r^(-7) circular-family derivative.

Using the winding derivative -4/r inside the stationary-central epicyclic identity is a category error and must fail review. The fixed-q winding law and the circular-family force derivative are different objects.

## 6. Finite phase lock

To keep the phase degree of freedom explicit define

psi = chi - q_eff theta - chi_0.

Hard lock is psi=0. A finite locking model may declare

V_lock = (K_psi/2) psi^2.

After eliminating the cyclic common phase, with orbital inertia J_theta, the relative-phase inertia is

I_rel =
I_phi J_theta / (J_theta + q_eff^2 I_phi).

The uncoupled relative-phase frequency is

Omega_psi^2 = K_psi / I_rel.

The limit K_psi -> infinity recovers the hard-lock constraint by pushing the relative mode to infinite frequency.

## 7. Collective normal-mode interface

Use

delta X = (delta r, delta a_rho, delta psi)^T.

The executable interface accepts an explicit model

M delta Xdd + G delta Xd + K delta X = 0,

with:
- M symmetric positive definite;
- G antisymmetric;
- K symmetric.

The solver linearizes this to a six-dimensional first-order system and returns all eigenvalues, positive oscillation frequencies, maximum growth rate and a stability flag.

Mixed entries such as K_r_rho, K_r_psi, K_rho_psi and gyroscopic couplings are caller-owned inputs. GREMLIN does not fabricate them from notation.

The source term itself has a velocity sensitivity

partial a_source / partial(D_tau chi)
=
-C_mu eta_G I_phi (D_tau chi)/r^2,

which is why a G-type velocity coupling is allowed by the interface. The complete physical G matrix remains OPEN until a common coupled action is supplied.

## 8. Cross-domain Hessian interpretation

The shared upstream object may be projected differently:

- orbital route: radial gradient and curvature -> circular shift and kappa_end;
- condensate/chemistry route: density/configuration curvature -> collective or vibrational stiffness;
- phase optics route: transverse Hessian -> focusing/shear;
- spectroscopy route: admitted normal-mode eigenfrequencies -> candidate sidebands/resonances.

These projections are not numerically identical Hessians unless an explicit adapter proves that identification.

## 9. Firewalls

This gate does not establish:
- a physical EB condensate;
- the same-carrier phase bridge in nature;
- C_mu or eta_G individually;
- a spacetime metric modification;
- any mixed Hessian or gyroscopic coefficient without an independent adapter;
- that every normal mode is an observable chemical/spectroscopic line;
- that a stationary-central model and endogenous feedback are interchangeable.

Implementation:
tools/gremlin_endogenous_eb_condensate_normal_modes_v012.py

Tests:
tests/test_gremlin_endogenous_eb_condensate_normal_modes_v012.py
tests/test_gremlin_eb_endogenous_chain_v012.py


## Integration refresh — 2026-09-20

This review surface was refreshed against GREMLIN `main` commit
`f2e454b15c86053c69de93056262cb9e073bfb87` after the validated anti-entropy
and source-family-channel merges. This integration refresh changes no v0.10,
v0.11 or v0.12 mathematical claim, physical binding, firewall or epistemic status.
Hosted exact-head CI remains the integration authority.
