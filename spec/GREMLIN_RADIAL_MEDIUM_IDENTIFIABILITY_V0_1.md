# GREMLIN Radial Medium Identifiability v0.1

Status: `CANDIDATE_ONLY / EXACT_CENTRAL_IDENTITIES / SOURCE_ATTRIBUTION_FAIL_CLOSED`

This gate extends the existing role-typed orbital and holonomy work without
promoting a physical condensate or information-potential source. GREMLIN receives
a diagnostic layer for distinguishing a pure `1/r` radial kernel from a general
stationary central effective scalar.

## Parent surfaces

- GREMLIN orbital source/coupling identifiability v0.8:
  `K_orb = r^3 Omega^2 = mu_S eta_G` only for the declared pure `1/r` branch.
- GREMLIN connection-path holonomy v0.9:
  `tau` is a project holonomy coordinate; physical condensate-flux identification
  remains open.
- IDT 02JP/02JQ:
  nonlinear Madelung/BEC bridge and exact central inverse identities.
- RFC RF-L3:
  `U_I = (alpha_I/kappa_E) Xi_I`, with physical calibration inherited and open.

## 1. Observed radial kernel

For any circular branch define

~~~text
K_obs(r) = r^3 Omega^2(r)
~~~

The pure Kepler/source model is the special case

~~~text
K_obs(r) = mu_S eta_G = constant
~~~

For a general stationary central scalar `Phi_eff`,

~~~text
Omega^2 = Phi_eff' / r

kappa_epi^2
= 4 Omega^2 + r d(Omega^2)/dr
~~~

Hence

~~~text
dK_obs/dr = r^2 (kappa_epi^2 - Omega^2)
~~~

GREMLIN therefore treats nonzero `dK_obs/dr` as evidence for non-Kepler radial
structure, not as a source label.

## 2. BELZEBUB central-consistency residual

Define

~~~text
B(r)
= kappa_meas^2
  - 4 Omega_meas^2
  - r d(Omega_meas^2)/dr
~~~

A significant nonzero residual means the declared one-scalar stationary central
model is inconsistent with the measurements. GREMLIN must not repair this by
silently inserting a new source term.

## 3. Kepler-camouflage firewall

Any additional radial scalar of the form

~~~text
delta Phi(r) = C_0 + C_1/r
~~~

is exactly degenerate with a redefinition of the pure Kepler kernel under
`Omega(r)` and `kappa_epi(r)`.

Therefore

~~~text
Kepler-shaped data  !=>  unique source/coupling identification
~~~

The v0.8 source/coupling non-identifiability theorem is thus strengthened in
medium: even an apparently constant `K_obs` does not establish that the full
`1/r` coefficient is `mu_S eta_G`.

## 4. Condensate-subtracted residual

If independent channels provide the density profile and the declared
mean-field/quantum-pressure calibration, define

~~~text
Q_rho = (nabla^2 sqrt(rho)) / sqrt(rho)
~~~

and

~~~text
G_res(r)
= r Omega^2
  - K_orb/r^2
  - 2 M g rho'
  + 2 M^2 Q_rho'
~~~

Only after those independently constrained contributions are removed may GREMLIN
route the residual to candidate source families. Under the conditional RFC +
GREMLIN bridge,

~~~text
G_res / (2 M)
= c_I Xi_I'
  - J' cos(epsilon)
  + J sin(epsilon) epsilon'
~~~

This equation is a candidate decomposition interface, not a license to fit
`U_I`, `J`, or `epsilon` freely to the same orbital data.

## 5. Holonomy-shell susceptibility

Use

~~~text
r^2 Omega = Lambda nu

nu = ell - tau/(2 pi)
~~~

Then

~~~text
partial r / partial tau
= - Lambda^2 nu / (pi r^3 kappa_epi^2)
~~~

The response diverges at the radial marginal-stability boundary
`kappa_epi^2 -> 0`. Shell existence and shell stability are distinct.

GREMLIN may use this as a sensitivity diagnostic only after a declared
`tau`-to-carrier binding.

## 6. Precession discriminator

For nearly circular motion,

~~~text
Delta varpi
= 2 pi (Omega/kappa_epi - 1)
~~~

Near the Kepler branch,

~~~text
Delta varpi
~= - pi d ln(K_obs) / d ln(r)
~~~

This gives a cross-observable consistency check between the rotation curve and
apsidal precession.

## 7. Cross-repository links

- IDT 02JQ branch:
  https://github.com/AdrianLipa90/Informational-Dynamics-of-Time/blob/candidate/idt-eb-bec-orbital-acoustic-v0.1/formalism/02JQ_radial_condensate_profile_classification.md
- FPDG:
  https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph
- RFC:
  https://github.com/AdrianLipa90/Relational-Field-Closure
- Resonant Chemistry:
  https://github.com/AdrianLipa90/Resonant-Chemistry
- Orbital Eclipse Spectroscopy:
  https://github.com/AdrianLipa90/Orbital-Eclipse-Spectroscopy
- QHTRI phase optics:
  https://github.com/AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics

## 8. Authority firewall

PASS within this gate means the algebraic diagnostic is implemented/tested.
It does not:

- promote a Bose-Einstein condensate as the physical carrier;
- identify `q_G = m_I`;
- identify GREMLIN `tau` with a physical condensate flux;
- calibrate RFC `c_I`;
- promote an analogue/phase-optics scalar to spacetime metric curvature.
