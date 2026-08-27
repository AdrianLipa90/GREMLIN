# GREMLIN Hermitian Oriented Exchange v1.4

Status: `CANDIDATE / RESEARCH_BINDING_ONLY`

## Purpose

v1.4 gives the v1.3 oriented relational coupling a parameter-free Hermitian operator embedding for a two-state exchange sector.

The bound lineage is

`Lambda_R -> E_R -> connection holonomy tau -> J_complex=E_R exp(i tau) -> H_ex -> unitary exchange evolution`.

## Oriented coupling input

v1.3 supplies

\[
\mathcal J_R
=E_Re^{i\tau}
=J_R^{(x)}+iJ_R^{(y)},
\]

with

\[
J_R^{(x)}=E_R\cos\tau,
\qquad
J_R^{(y)}=E_R\sin\tau,
\qquad
|\mathcal J_R|=|E_R|.
\]

## Hermitian exchange operator

On the ordered basis

\[
(|00\rangle,|01\rangle,|10\rangle,|11\rangle),
\]

define

\[
\boxed{
H_{\rm ex}
=\mathcal J_R|01\rangle\langle10|
+\mathcal J_R^*|10\rangle\langle01|.
}
\]

Its matrix is

\[
H_{\rm ex}
=
\begin{pmatrix}
0&0&0&0\\
0&0&\mathcal J_R&0\\
0&\mathcal J_R^*&0&0\\
0&0&0&0
\end{pmatrix}.
\]

Hermiticity follows directly from the conjugate off-diagonal pair.

The same operator can be written

\[
\boxed{
H_{\rm ex}
=\frac{\operatorname{Re}\mathcal J_R}{2}(X\otimes X+Y\otimes Y)
+\frac{\operatorname{Im}\mathcal J_R}{2}(X\otimes Y-Y\otimes X).
}
\]

Thus the v1.3 orientation quadrature `E_R sin(tau)` enters an explicit Hermitian operator component.

## Spectrum

In the single-excitation sector the Hamiltonian is

\[
\begin{pmatrix}
0&\mathcal J_R\\
\mathcal J_R^*&0
\end{pmatrix},
\]

so its eigenvalues are

\[
\boxed{\lambda_\pm=\pm|\mathcal J_R|=\pm|E_R|.}
\]

The `|00>` and `|11>` sectors carry eigenvalue zero. The spectral radius therefore closes to `|E_R|`.

## Exact unitary evolution

Let

\[
\phi=\frac{|\mathcal J_R|\,\Delta t}{\hbar}.
\]

For amplitudes in the single-excitation sector,

\[
\boxed{
\begin{aligned}
a'_{01}
&=\cos\phi\,a_{01}
-i\sin\phi\,\frac{\mathcal J_R}{|\mathcal J_R|}a_{10},\\
a'_{10}
&=\cos\phi\,a_{10}
-i\sin\phi\,\frac{\mathcal J_R^*}{|\mathcal J_R|}a_{01}.
\end{aligned}
}
\]

The zero- and double-excitation amplitudes remain in their sectors under this exchange operator.

## Quarter-exchange witness

Starting from `|10>`, at

\[
\boxed{
\Delta t_{1/4}=\frac{\pi\hbar}{4|\mathcal J_R|}
}
\]

the state has equal single-excitation populations and the pure two-qubit concurrence reaches

\[
\boxed{C=1}
\]

inside this declared model.

At

\[
\Delta t_{1/2}=\frac{\pi\hbar}{2|\mathcal J_R|},
\]

the population is fully exchanged between `|10>` and `|01>`.

## Orientation reversal

Under

\[
\tau\mapsto-\tau,
\]

we have

\[
\operatorname{Re}\mathcal J_R\mapsto\operatorname{Re}\mathcal J_R,
\qquad
\operatorname{Im}\mathcal J_R\mapsto-\operatorname{Im}\mathcal J_R.
\]

The single-excitation transfer probabilities are preserved while the transfer phase changes. For positive `E_R`, the phase difference between the `+tau` and `-tau` transfer amplitudes is

\[
\boxed{\Delta\varphi_{\rm transfer}=2\tau\pmod{2\pi}.}
\]

This supplies a phase-sensitive orientation test in addition to population observables.

## Conservation checks

The implementation receipts:

- state norm closure under the exact unitary update;
- excitation-number expectation conservation;
- Hamiltonian Hermiticity;
- spectral radius `|E_R|`;
- orientation-sensitive transfer phase;
- concurrence of the resulting pure two-qubit state.

## Attribution firewall

The operator family is recorded as

`ORIENTED_COMPLEX_EXCHANGE_CANDIDATE`.

The physical target attribution remains `OPEN`. Entanglement-generation statements are scoped to the declared oriented-exchange model and require an independent target-system binding for promotion.

## Next frontier

The next test is a target adapter for neutrino flavor/mass evolution. Such an adapter must specify which two-level or multi-level subspace receives the exchange operator, preserve the standard vacuum/matter phase terms, and expose falsifiable residual phase predictions from the relational holonomy contribution.
