# GREMLIN Source-Family Signature Identifiability v0.1

Status: `CANDIDATE_DIAGNOSTIC_GATE / SOURCE_NEUTRAL / HELD_OUT_VALIDATION_REQUIRED_FOR_ROUTE`

This gate answers a narrower question than source attribution:

> given a declared set of candidate source-family signatures, do the available
> observables contain enough independent geometry to distinguish their amplitudes?

It does not select a physical source and it does not promote any candidate family
to canon.

## 1. Inputs

Let the independently constructed cross-modal residual be

~~~text
r in R^m
~~~

with positive-definite covariance

~~~text
Sigma in R^(m x m)
~~~

Let the candidate source-family signature matrix be

~~~text
S = [ s_1  s_2  ...  s_p ]

S in R^(m x p)
~~~

Each column is the predicted *shape across observables per unit candidate
amplitude* for one declared source family.

A signature column must have explicit provenance. The matrix is not allowed to
contain a source family whose normalization or channel mapping is undeclared.

## 2. Whitening

Take the Cholesky factor

~~~text
Sigma = L L^T
~~~

Define

~~~text
A = L^(-1) S

b = L^(-1) r
~~~

The weighted least-squares geometry is therefore ordinary Euclidean geometry in
the whitened coordinates.

The weighted Gram/Fisher matrix is

~~~text
G = A^T A = S^T Sigma^(-1) S
~~~

## 3. Exact source-family identifiability theorem

Because `Sigma` is positive definite, `L` is invertible. Therefore

~~~text
rank(G) = rank(A) = rank(S)
~~~

Hence the declared `p` source-family amplitudes are algebraically identifiable
from the fit channels iff

~~~text
rank(G) = p
~~~

If

~~~text
rank(G) < p
~~~

then there exists a non-zero vector `v` satisfying

~~~text
S v = 0
~~~

and therefore

~~~text
S (a + lambda v) = S a
~~~

for every scalar `lambda`.

The affected source-family amplitudes are observationally non-unique.

GREMLIN must report

~~~text
UNDERDETERMINED
~~~

for unique amplitude/source-family recovery.

## 4. Nullspace and degeneracy structure

The singular-value decomposition

~~~text
A = U diag(sigma_1, ..., sigma_q) V^T
~~~

provides the exact/numerical nullspace.

For numerical rank `r`,

~~~text
dim ker(A) = p - r
~~~

Each nullspace vector is a source-amplitude combination that leaves the predicted
observable vector unchanged at the declared numerical tolerance.

The numerical nullspace basis is a diagnostic representation, not a canonical
physical basis.

### Pairwise degeneracy classes

Normalize each non-zero whitened signature column:

~~~text
s_hat_j = A[:, j] / ||A[:, j]||
~~~

If

~~~text
| s_hat_i^T s_hat_j | ~= 1
~~~

the two source families are pairwise indistinguishable up to amplitude sign.

Connected components of this pairwise-collinearity relation may be reported as
pairwise degeneracy classes.

This does not replace the full nullspace test: three or more signatures can be
linearly dependent without any pair being collinear.

## 5. Practical conditioning gate

Formal full rank is not sufficient for stable inversion.

Let

~~~text
sigma_max >= ... >= sigma_min > 0
~~~

be the retained singular values of `A`.

Define

~~~text
kappa_2(A) = sigma_max / sigma_min
~~~

GREMLIN distinguishes:

- `UNDERDETERMINED`: rank < p;
- `ILL_CONDITIONED`: rank = p but the configured numerical condition limit is exceeded;
- `IDENTIFIABLE`: rank = p and the condition gate passes.

The condition threshold is a numerical policy parameter, not a physical constant.

## 6. Candidate amplitude estimator

Only in the `IDENTIFIABLE` state may GREMLIN report a unique weighted
least-squares candidate amplitude vector

~~~text
a_hat
= G^(-1) S^T Sigma^(-1) r
~~~

Equivalently,

~~~text
a_hat
= (A^T A)^(-1) A^T b
~~~

The nominal amplitude covariance under the declared linear/Gaussian local model is

~~~text
Cov(a_hat) = G^(-1)
~~~

These are candidate model coefficients, not physical-source verdicts.

For rank-deficient or ill-conditioned cases GREMLIN must not report a unique
amplitude solution as if it were identified.

## 7. Fit residual

The fitted residual is

~~~text
e = r - S a_hat
~~~

The training statistic is

~~~text
chi_fit^2 = e^T Sigma^(-1) e
~~~

The null statistic is

~~~text
chi_0^2 = r^T Sigma^(-1) r
~~~

with training improvement

~~~text
Delta chi_fit^2 = chi_0^2 - chi_fit^2
~~~

Training improvement is not independent confirmation.

## 8. Held-out validation

Source-family routing requires an independent held-out channel set.

Let

~~~text
r_h, S_h, Sigma_h
~~~

be data/signatures/covariance not used to estimate `a_hat`.

The frozen fit predicts

~~~text
r_hat_h = S_h a_hat
~~~

Then

~~~text
chi_h^2
= (r_h - S_h a_hat)^T
  Sigma_h^(-1)
  (r_h - S_h a_hat)
~~~

The held-out null statistic is

~~~text
chi_(h,0)^2 = r_h^T Sigma_h^(-1) r_h
~~~

and

~~~text
Delta chi_h^2 = chi_(h,0)^2 - chi_h^2
~~~

A positive value means that the frozen candidate-family mixture predicts the
held-out residual better than the zero-source-family null under the declared
covariance. It is not by itself proof of physical origin.

## 9. Routing rule

A source-family test may be routed downstream only when:

1. the cross-modal residual packet is otherwise source-routing admissible;
2. source-family rank is full;
3. the configured conditioning gate passes;
4. all signature columns have explicit provenance;
5. the fit is not circular;
6. independent held-out data are supplied.

Then GREMLIN may emit

~~~text
ALLOW_CANDIDATE_SOURCE_FAMILY_TESTS
~~~

Otherwise it emits one of:

- `REQUEST_MORE_INDEPENDENT_CHANNELS`;
- `REQUEST_BETTER_CONDITIONING`;
- `REQUEST_HELD_OUT_VALIDATION`;
- `STOP_DECLARED_SOURCE_FAMILY_MODEL`.

## 10. Firewalls

This gate does not establish:

~~~text
candidate amplitude => physical source
best fit => true cause
U_I is physical
W_chem = W_sem
Phi_phase => g_(mu nu)
~~~

The strongest admitted statement is:

~~~text
the declared source-family signatures are or are not distinguishable
within the supplied observable/covariance geometry
~~~

## 11. Upstream/downstream links

Upstream cross-modal residual packet:

https://github.com/AdrianLipa90/GREMLIN/pull/88

MAS candidate orchestration:

https://github.com/AdrianLipa90/PhaseNav-MAS-Upgrade

PNCS evidence routing:

https://github.com/AdrianLipa90/PhaseNav-Natural-Coding-System/pull/70

PhaseNav runtime evidence sidecar:

https://github.com/AdrianLipa90/noema-phasenav-core/pull/35

FPDG staging authority:

https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph/pull/22
