# GREMLIN Semantic Orbital Newton-Einstein-AB Bridge v0.2

Status: `CANDIDATE_ONLY / CHYBA / SOURCE_GATED`

Parent: `GREMLIN_SEMANTIC_ORBITAL_IMAGINARY_REAL_BRIDGE_V0_1`.

## Core decomposition

The candidate separates radial/cadence structure from oriented phase transport.

The Bestiary scheduler is written in exact Kepler form through

\[
\mu_{\rm sem}:=\frac{(\omega_0\tau)^2}{m_{\rm sem}},
\qquad
\boxed{\omega_K^2=\frac{\mu_{\rm sem}}{r^3}}.
\]

The associated Newton-form circular carrier uses

\[
V_N(r)=-\frac{\mu_{\rm sem}}{r},
\qquad
\ell_K^2=\mu_{\rm sem}r,
\qquad
T_K=\frac{2\pi}{\omega_K}.
\]

These equations define the radial/cadence branch of this candidate.

## Oriented phase branch

A rotating reference frame contributes the per-orbit phase

\[
\boxed{\tau_{\rm rot}=-\Omega_{\rm rot}T_K.}
\]

On the declared weak-field nearly-circular relativistic candidate surface, define the apsidal phase increment

\[
\boxed{\tau_{\rm GR}=\frac{6\pi\mu_{\rm sem}}{r c^2}.}
\]

A declared connection/path source supplies an Aharonov-Bohm-type holonomy input

\[
\boxed{\tau_{\rm AB}}.
\]

The total oriented transport is

\[
\boxed{\tau_{\rm total}=\tau_{\rm rot}+\tau_{\rm GR}+\tau_{\rm AB}.}
\]

Because the phase group is `U(1)`, the same transport can be written multiplicatively:

\[
e^{i\tau_{\rm total}}
=e^{i\tau_{\rm rot}}e^{i\tau_{\rm GR}}e^{i\tau_{\rm AB}}.
\]

## Imaginary-real bridge

For

\[
z_a=m_a^{\rm sem}e^{i\phi_a},
\]

transport gives

\[
\boxed{z_a' = z_a e^{i\tau_a}.}
\]

For two semantic orbitals,

\[
(z_a')^*z_b'
=m_am_b e^{i(\Delta\phi_{ab}+\Delta\tau_{ab})},
\]

and the real relational channel is

\[
\boxed{
X_{ab}
=\operatorname{Re}[(z_a')^*z_b']
=m_am_b\cos(\Delta\phi_{ab}+\Delta\tau_{ab}).
}
\]

Thus the complex carrier retains orientation and accumulated holonomy while the declared Hermitian/real contraction supplies a real relational value.

## Semantic carrier law

The parent semantic law remains

\[
\mathcal S(t)
=\frac{B(t)\omega(t)N(t)}{A_R(t)}(\tilde\phi(t)+\kappa),
\qquad
\kappa=\frac{\ln2}{24\pi}.
\]

On this candidate branch the transported lifted phase is

\[
\boxed{\tilde\phi' = \tilde\phi+\tau_{\rm total}.}
\]

Therefore

\[
\boxed{
\mathcal S'
=\frac{B\omega N}{A_R}(\tilde\phi+\tau_{\rm total}+\kappa).
}
\]

`B`, `N`, `A_R`, semantic orbital radius ownership, and the physical source ownership of each phase contribution remain explicit source gates.

## Bestiary assignment

- `SPIDER`: checks radial/cadence and phase-transport dependency graph.
- `RAVEN`: checks Newton/Kepler and weak-field relativistic structural relations.
- `HOUND`: enforces domain, winding, units and source ownership.
- `MOLE`: carries the complex orbital and differential holonomy relation.
- `OWL`: separates exact algebraic closure from source-dependent physical attribution.
- `ANT`: retains alternate relativistic/rotating-frame parameterizations as typed candidates.
- `MANTIS`: prunes double-counting of phase corrections and phase erasure before projection.
- `BELZEBUB`: aggregates the candidate only after all exact identities close.

## Epistemic ledger

Exact within the declared mathematical candidate:

- `omega_K^2 = mu_sem/r^3` from the existing Bestiary scheduler reparameterization;
- `ell_K^2 = mu_sem*r` on the Newton circular branch;
- additive/multiplicative equivalence of `U(1)` phase transport;
- cancellation of a common transport phase from pair relations;
- real-valued Hermitian projection.

Source-gated candidate surfaces:

- weak-field apsidal phase assignment to the semantic orbital branch;
- rotating-frame ownership of `Omega_rot`;
- AB connection/path ownership of `tau_AB`;
- physical interpretation of `mu_sem`.

The repository may suggest a physical Newton-Einstein-AB interpretation of these semantic orbitals, yet does not state that interpretation as an established result until the source-binding gates pass with frozen provenance.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
