# GREMLIN Bestiary Mass-Role Typed Scheduler v0.7

Status: `CANDIDATE_ONLY / CHYBA / COMPATIBILITY_TYPED / HISTORICAL_ROLE_CROSSWALK_ATTACHED`

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

## Historical CIEL inertial-simulation compatibility profile

Profile ID:

`CIEL_KEPLER_INERTIAL_SIM_COMPAT`

Historical source:

```text
archive:
  CIEL-Omega-ApokalypOS-codex-ciel-sync-2026-05-12.zip
archive_sha256:
  fef25a4cb20380483fec5b3e84ad8a2d1465e6a53ecf6dfd9ec42ec67d82e9ef
entry:
  scripts/sims/kepler_ciel_sim.py
entry_sha256:
  d7b5cea2673bea6979bd7a99077d90d7e9f84ae010b6c5cd2d9fa1ac704f8581
```

The archived simulation initializes the circular speed through

\[
\boxed{
v_{circ}^2=\frac{k}{M_{sem}r}
}
\]

and therefore

\[
\boxed{
\omega^2=\frac{k}{M_{sem}r^3}.
}
\]

v0.7 realizes this exactly with

\[
\boxed{
\mu_{source}=k,
\quad
q_{coupling}=1,
\quad
m_{inertial}=M_{sem}.
}
\]

Thus this historical simulation and the current Bestiary scheduler place their respective semantic-mass coordinate in the same **inertial/service-load role**.

This is an exact source crosswalk. It does not identify the historical numeric mass scale with the current PNCS mass scale.

## Foundation compatibility profile

Profile ID:

`CIEL_FOUNDATION_P3_SOURCE_ATTRACTOR_COMPAT`

The same historical archive independently contains `src/ciel_geometry/semantic_mass.py`, SHA-256

```text
bd48c3ea201c2244d890fb010e836f227d56bb0a0b68f21d4499a79620327264
```

with the stored period law

\[
T^2=\frac{r^3}{M_{sem}}.
\]

v0.7 maps this distinct branch as

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

The historical archive therefore contains two opposite semantic-mass responses at fixed radius:

```text
CIEL_KEPLER_INERTIAL_SIM_COMPAT
    T^2 proportional +M_sem

CIEL_FOUNDATION_P3_SOURCE_ATTRACTOR_COMPAT
    T^2 proportional 1/M_sem
```

v0.7 preserves them as different typed profiles. A profile switch is a role change rather than a normalization retune.

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

For `CIEL_KEPLER_INERTIAL_SIM_COMPAT`, the same role-separated inverse is

\[
\boxed{
r=\left[\frac{k}{M_{sem}(2\pi/T)^2}\right]^{1/3}.}
\]

For a general role tuple the correct inverse is

\[
\boxed{
r=\left[\frac{\mu_{source}q_{coupling}}{m_{inertial}\omega^2}\right]^{1/3}.}
\]

Generic `semantic_mass + orbit_period` values therefore do not establish a Bestiary radius source binding by themselves.

## PNLF compatibility boundary

PNLF v0.1 already carries the model/profile identifiers

```text
mass_model_id
orbit_quantizer_id
proper_time_model_id
```

and deliberately leaves geometry-to-band realization to an explicit `orbit_quantizer_id` profile.

v0.7 does **not** introduce a new PNLF field. Instead, the scheduler-side

```text
mass_role_profile_id
```

must be preserved by an explicit PNLF compatibility/quantizer profile or an explicit lineage/profile transition that binds the PNLF record to the typed scheduler realization used to compute its period/radius.

Accordingly, future PNLF radius admission requires provenance sufficient to recover the exact role tuple. A numeric `semantic_mass` and `orbit_period` pair without that profile binding fails closed.

## Historical orbital-shell firewall

The archived `orbital_shell.py`, SHA-256

```text
8d57507edfa1060fe825e10d93ef7d9a6bc63738cddd67c182f81dbdb9796990
```

uses a separate coordinate family based on `r_phase`, `E_bind`, and shell `0..8`. This does not identify scheduler radius with `r_phase`. A crosswalk requires an explicit `orbit_quantizer_id`.

## Open gates

- bind current Bestiary legacy `mass` to an admitted PNCS semantic-mass record or rename it as service load;
- source-bind `mu_source` beyond compatibility constants;
- establish or falsify source-independence of `q_coupling/m_inertial`;
- bind `mass_role_profile_id` into a PNLF compatibility/quantizer lineage without changing the PNLF v0.1 schema;
- connect role-typed orbit state to `O0..O8` through an explicit quantizer;
- validate role-typed frequency on live HTRI/QHTRI oscillator actuation.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
