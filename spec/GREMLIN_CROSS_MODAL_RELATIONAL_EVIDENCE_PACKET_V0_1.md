# GREMLIN Cross-Modal Relational Evidence Packet v0.1

Status: `CANDIDATE_DIAGNOSTIC_PACKET / SOURCE_ATTRIBUTION_FAIL_CLOSED / NO_SINGLE_SCORE_PROMOTION`

This packet joins independently constrained observables from the radial, condensate,
phase-optics and spectroscopy branches without collapsing them into a physical-source verdict.

Its purpose is to answer three narrower questions:

1. are the declared observables mutually consistent with one common scalar/transport model?
2. are the latent phase coordinates locally identifiable?
3. after known sectors are subtracted, is any residual still statistically resolved?

It does **not** answer "the residual is informational", "the residual is holonomic",
or "the residual is gravitational".

## 1. Typed channel residuals

Each observable channel supplies a residual

~~~text
r_a = y_a(obs) - y_a(pred)
~~~

together with a declared positive uncertainty scale `sigma_a`, or with a full
positive-definite covariance matrix `Sigma`.

For diagonal covariance,

~~~text
z_a = r_a / sigma_a
~~~

For a full covariance model,

~~~text
chi^2 = r^T Sigma^(-1) r
~~~

The statistic is a consistency diagnostic only. It is not a physical-source probability.

## 2. Recommended upstream channels

The packet can carry, when available:

- **orbital central-consistency**

~~~text
B = kappa_meas^2 - 4 Omega_meas^2 - r d(Omega_meas^2)/dr
~~~

- **condensate-subtracted radial residual**

~~~text
G_res = r Omega^2
        - K_orb/r^2
        - 2 M g rho'
        + 2 M^2 Q_rho'
~~~

- **phase-optics curvature residual**, comparing an independently measured
  phase-curvature observable to

~~~text
d^2 Phi / db^2
= (b^2/r^2) kappa^2
  + (1 - 4 b^2/r^2) Omega^2
~~~

- **spectral line/intensity response residuals** derived from the declared
  phase-dependent Hamiltonian;
- **density / Bogoliubov control residuals** constraining `g rho`, `c_s`,
  or the quantum-pressure reconstruction.

No channel is mandatory in all experiments, but absent channels reduce what may be inferred.

## 3. Phase-identifiability gate

Let the declared effective transport graph have cycle rank `beta_1`.

The phase sector is locally identifiable only if

~~~text
rank(J) >= beta_1
and
rank(F_Phi) >= beta_1
~~~

If this fails, GREMLIN must emit

~~~text
UNDERDETERMINED
~~~

for any source decomposition that requires the unresolved phase coordinates.

A small orbital residual cannot override this gate.

## 4. Known-sector subtraction gate

A candidate residual may be routed downstream only when all declared known-sector
contributors used in the subtraction have external constraints.

Examples:

- `rho(r)` constrained by imaging or another independent measurement;
- `g rho / m_B` constrained by Bogoliubov spectroscopy;
- `K_orb` constrained under its own source/coupling identifiability firewall;
- covariance/uncertainty model declared before the final source fit.

If the subtraction reuses the same observable both to fit and to "confirm" a
contributor, the packet is marked `circular_fit=true` and source attribution
fails closed.

## 5. Packet verdicts

The packet has three top-level consistency states.

### CONSISTENT

All supplied channel residuals are within their declared tolerance/covariance gate
and no structural model-consistency check is violated.

This means only:

~~~text
data are consistent with the declared model at the tested resolution
~~~

### INCONSISTENT

At least one supplied channel violates its declared gate, or a structural identity
such as the orbital/epicyclic consistency relation fails.

This rejects the declared combined model for that packet.

### UNDERDETERMINED

The supplied observations do not provide enough independent constraints to resolve
the declared latent coordinates or source decomposition.

This state takes precedence over source attribution even if the measured residual
norm is small.

## 6. Source-attribution firewall

The packet reports a separate boolean:

~~~text
source_attribution_admissible
~~~

which can be true only when:

1. phase identifiability is sufficient for the requested decomposition;
2. all known-sector subtraction inputs are independently constrained;
3. no circular fit is declared;
4. the residual is resolved above the declared uncertainty model;
5. all required source-specific binding gates are already admitted upstream.

Even when true, GREMLIN still returns a **candidate source family**, not a proven
physical origin.

## 7. Provenance requirements

Every channel must carry:

- repository;
- branch;
- exact commit SHA;
- schema or theorem identifier;
- validation/receipt locator;
- epistemic status.

The packet itself is content-addressable and suitable for PNCS/runtime transport,
but remains non-canonical until its source-owned parents are promoted.

## 8. Cross-repository links

- FPDG rollout:
  https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph/pull/22
- IDT 02JQ:
  https://github.com/AdrianLipa90/Informational-Dynamics-of-Time/pull/101
- Resonant Chemistry:
  https://github.com/AdrianLipa90/Resonant-Chemistry/pull/27
- OES:
  https://github.com/AdrianLipa90/Orbital-Eclipse-Spectroscopy/pull/14
- QHTRI phase optics:
  https://github.com/AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics/pull/1
- PhaseNav Telescope:
  https://github.com/AdrianLipa90/PhaseNav-Telescope-Spectral-Modulation/pull/24
- PNCS typed observation packet:
  https://github.com/AdrianLipa90/PhaseNav-Natural-Coding-System/pull/70
- noema-phasenav-core sidecar:
  https://github.com/AdrianLipa90/noema-phasenav-core/pull/35
- TIR:
  https://github.com/AdrianLipa90/The-Fundamental-Theory-of-Informational-Relations/pull/174
- RFC:
  https://github.com/AdrianLipa90/Relational-Field-Closure/pull/142

## 9. Non-promotions

This gate does not establish any of the following:

~~~text
W_chem = W_sem
U_I is a universal physical force
Phi_phase => g_(mu nu)
a physical BEC realization
~~~

Software PASS means that the packet logic is implemented as declared, not that a
new physical source has been observed.
