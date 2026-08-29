# GREMLIN Semantic Orbital RFC Source-Density Bridge v0.4

Status: `CANDIDATE_ONLY / CHYBA / EXACT_STRUCTURAL_CROSSWALK`

## Parent sources

This gate consumes:

- GREMLIN semantic orbital C7 / lifted-phase bridge v0.1;
- GREMLIN Newton-Einstein-AB bridge v0.2;
- GREMLIN PNLF radius inverse v0.3;
- RFC `main` head `6001960e7d2dde60765bc110fc7d2c532b79b531`, specifically RF-S13 `Relational Generator Source-Density Binding`.

RF-S13 carries the relational generator

\[
\boxed{
\mathcal G(t)
=\frac{B(t)\,\omega(t)\,\mathcal N(t)}{A(t)R(t)}
\bigl(\phi(t)+\kappa\bigr),
\qquad
\kappa=\frac{\ln2}{24\pi}.
}
\]

Here `AR` is the product `A*R`, with `[A]=L^2` and `[R]=L`; it is not a single field named `A_R`.

RF-S13 types

\[
V_R:=AR,
\qquad
n_R:=\frac{\mathcal N}{AR},
\qquad
\epsilon_\Psi:=B\omega(\phi+\kappa),
\]

and therefore

\[
\boxed{
\rho_E=n_R\epsilon_\Psi=\mathcal G.
}
\]

The present GREMLIN gate does not replace those RFC definitions. It binds them to the winding-aware semantic orbital coordinates.

## C7 universal lift

Let

\[
\delta_7:=\frac{2\pi}{7},
\qquad
n\in\{0,1,\ldots,6\},
\qquad
w\in\mathbb Z.
\]

The lifted semantic phase is

\[
\boxed{
\tilde\phi_{n,w}
=\phi_0-n\delta_7+2\pi w.
}
\]

Define the integer lift coordinate

\[
\boxed{q:=7w-n\in\mathbb Z.}
\]

Then exactly

\[
\boxed{
\tilde\phi_q=\phi_0+q\delta_7.
}
\]

The pair `(n,w)` with `n in 0..6` is a unique representation of the integer lift coordinate `q`.

## Imaginary / complex orbital channel

For semantic mass `m_sem>0`, define

\[
\boxed{z_q=m_{\rm sem}e^{i\tilde\phi_q}.}
\]

Because `7 delta_7 = 2 pi`,

\[
\boxed{z_{q+7}=z_q.}
\]

Thus the complex orbital retains the C7 orientation while quotienting full turns in the exponential phase.

## Real source-density channel

On the RF-S13 typed source branch, replace the linear phase coordinate by the explicitly lifted coordinate:

\[
\boxed{
\rho_E(q)
=Q\bigl(\tilde\phi_q+\kappa\bigr),
\qquad
Q:=\frac{B\omega\mathcal N}{AR}.
}
\]

For fixed `B,omega,N,A,R`, adjacent integer-lift states satisfy

\[
\boxed{
\rho_E(q+1)-\rho_E(q)=Q\frac{2\pi}{7}.
}
\]

A full C7 turn satisfies

\[
\boxed{
\rho_E(q+7)-\rho_E(q)=2\pi Q.
}
\]

Therefore the complex orbital and the linear RFC source coordinate carry complementary information:

```text
complex orbital exp(i*phi_lift) -> C7 orientation modulo 2*pi
RFC source density              -> lifted phase / winding coordinate
```

This is an exact structural bridge on the declared source branch.

## Winding firewall

Because the source law is linear in phase, `w` is not discardable metadata on this branch. Replacing `phi_lift` by `wrap(phi_lift)` changes `rho_E` by integer multiples of `2*pi*Q`.

Accordingly:

```text
wrapped_phase_only source density -> REJECT
lifted_phase + winding source      -> ADMISSIBLE CANDIDATE
```

This statement is local to the linear semantic-generator branch. It does not declare winding to be a universal observable for every PhaseNav operator.

## Source sign

The gate does not impose a positive-energy condition. The sign of

\[
\rho_E=Q(\tilde\phi+\kappa)
\]

depends on the admitted source values and lift. A later physical-source gate must specify any positivity, boundedness, or reference-zero condition.

## RFC Newton/Einstein crosswalk

RF-S13 independently records

\[
\rho_m=\frac{\rho_E}{c^2},
\qquad
\mathcal S_R=\frac{\kappa_E}{2}\rho_E.
\]

The present gate therefore transports the winding-aware source density into those already-typed RFC source slots without changing their normalization.

## Open physical gates

- physical realization of the action carrier `B`;
- physical occupation/current receipt for `N`;
- physical `A*R` relational cell-volume receipt;
- source relation between `semantic_mass` and the RFC energy/mass density ledger;
- physical choice of winding/reference-zero branch;
- project-side absolute `kappa_E/G` promotion;
- HTRI/QHTRI actuation binding.

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
