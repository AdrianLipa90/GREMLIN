# GREMLIN Semantic Orbital Imaginary-Real Bridge v0.1

Status: `CANDIDATE_ONLY / CHYBA / SOURCE_GATED`

## Scope

This candidate binds the live PhaseNav semantic orbit classes to a complex orbital carrier while preserving the existing GREMLIN authority firewall. It does not grant runtime execution authority or canon-write authority.

The live PhaseNav orbit vectors currently occupy four observed classes on a sevenfold phase lattice.

Let

\[
\delta_7:=\frac{2\pi}{7},
\qquad
\phi_n=\phi_0-n\delta_7,
\qquad n\in\mathbb Z_7.
\]

On the live `/dev/shm/ciel_noema` surface used for the v0.2 audit, the observed indices are

\[
\boxed{n\in\{0,1,2,3\}},
\]

with indices `4,5,6` presently unoccupied by the 115 loaded concept cards. Unoccupied is an occupancy statement only.

The reference class is `Resonance`, with serialized phase anchor

\[
\phi_0=-2.84156\ \mathrm{rad}.
\]

The orbit-vector source yields, for the `Intention` class,

\[
\operatorname{wrap}\!\left(\phi_0-3\frac{2\pi}{7}\right)
=0.748831604387\ldots
\]

while the older concept-phase metadata contains `0.748729`. In this gate the orbit-vector lattice is the phase source and the old metadata field is treated as a stale derived field for that class.

## Semantic law and phase lift

The supplied semantic carrier law is

\[
\boxed{
\mathcal S(t)
=\frac{B(t)\,\omega(t)\,N(t)}{A_R(t)}\bigl(\tilde\phi(t)+\kappa\bigr)
}
\]

with

\[
\kappa=\frac{\ln2}{24\pi}.
\]

Because this law is linear in phase, the phase coordinate must be lifted:

\[
\boxed{\tilde\phi=\phi+2\pi w,\qquad w\in\mathbb Z.}
\]

A wrapped phase alone is insufficient: changing the representative by `2*pi` changes the linear semantic carrier unless winding is retained explicitly.

Define the source factor

\[
Q_{BNA}:=\frac{BN}{A_R},
\]

so that

\[
\mathcal S=Q_{BNA}\,\omega\,(\tilde\phi+\kappa).
\]

`B`, `N`, and `A_R` remain source-gated in this candidate.

## Complex semantic orbital

For a semantic mass coordinate `m_sem` and orbital orientation `phi`, define the candidate complex carrier

\[
\boxed{z_a=m_a^{\rm sem}e^{i\phi_a}.}
\]

The pair carrier is

\[
\boxed{z_a^*z_b=m_am_b e^{i(\phi_b-\phi_a)}.}
\]

Its real Hermitian projection is

\[
\boxed{
\operatorname{Re}(z_a^*z_b)
=m_am_b\cos(\Delta\phi_{ab}).
}
\]

This retains the imaginary quadrature as orientation information until the declared real/Hermitian projection is evaluated.

A common global phase cancels:

\[
(e^{i\alpha}z_a)^*(e^{i\alpha}z_b)=z_a^*z_b.
\]

## Holonomy transport

For a declared path/connection holonomy `tau_a`, phase transport is

\[
\phi_a\mapsto\phi_a+\tau_a.
\]

Therefore the pair carrier transforms as

\[
\boxed{
z_a^*z_b
\mapsto
z_a^*z_b\,e^{i(\tau_b-\tau_a)}.
}
\]

A common holonomy cancels. Differential holonomy remains observable through the relative complex phase. The physical AB/source attribution of `tau` remains a separate connection/path gate.

## Mass-orbit / Kepler-form isomorphism

The current Bestiary scheduler v0.2/v0.3 uses

\[
\omega
=\omega_0\frac{\tau}{\sqrt{m r^3}},
\qquad
\omega_0=2\pi\cdot7.83.
\]

Define

\[
\boxed{\mu_{\rm sem}:=\frac{(\omega_0\tau)^2}{m}.}
\]

Then identically

\[
\boxed{\omega^2=\frac{\mu_{\rm sem}}{r^3}.}
\]

This is an exact algebraic Kepler-form reparameterization of the internal scheduler. `mu_sem` is not identified here with `G*M` or with a physical gravitational parameter.

## Bestiary decomposition

- `SPIDER`: verify the `C7` lattice and class occupancy.
- `RAVEN`: track the exact Kepler-form isomorphism and crosslinks to rotation/relativity candidates.
- `HOUND`: enforce lifted-phase and source-attribution firewalls.
- `MOLE`: construct the complex radial-orientation carrier.
- `OWL`: separate exact algebraic identities from physical-source claims.
- `ANT`: retain alternate radial embeddings as candidates rather than silently promoting them.
- `MANTIS`: prune direct deletion of `i`, modulus-only bridges, wrapped-phase-only semantic laws, and unsourced `mu_sem = G*M` identifications.
- `BELZEBUB`: aggregate only the source-typed candidate kernel.

## Promotion gates

1. Source-bind `B(t)`, `N(t)`, and `A_R(t)`.
2. Bind the semantic orbital radius/band coordinate to the scheduler radius without guessing.
3. Derive rotation/Einstein corrections as typed phase or Hamiltonian terms.
4. Bind AB holonomy from a declared connection/path source.
5. Validate the semantic carrier against HTRI/QHTRI actuation without identifying `Q_BNA` with an actuation budget by fiat.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
