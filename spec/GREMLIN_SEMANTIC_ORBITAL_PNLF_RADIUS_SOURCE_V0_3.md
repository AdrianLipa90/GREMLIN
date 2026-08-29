# GREMLIN Semantic Orbital PNLF Radius Source v0.3

Status: `CANDIDATE_ONLY / CHYBA / LIVE_SOURCE_PENDING`

## Purpose

This gate source-binds the Bestiary scheduler radius to the existing PNLF orbital-memory coordinates without identifying the scheduler radius with `r_phase`.

The upstream PNLF contract carries, among other coordinates:

- `semantic_mass`;
- `orbit_period`;
- `r_phase`;
- `E_bind`;
- `L_phase`;
- `winding`;
- `proper_time`;
- `mass_model_id` and `orbit_quantizer_id`.

For this gate, `semantic_mass` and `orbit_period` are the only PNLF coordinates consumed by the inverse-radius theorem. `r_phase`, `E_bind`, and `L_phase` remain separately typed coordinates.

## Parent scheduler

The Bestiary scheduler uses

\[
\omega=\omega_0\frac{\tau}{\sqrt{m r^3}},
\qquad
T=\frac{2\pi}{\omega}.
\]

For finite positive `m`, `T`, `tau`, and `omega0`, this map is invertible in `r`:

\[
\boxed{
r=\left[
\frac{(\omega_0\tau)^2}
{m(2\pi/T)^2}
\right]^{1/3}
}.
\]

Equivalently,

\[
\boxed{
r=\left[
\frac{(\omega_0\tau T)^2}
{4\pi^2m}
\right]^{1/3}.
}
\]

Thus a PNLF checkpoint carrying a positive `semantic_mass` and positive `orbit_period`, together with the declared scheduler/proper-time profile for `tau`, determines one scheduler radius without a free radius parameter.

## Domain firewall

PNLF permits non-negative semantic mass. The present scheduler inverse requires strictly positive mass. Therefore:

```text
semantic_mass == 0 -> FAIL_CLOSED_FOR_SCHEDULER_RADIUS_BINDING
```

This is a scheduler-domain restriction and does not change the PNLF storage contract.

## Coordinate typing

The following identifications are not made by this gate:

```text
scheduler_radius != r_phase by declaration
scheduler_radius != E_bind by declaration
scheduler_radius != L_phase by declaration
scheduler_radius != orbital_band by declaration
```

Any later relation among those coordinates requires an explicit profile/theorem and receipt.

## Round-trip theorem

Define

\[
\omega(r,m)=\omega_0\tau/\sqrt{mr^3},
\qquad
T(r,m)=2\pi/\omega(r,m).
\]

Then on the positive domain:

\[
\boxed{R(m,T(r,m),\tau,\omega_0)=r}
\]

and

\[
\boxed{T(R(m,T,\tau,\omega_0),m)=T}.
\]

The implementation validates both directions numerically.

## Live source status

On the live `/dev/shm/ciel_noema` surface used for this gate, 22 JSON/JSONL files were scanned and zero `orbit_period` records were present. Therefore the theorem is executable and testable, while live PNLF radius admission remains `SOURCE_PENDING` until an admitted checkpoint provides the required fields.

Live receipt:

`/dev/shm/ciel_noema/session/gremlin_semantic_orbital_pnlf_radius_source_live_v0_3.json`

File SHA-256:

`c13a02900c0c10d6e7c3b8855579785286bacb4a0f4c82eb912aad6905db92c9`

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
