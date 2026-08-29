# GREMLIN Semantic Orbital Mass-Role Firewall v0.6

Status: `CANDIDATE_ONLY / CHYBA / MASS_ROLE_SEPARATION_REQUIRED`

## Purpose

This gate prevents three historically distinct semantic-mass orbit laws from being collapsed into one overloaded `mass` coordinate.

The active dependency chain entering this gate is:

```text
C7 semantic orbital
 -> Newton/Einstein/AB candidate phase transport
 -> PNLF radius inverse (Bestiary-profile conditional)
 -> RFC source-density winding bridge
 -> current-live radial/angular factorization
 -> MASS ROLE FIREWALL
```

The v0.3 PNLF radius inverse remains an exact inverse of the current Bestiary scheduler, but its interpretation is restricted here to the Bestiary mass-role profile until a role-binding receipt is admitted.

## Source pins

### Current GREMLIN Bestiary scheduler

Repository: `AdrianLipa90/GREMLIN`

Bestiary parent head: `44d16d8a911c9871bbd1f7a44ba5a5e7f725d5de`

Native scheduler blob SHA: `63b967a656ef8db85890ac80934a8e0bc61f865f`

The native PNV declares:

```text
ORBIT.MASS SOURCE exact_semantic_mass_units
SCHEDULER_RELATION omega = omega0 * tau / sqrt(mass * radius^3)
SCHEDULER_RELATION_SCOPE INTERNAL_SERVICE_CADENCE
```

Hence

\[
\boxed{
\omega_B^2
=\frac{(\omega_0\tau)^2}{m_B r^3}.
}
\]

At fixed radius and flow parameter, this profile has `omega^2` mass exponent `-1` and period mass exponent `+1/2`.

### Historical CIEL Foundation semantic-mass implementation

Archive:

`CIEL-Omega-ApokalypOS-codex-ciel-sync-2026-05-12.zip`

Archive SHA-256:

`fef25a4cb20380483fec5b3e84ad8a2d1465e6a53ecf6dfd9ec42ec67d82e9ef`

Entry:

`src/ciel_geometry/semantic_mass.py`

Entry SHA-256:

`bd48c3ea201c2244d890fb010e836f227d56bb0a0b68f21d4499a79620327264`

The implementation computes

\[
\boxed{
T_F^2=\frac{a^3}{M_F}
}
\]

through `T_sq = a**3 / M_sem`, so

\[
\boxed{
\omega_F^2=\frac{4\pi^2 M_F}{a^3}.
}
\]

At fixed radius this profile has `omega^2` mass exponent `+1` and period mass exponent `-1/2`.

### Historical CIEL ObjectCard orbital prose/profile

The archived system report additionally records

\[
\boxed{T_C\propto m_C^{3/2}}
\]

for the ObjectCard holonomic phase-space layer, corresponding to

\[
\boxed{\omega_C^2\propto m_C^{-3}}.
\]

This profile is retained as a distinct historical role law. It is not silently identified with either Foundation P3 or current Bestiary cadence.

### Historical N-body source-role implementation

Library artifact: `nbody_gravity.py`

SHA-256:

`77f94b45af0d51dc17b6f80ceec7b1e8e17261a6217640aba0a58349be5f5396`

The implementation uses the standard source parameter

\[
\mu=GM
\]

and orbital period

\[
T=2\pi\sqrt{\frac{a^3}{\mu}}.
\]

Its two-body branch uses `M = central.mass + body.mass`; its semantic-table initializer also uses `M_sem` as a source mass for circular velocity.

## Generalized role equation

Introduce three separately typed positive coordinates:

- `mu_source` — source/attractor strength entering the inverse-square law;
- `q_coupling` — coupling/gravitational charge of the orbiting carrier;
- `m_inertial` — inertial load of the orbiting carrier.

For circular balance

\[
\frac{\mu_{S}q_G}{r^2}
=m_I r\omega^2,
\]

