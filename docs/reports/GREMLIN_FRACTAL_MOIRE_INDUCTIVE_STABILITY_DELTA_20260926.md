# GREMLIN Fractal-Moire Inductive Stability Delta 2026-09-26

Status: SUMMABLE_DEFECT_STABILITY_PASS / NOISY_36D_CONTRACT_PASS / PHYSICAL_ERROR_MODEL_OPEN

## 1. Exact stability theorem

The stack now handles approximate cross-level covariance.

For

\[
\varepsilon_N
=
\|R_{N+1}J_N-J_NR_N\|
\]

with

\[
\sum_N\varepsilon_N<\infty,
\]

the approximate finite-level family defines a genuine unitary limit.

The remaining error budget is

\[
\boxed{
\tau_N
=
\sum_{k=N}^{\infty}\varepsilon_k.
}
\]

Then

\[
\|R_\infty J_N-J_NR_N\|
\le
\tau_N
\]

in the canonical limit embedding.

For the mismatch,

\[
\boxed{
\|\Delta_\infty J_N-J_N\Delta_N\|
\le
2\tau_N.
}
\]

Finite unitary eigenvalues are within \(\tau_N\) of the limit spectrum and
finite mismatch eigenvalues are within \(2\tau_N\).

## 2. Why decreasing residual is insufficient

A sequence may satisfy

\[
\varepsilon_N\to0
\]

without being summable.

The harmonic control used in the replay has final one-step defect near

\[
10^{-4}
\]

while the tested accumulated tail after level 100 is still

\[
4.590327528305752.
\]

Therefore a decreasing residual graph is not an infinite-depth certificate.

## 3. Executable geometric envelope

For

\[
\varepsilon_N\le Aq^N,
\qquad
0\le q<1,
\]

the certified tail is

\[
\boxed{
\tau_N
\le
\frac{Aq^N}{1-q}.
}
\]

The 36D v0.7 contract computes this bound and rejects:
- q >= 1;
- an observed defect above the envelope;
- missing summability provenance;
- empty noisy-depth information-loss ledger.

## 4. Current reference control

For

\[
A=0.2,\quad q=0.5,\quad N=5,
\]

the current envelope is

\[
0.00625,
\]

the accepted observed defect is

\[
0.005,
\]

the unitary tail budget is

\[
0.0125,
\]

and the mismatch budget is

\[
0.025.
\]

## 5. Current operator stack

The project now has separate typed surfaces for:

1. compression-only IFS observables;
2. fixed-branch unitary intertwiners;
3. branch permutations;
4. general Cuntz block cocycles;
5. ARPL carry cocycles;
6. overlap-Gram covariance;
7. global unitary dilation;
8. exact inductive-limit covariance;
9. summable-defect inductive stability.

The next blocker is no longer an operator-algebra ambiguity.

It is a source-owned physical/noisy family and its error model.

Hosted CI status is absent on the implementation heads; only independent
reference replay is claimed.

canon_allowed = false.
