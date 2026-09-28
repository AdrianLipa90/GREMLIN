# GREMLIN Residual Red-Team v0.19 — Dual-Surface Functional Dependence

Status: CANDIDATE GUARD / HIGH-ORDER FUNCTIONAL PASS / UNIVERSAL-INDEPENDENCE NO-GO / NO CANON PROMOTION

Date: 2026-09-28

## Why v0.19 exists

v0.18 correctly demonstrated that the finite feature bank {x,x^2,x^3,|x|} is not a universal independence test.

A second attack showed that preprocessing itself is part of the epistemic boundary.

For a deterministic high-order Chebyshev relation, dependence can be obvious on the untouched residual and weak after detrend/notch. Therefore:

[
\boxed{\text{POST-OPERATOR no-rejection} \neq \text{RAW independence}.}
]

## Functional guard

v0.19 adds a NumPy-only nonparametric predictive guard.

For every ordered run pair i->j, k-nearest neighbours are selected using run i and used to predict run j. The statistic is out-of-sample predictive R^2. The audit statistic is the maximum over all run pairs and both prediction directions.

Calibration uses the existing RAW IAAFT surrogate generator. Each surrogate is passed through exactly the same surface operator as the observed data.

This guard is deliberately typed as a functional-dependence guard, not a universal independence test.

## Two surfaces

1. RAW: the residual is tested without detrend/notch.
2. POST_CANDIDATE_REMOVAL: the existing detrend/notch operator is applied.

The two surfaces answer different questions.

If RAW rejects independence but the post-removal surface does not, v0.19 returns:

OPERATOR_SENSITIVE_RUN_DEPENDENCE_AMBIGUOUS

and cross-fit promotion is fail-closed.

## High-order witness

For 8 runs x 128 samples with

x0=sqrt(2) cos(phi),
x1=sqrt(2) cos(17 phi),

the raw max predictive R^2 is about 0.76 and the familywise 31-null screening gives p=1/32.

On the post-removal surface the same witness is not rejected in the pinned prototype.

This closes the specific v0.18 high-order deterministic no-go by abstaining when the operator hides dependence.

## Explicit no-go

The guard fails on dependence that does not alter conditional mean in a predictable way.

Pinned example:

Y = X epsilon,

with independent zero-mean epsilon.

The conditional variance depends on X while a kNN mean predictor may have no positive R^2.

Therefore:

[
\boxed{\text{kNN functional guard} \neq \text{universal independence test}.}
]

Characteristic-kernel / mutual-information / conditional-distribution gates remain open.

## False-positive adversarial check

A white-noise seed that produced p=1/32 under a permissive 31-null alpha=0.05 screen was rerun with 255 null worlds.

It yielded p=0.04296875 and therefore did not reject at the intended alpha=0.005.

This is one adversarial seed, not an empirical false-positive bound.

## Claim boundary

A v0.19 FAIL means the independent-run assumption is unsupported under the tested functional family/surface.

A v0.19 no-rejection does not prove independence.

RAW/post-removal disagreement is ambiguity, not evidence that preprocessing removed a nuisance correctly.

No result establishes cause, physical mechanism, new physics or time fluctuations.