therefore

\[
\boxed{
\omega^2
=\frac{\mu_S}{r^3}\frac{q_G}{m_I}.
}
\]

Define

\[
\boxed{\eta_G:=\frac{q_G}{m_I}.}
\]

Then

\[
\boxed{
\omega^2=\frac{\mu_S\eta_G}{r^3}.
}
\]

This is the role-separated kernel of the present gate.

## Profile embeddings

### Bestiary internal service-cadence profile

The current Bestiary scheduler is reproduced exactly by

\[
\boxed{
\mu_S=(\omega_0\tau)^2,
\qquad
q_G=1,
\qquad
m_I=m_B.
}
\]

Thus, under this embedding, the Bestiary `semantic mass` occupies an **inertial/service-load role**.

This is an exact algebraic embedding of the current scheduler. It is not a physical equivalence-principle claim.

### Foundation P3 profile

The Foundation law is reproduced exactly by

\[
\boxed{
\mu_S=4\pi^2M_F,
\qquad
\eta_G=1.
}
\]

For example one may choose any positive `m_I=q_G`; the ratio cancels. Under this embedding, Foundation `M_sem` occupies a **source/attractor role**.

### N-body profile

The historical N-body implementation realizes

\[
\boxed{
\mu_S=G(M_1+M_2),
\qquad
\eta_G=1
}
\]

for relative two-body orbital elements.

### ObjectCard profile

If `T_C \propto m_C^{3/2}`, then

\[
\omega_C^2\propto m_C^{-3}.
\]

A fixed-source profile with `m_I=m_C` and constant `q_G` gives only `m_C^{-1}`. Therefore matching the ObjectCard exponent requires an additional mass-dependent source/coupling factor with net exponent `-2`:

\[
\boxed{
\mu_S q_G\propto m_C^{-2}
}
\]

when `m_I=m_C`.

The source/coupling law supplying that exponent is not present in the admitted source set for this gate, so the ObjectCard profile remains `ROLE_SOURCE_UNRESOLVED`.

## Equivalence branch

If a later admitted source law establishes

\[
q_G=m_I,
\]

then

\[
\boxed{
\eta_G=1,
\qquad
\omega^2=\frac{\mu_S}{r^3},
}
\]

and the orbiting test-carrier mass cancels from circular acceleration.

This is a conditional algebraic branch. Physical promotion requires an independent source/charge equivalence receipt.

## Consequence for semantic orbitals

The semantic orbital state must carry role labels rather than one untyped mass slot when it crosses between scheduler, memory, and physical-law layers:

```text
semantic_mass_realization  : PNCS realization/integrity coordinate
source_mass_or_mu          : attractor/source role
inertial_mass              : orbiting load role
coupling_charge            : source-coupling role
mass_role_profile_id       : exact mapping provenance
```

A numerical equality between two of these fields does not establish role identity.

## v0.3 reinterpretation firewall

The v0.3 inverse

\[
r=\left[\frac{(\omega_0\tau)^2}{m(2\pi/T)^2}\right]^{1/3}
\]

remains mathematically exact for the current Bestiary scheduler. After this gate it is typed as:

```text
Bestiary internal service-cadence inverse
```

until an admitted profile explicitly binds PNCS `semantic_mass` into the Bestiary inertial/service-load role.

## Promotion requirements

1. Freeze a `mass_role_profile_id` for every scheduler/orbital consumer.
2. Source-bind Bestiary `ORBIT.MASS` to a specific PNCS semantic-mass binding or rename it to a service-load coordinate.
3. Source-bind `mu_source` to an admitted attractor/source quantity.
4. Source-bind `q_coupling/m_inertial` and test whether `eta_G` is source-independent.
5. Reconcile or retire the historical ObjectCard `T proportional m^(3/2)` profile with an explicit source/coupling law.
6. Re-run PNLF radius admission after mass-role typing is frozen.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
