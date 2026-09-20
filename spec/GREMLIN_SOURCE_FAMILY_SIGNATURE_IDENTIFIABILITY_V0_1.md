# GREMLIN Source-Family Signature Identifiability v0.1

Status: `CANDIDATE_DIAGNOSTIC_GATE / SOURCE_NEUTRAL / HELD_OUT_VALIDATION_REQUIRED_FOR_ROUTE`

This gate answers a narrower question than source attribution:

> given a declared set of candidate source-family signatures, do the available observables contain enough independent geometry to distinguish their amplitudes?

It does not select a physical source and it does not promote any candidate family to canon.

## 1. Inputs

Let the independently constructed cross-modal residual be

[
mathbf rinmathbb R^m,
]

with positive-definite covariance

[
Sigmainmathbb R^{m	imes m}.
]

Let the candidate source-family signature matrix be

[
oxed{
S=
egin{bmatrix}
mathbf s_1 & mathbf s_2 & cdots & mathbf s_p
end{bmatrix}
inmathbb R^{m	imes p}.
}
]

Each column is the predicted *shape across observables per unit candidate amplitude* for one declared source family.

A signature column must have explicit provenance. The matrix is not allowed to contain a source family whose normalization or channel mapping is undeclared.

## 2. Whitening

Take the Cholesky factor

[
Sigma=LL^T.
]

Define

[
oxed{
A=L^{-1}S,
qquad
mathbf b=L^{-1}mathbf r.
}
]

The weighted least-squares geometry is therefore ordinary Euclidean geometry in the whitened coordinates.

The weighted Gram/Fisher matrix is

[
oxed{
G
=
A^TA
=
S^TSigma^{-1}S.
}
]

## 3. Exact source-family identifiability theorem

Because (Sigma) is positive definite, (L) is invertible. Therefore

[
oxed{
operatorname{rank}(G)
=
operatorname{rank}(A)
=
operatorname{rank}(S).
}
]

Hence the declared (p) source-family amplitudes are algebraically identifiable from the fit channels iff

[
oxed{
operatorname{rank}(G)=p.
}
]

If

[
operatorname{rank}(G)<p,
]

then there exists a non-zero vector (mathbf v) satisfying

[
Smathbf v=0,
]

and therefore

[
S(mathbf a+lambdamathbf v)=Smathbf a
]

for every scalar (lambda).

The affected source-family amplitudes are observationally non-unique.

GREMLIN must report

[
oxed{	exttt{UNDERDETERMINED}}
]

for unique amplitude/source-family recovery.

## 4. Nullspace and degeneracy structure

The SVD

[
A=U,operatorname{diag}(sigma_1,ldots,sigma_q)V^T
]

provides the exact/numerical nullspace.

For numerical rank (r),

[
oxed{
dimker A=p-r.
}
]

Each nullspace vector is a source-amplitude combination that leaves the predicted observable vector unchanged at the declared numerical tolerance.

The numerical nullspace basis is a diagnostic representation, not a canonical physical basis.

### Pairwise degeneracy classes

Normalize each non-zero whitened signature column,

[
hat{mathbf s}_j=rac{A_{cdot j}}{|A_{cdot j}|}.
]

If

[
left|
hat{mathbf s}_i^That{mathbf s}_j
ight|
approx 1,
]

the two source families are pairwise indistinguishable up to amplitude sign.

Connected components of this pairwise-collinearity relation may be reported as pairwise degeneracy classes.

This does not replace the full nullspace test: three or more signatures can be linearly dependent without any pair being collinear.

## 5. Practical conditioning gate

Formal full rank is not sufficient for stable inversion.

Let

[
sigma_{max}gecdotsgesigma_{min}>0
]

be the retained singular values of (A).

Define

[
oxed{
kappa_2(A)=rac{sigma_{max}}{sigma_{min}}.
}
]

GREMLIN distinguishes:

- `UNDERDETERMINED`: rank (<p);
- `ILL_CONDITIONED`: rank (=p) but the configured numerical condition limit is exceeded;
- `IDENTIFIABLE`: rank (=p) and the condition gate passes.

The condition threshold is a numerical policy parameter, not a physical constant.

## 6. Candidate amplitude estimator

Only in the `IDENTIFIABLE` state may GREMLIN report a unique weighted least-squares candidate amplitude vector

[
oxed{
hat{mathbf a}
=
G^{-1}S^TSigma^{-1}mathbf r.
}
]

Equivalently,

[
hat{mathbf a}
=
(A^TA)^{-1}A^Tmathbf b.
]

The nominal amplitude covariance under the declared linear/Gaussian local model is

[
oxed{
operatorname{Cov}(hat{mathbf a})=G^{-1}.
}
]

These are candidate model coefficients, not physical-source verdicts.

For rank-deficient or ill-conditioned cases GREMLIN must not report a unique amplitude solution as if it were identified.

## 7. Fit residual

The fitted residual is

[
mathbf e
=
mathbf r-Shat{mathbf a}.
]

The training statistic is

[
oxed{
chi^2_{m fit}
=
mathbf e^TSigma^{-1}mathbf e.
}
]

The null statistic is

[
chi^2_{0}
=
mathbf r^TSigma^{-1}mathbf r,
]

with training improvement

[
Deltachi^2_{m fit}
=
chi^2_0-chi^2_{m fit}.
]

Training improvement is not independent confirmation.

## 8. Held-out validation

Source-family routing requires an independent held-out channel set.

Let

[
mathbf r_h,quad
S_h,quad
Sigma_h
]

be data/signatures/covariance not used to estimate (hat{mathbf a}).

The frozen fit predicts

[
hat{mathbf r}_h=S_hhat{mathbf a}.
]

Then

[
oxed{
chi^2_h
=
(mathbf r_h-S_hhat{mathbf a})^T
Sigma_h^{-1}
(mathbf r_h-S_hhat{mathbf a}).
}
]

The held-out null statistic is

[
chi^2_{h,0}
=
mathbf r_h^TSigma_h^{-1}mathbf r_h,
]

and

[
oxed{
Deltachi^2_h
=
chi^2_{h,0}-chi^2_h.
}
]

A positive value means that the frozen candidate-family mixture predicts the held-out residual better than the zero-source-family null under the declared covariance. It is not by itself proof of physical origin.

## 9. Routing rule

A source-family test may be routed downstream only when:

1. the cross-modal residual packet is otherwise source-routing admissible;
2. source-family rank is full;
3. the configured conditioning gate passes;
4. all signature columns have explicit provenance;
5. the fit is not circular;
6. independent held-out data are supplied.

Then GREMLIN may emit

[
oxed{	exttt{ALLOW_CANDIDATE_SOURCE_FAMILY_TESTS}}.
]

Otherwise it emits one of:

- `REQUEST_MORE_INDEPENDENT_CHANNELS`;
- `REQUEST_BETTER_CONDITIONING`;
- `REQUEST_HELD_OUT_VALIDATION`;
- `STOP_DECLARED_SOURCE_FAMILY_MODEL`.

## 10. Firewalls

This gate does not establish:

[
	ext{candidate amplitude}Rightarrow	ext{physical source},
]

[
	ext{best fit}Rightarrow	ext{true cause},
]

[
U_I	ext{ is physical},
]

[
W_{m chem}=W_{m sem},
]

or

[
Phi_{m phase}Rightarrow g_{mu
u}.
]

The strongest admitted statement is:

[
oxed{
	ext{the declared source-family signatures are or are not distinguishable
within the supplied observable/covariance geometry.}
}
]

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
