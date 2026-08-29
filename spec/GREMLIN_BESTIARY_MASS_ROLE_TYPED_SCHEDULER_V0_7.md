# GREMLIN Bestiary Mass-Role Typed Scheduler v0.7

Status: `CANDIDATE_ONLY / CHYBA / COMPATIBILITY_TYPED`

## Purpose

This layer operationalizes the v0.6 mass-role firewall without changing the current Bestiary cadence output.

The legacy scheduler accepts one overloaded `mass` coordinate:

\[
\omega=\omega_0\frac{\tau}{\sqrt{m r^3}}.
\]

v0.7 introduces an explicit role tuple

```text
mass_role_profile_id
mu_source
q_coupling
m_inertial
radius
```

and evaluates

\[
\boxed{
\omega^2
=\frac{\mu_{source}}{r^3}
\frac{q_{coupling}}{m_{inertial}}.
}
\]

There is no implicit/default mass-role profile. Unknown profiles fail closed.

## Current Bestiary compatibility profile

Profile ID:

`GREMLIN_BESTIARY_V02_INERTIAL_SERVICE_LOAD_COMPAT`

For each existing Bestiary species with legacy `(mass, radius)`, v0.7 maps

\[
\boxed{
\mu_{source}=(\omega_0\tau)^2,
\quad
q_{coupling}=1,
\quad
m_{inertial}=m_{legacy},
\quad
r=r_{legacy}.
}
\]

Then

\[
\omega_{typed}
=\omega_0\frac{\tau}{\sqrt{m_{legacy}r^3}}
=\omega_{legacy}
\]

up to floating-point evaluation order.

This preserves current service cadence while making the mass role explicit.

## Foundation compatibility profile

Profile ID:

`CIEL_FOUNDATION_P3_SOURCE_ATTRACTOR_COMPAT`

For historical Foundation

\[
T^2=\frac{r^3}{M_{sem}},
\]

v0.7 maps

\[
\boxed{
\mu_{source}=4\pi^2 M_{sem},
\quad
q_{coupling}=m_{inertial},
}
\]

which yields

\[
\omega=2\pi\sqrt{\frac{M_{sem}}{r^3}}.
\]

The numerical equality `q_coupling=m_inertial` is local to this compatibility profile and does not promote a universal physical equivalence principle.

## Explicit equivalence candidate profile

Profile ID:

`SEMANTIC_EQUIVALENCE_CANDIDATE`

This profile requires an externally supplied positive `mu_source`, positive `carrier_mass`, and positive radius and sets

\[
q_{coupling}=m_{inertial}=m_{carrier}.
\]

The resulting frequency is

\[
\omega^2=\frac{\mu_{source}}{r^3},
\]

independent of the carrier mass. The profile remains candidate-only until an independent source/charge equivalence receipt exists.

## Species compatibility requirement

The existing Bestiary species table remains unchanged. v0.7 is an adapter over the v0.2/v0.3 scheduler source, not a rewrite of species masses or radii.

For all nine current species, the typed compatibility frequency must match the legacy `service_omega` within numerical tolerance and preserve the cadence ordering.

## Scheduler output contract

A typed schedule witness records:

```text
species
mass_role_profile_id
mu_source
q_coupling
m_inertial
radius
tau
omega0
omega
period
legacy_omega | null
compatibility_residual | null
```

The role tuple is provenance-bearing. Downstream vector lane width, batching, and phase ordering may consume `omega`; they must not infer source/inertial/coupling roles from the scalar frequency alone.

## v0.3 radius inverse interaction

For `GREMLIN_BESTIARY_V02_INERTIAL_SERVICE_LOAD_COMPAT`, the earlier v0.3 inverse remains

\[
r=\left[\frac{(\omega_0\tau)^2}{m_I(2\pi/T)^2}\right]^{1/3}.
\]

For a general role tuple the correct inverse is

\[
\boxed{
r=\left[\frac{\mu_{source}q_{coupling}}{m_{inertial}\omega^2}\right]^{1/3}.}
\]

Thus future PNLF radius admission must record the exact `mass_role_profile_id` used to obtain the radius.

## Open gates

- bind current Bestiary legacy `mass` to an admitted PNCS semantic-mass record or rename it as service load;
- source-bind `mu_source` beyond compatibility constants;
- establish or falsify source-independence of `q_coupling/m_inertial`;
- connect role-typed orbit state to `O0..O8` through an explicit quantizer;
- validate role-typed frequency on live HTRI/QHTRI oscillator actuation.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
