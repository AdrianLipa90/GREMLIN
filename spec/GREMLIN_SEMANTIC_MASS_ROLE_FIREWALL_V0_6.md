# GREMLIN Semantic Mass-Role Firewall v0.6

Status: `PASS_EXACT_MASS_ROLE_SEPARATION / HISTORICAL_PERIOD_ROLE_CONFLICT_FOUND / PNLF_PERIOD_PROFILE_GATE_REQUIRED / CANDIDATE_ONLY`

Authority:

```text
epistemic                    = CHYBA
promotion_state              = CANDIDATE_ONLY
runtime_execution_authority  = false
canon_write_authority        = false
```

## 1. Purpose

This gate prevents one scalar named `semantic_mass` from silently occupying incompatible dynamical roles.

The current Bestiary scheduler, historical CIEL Kepler simulation, historical Foundation-P3 stored period, and historical ObjectCard cadence use different mass exponents. v0.6 makes those roles explicit before any PNLF orbital-period value is used to reconstruct scheduler radius.

## 2. Typed circular-orbit seam

Define positive typed coordinates

\[
\Lambda>0,\qquad \tau>0,\qquad
Q_{\rm src}>0,\qquad Q_{\rm orb}>0,\qquad
m_{\rm in}>0,\qquad r>0.
\]

The candidate circular scheduling law is

\[
\boxed{
\omega^2
=
(\Lambda\tau)^2
\frac{Q_{\rm src}Q_{\rm orb}}
{m_{\rm in}r^3}
}
\]

with period

\[
\boxed{
T=\frac{2\pi}{\omega}.
}
\]

The three roles are distinct:

```text
Q_src   source / attractor coupling charge
Q_orb   orbiting coupling charge
m_in    inertial / workload load coordinate
```

This is a typed internal scheduling/crosswalk law. Physical promotion requires a separate source/coupling realization.

## 3. Exact current Bestiary realization

Current Bestiary v0.2 records

\[
\boxed{
\omega
=
\omega_0\frac{\tau}{\sqrt{m_{\rm sem}r^3}}.
}
\]

It is recovered exactly by

\[
\Lambda=\omega_0,\qquad
Q_{\rm src}=1,\qquad
Q_{\rm orb}=1,\qquad
m_{\rm in}=m_{\rm sem}.
\]

Therefore

\[
\boxed{
T^2
=
\frac{4\pi^2}{(\omega_0\tau)^2}
m_{\rm sem}r^3.
}
\]

So on the Bestiary branch the semantic mass occupies the `INERTIAL_LOAD` role.

Source pin:

```text
GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2.pnv
git blob: 63b967a656ef8db85890ac80934a8e0bc61f865f
scope: INTERNAL_SERVICE_CADENCE
```

## 4. Historical CIEL inertia branch

Historical `scripts/sims/kepler_ciel_sim.py` uses

```text
v_circ^2 = k / (M_sem * r)
```

and therefore

\[
\boxed{
\omega^2=\frac{k}{M_{\rm sem}r^3}.
}
\]

This is the same mass role as the current Bestiary branch:

\[
\Lambda=\sqrt{k},\qquad
\tau=1,\qquad
Q_{\rm src}=Q_{\rm orb}=1,\qquad
m_{\rm in}=M_{\rm sem}.
\]

Historical source SHA-256:

```text
d7b5cea2673bea6979bd7a99077d90d7e9f84ae010b6c5cd2d9fa1ac704f8581
```

## 5. Historical Foundation-P3 stored-period conflict

The historical `src/ciel_geometry/semantic_mass.py` independently stores

\[
\boxed{
T^2=\frac{r^3}{M_{\rm sem}}.
}
\]

This has the opposite mass exponent from the inertia branch.

For fixed radius:

```text
inertial-load branch:   T^2 proportional M_sem^(+1)
source-strength branch: T^2 proportional M_sem^(-1)
```

Thus these cannot be the same typed role with only a normalization change.

Historical source SHA-256:

```text
bd48c3ea201c2244d890fb010e836f227d56bb0a0b68f21d4499a79620327264
```

The v0.6 verdict is therefore:

\[
\boxed{
\text{historical semantic-mass role overload existed.}
}
\]

