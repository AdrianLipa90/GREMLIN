# GREMLIN Fractal-Moire / ARPL Infinite-Depth Delta 2026-09-26

Status: EXACT_INDUCTIVE_LIMIT_REFERENCE_PASS / ARPL_SPECTRAL_CLOSURE_PASS / HOSTED_CI_NOT_PRESENT

## 1. New exact layer

The operator stack now includes an exact inductive-limit theorem.

For isometric embeddings

\[
J_N:\mathcal H_N\to\mathcal H_{N+1}
\]

and compatible finite unitaries

\[
R_{N+1}J_N=J_NR_N,
\]

there is a unique unitary \(R_\infty\) on the Hilbert inductive limit.

The mismatch family

\[
\Delta_N=(I-R_N)^*(I-R_N)
\]

inherits the same compatibility.

For finite-dimensional levels,

\[
\sigma(R_\infty)
=
\overline{\bigcup_N\sigma(R_N)}.
\]

## 2. ARPL exact specialization

For the ARPL clocks

\[
K_{h,N}\cong\mathbb Z/L_N\mathbb Z,
\]

the canonical coarse pullback is

\[
(J_Nf)(a)=f(a\bmod L_N).
\]

It is isometric and satisfies

\[
U_{N+1}J_N=J_NU_N.
\]

The child carry-cocycle and the coarse-pullback intertwiner are two exact
resolutions of the same odometer.

On the infinite-refinement sector \(L_N\to\infty\):

\[
\boxed{\sigma(U_\infty)=S^1}
\]

while the point spectrum is the countable dense Pontryagin-dual eigenvalue
group.

For

\[
\Delta_\infty=(I-U_\infty)^*(I-U_\infty),
\]

\[
\boxed{\sigma(\Delta_\infty)=[0,4]}.
\]

The point eigenvalues are countable and dense in that interval.

## 3. Relational zero and gap

The topological generator property gives

\[
\ker\Delta_\infty=\operatorname{span}\{1\}.
\]

At finite level,

\[
\lambda_N^+
=
4\sin^2(\pi/L_N).
\]

Hence

\[
\lambda_N^+\to0
\]

on infinite refinement.

The infinite mismatch operator has no positive gap above its one-dimensional
relational-zero mode.

In the canonical arithmetic ultrametric scale
\(\varepsilon_N=1/L_N\),

\[
\lambda_N^+/\varepsilon_N^2
\to4\pi^2.
\]

## 4. Independent replay

Orbital coarse-pullback controls:
- maximum isometry defect: 1.1102230246251565e-16;
- maximum adjoint-roundtrip defect: 6.397344083151129e-17;
- child recombination residual: 0;
- tested cyclic-translation intertwiner residual: 0.

ARPL finite spectral controls:
- nested odometer spectrum residual <= 9.56e-16;
- nested mismatch spectrum residual <= 1.78e-15;
- finite zero multiplicity = 1 on tested clocks;
- L=2310 first positive mismatch = 7.398360837449984e-6;
- L=30030 quadratic gap-scaling error vs 4*pi^2 =
  1.4402157688664374e-7.

## 5. 36D firewall

PhaseNav v0.6 now distinguishes:
- FINITE_LEVEL_ONLY;
- INDUCTIVE_STEP_COVARIANT;
- INDUCTIVE_LIMIT_COVARIANT.

An infinite-depth claim requires:
- an inductive-family witness;
- a limit-theorem witness;
- a cofinality witness;
- cross-level residual checks;
- an explicit infinite-depth information-loss ledger.

One 36D packet cannot self-certify infinity.

## 6. Current exact frontier

Closed mathematically at reference/theorem level:
- branch isometries;
- fixed-branch unitary recursion;
- branch permutations;
- Cuntz block cocycles;
- overlap Gram covariance;
- ARPL carry cocycle;
- exact inductive limit;
- ARPL full-circle and [0,4] mismatch spectra.

Next mathematical gate:
approximate/noisy inductive consistency.

Physical gates remain:
- physical IFS;
- physical orbital/cocycle law;
- physical ARPL-to-36D state map;
- calibration/experiment.

Hosted GitHub status checks were absent on the implementation heads.

canon_allowed = false.