The current Bestiary relation agrees with the historical inertia simulation branch, while the old stored Foundation-P3 period belongs to a distinct source-strength branch.

## 6. Historical ObjectCard cadence is a third profile

Historical ObjectCard documentation records

\[
T\propto m^{3/2},
\]

hence

\[
T^2\propto m^3.
\]

This is retained as a separate `OBJECTCARD_CADENCE` profile. v0.6 does not lower it into the typed circular law by inventing nonlinear source or inertia mappings.

## 7. Mass-exponent diagnostic

Let

\[
T^2\propto m^\xi r^3.
\]

Then v0.6 uses the exact diagnostic:

| profile | \(\xi\) |
|---|---:|
| `INERTIAL_LOAD` | \(+1\) |
| `SOURCE_STRENGTH` | \(-1\) |
| `EQUIVALENCE_CANCELLED` | \(0\) |
| `OBJECTCARD_CADENCE` | \(+3\) |

A profile switch that changes \(\xi\) is a type change, not a parameter retuning.

## 8. PNLF correction to v0.3

PNLF v0.1 stores both

```text
semantic_mass
orbit_period
mass_model_id
orbit_quantizer_id
proper_time_model_id
```

and deliberately does not hard-code one universal orbital quantizer.

Therefore the v0.3 inverse formula

\[
r=
\left[
\frac{(\omega_0\tau)^2}
{m(2\pi/T)^2}
\right]^{1/3}
\]

remains algebraically exact only when the incoming PNLF record is explicitly bound to the Bestiary-compatible `INERTIAL_LOAD` period model.

Generic

```text
PNLF.semantic_mass + PNLF.orbit_period
```

is insufficient source evidence.

v0.6 requires an explicit admitted period-model identifier, for example

```text
GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2
CIEL_KEPLER_INERTIAL_SIM_COMPAT
```

before the v0.3 inverse is admitted.

For the distinct source-strength branch

\[
T^2=\frac{r^3}{M_{\rm src}},
\]

the inverse is instead

\[
\boxed{
r=(M_{\rm src}T^2)^{1/3}.
}
\]

Using one inverse formula on the other branch reverses the mass dependence.

## 9. Historical orbital-shell firewall

Historical `orbital_shell.py` carries another independent coordinate family:

\[
E_{\rm bind}=-\frac{G_{\rm sem}M_{\rm att}}{r_{\rm phase}^2},
\]

with shell `0..8` derived from `r_phase`.

Source SHA-256:

```text
8d57507edfa1060fe825e10d93ef7d9a6bc63738cddd67c182f81dbdb9796990
```

This does not identify scheduler radius with `r_phase`. A future shell crosswalk must carry an explicit `orbit_quantizer_id`.

## 10. Promotion ledger

```text
current Bestiary -> INERTIAL_LOAD role                 PASS EXACT
historical kepler_ciel_sim -> INERTIAL_LOAD role       PASS EXACT
historical semantic_mass.py stored period              PASS EXACT SOURCE_STRENGTH
historical opposite mass exponents identified          PASS EXACT
ObjectCard T~m^(3/2) kept as separate cadence profile  PASS TYPE FIREWALL
generic PNLF period -> Bestiary inverse                 BLOCKED FAIL CLOSED
explicit compatible PNLF period model -> v0.3 inverse  ADMISSIBLE
physical mass / gravitational mass identification      OPEN SEPARATE GATE
GREMLIN native KAKU authoring                           BLOCKED: LIVE WITNESS ABSENT
```

## 11. Provenance

Historical archive SHA-256:

```text
fef25a4cb20380483fec5b3e84ad8a2d1465e6a53ecf6dfd9ec42ec67d82e9ef
```

PNCS/PNLF reference head:

```text
7a54596c1794be29e0b85f5c363213cc81eb87d7
```

PNLF contract Git blob:

```text
6f81da701697ade117ece9ff6c3f4d684b38d51c
```

Live NOEMA receipt:

```text
/dev/shm/ciel_noema/session/gremlin_semantic_mass_role_firewall_live_v0_6.json
```

The live receipt is candidate-only and records the absence of a live GREMLIN authoring witness; no vector/KAKU realization is guessed.
