# GREMLIN Residual Red-Team v0.19 — Provenance-Bound Conditional Run Dependence

Status: CANDIDATE / CONDITIONAL-INDEPENDENCE FIREWALL / NO CANON PROMOTION

Date: 2026-09-28

## Why v0.19 exists

v0.18 established that a finite handcrafted nonlinear feature bank is not a universal independence test.

A direct RAW characteristic-kernel repair then exposed a different failure mode: a deterministic covariate shared by otherwise independent runs can appear as cross-run dependence when aligned samples are treated as the empirical joint distribution.

Synthetic witness:

[
x_i(t)=a(t),arepsilon_i(t),
]

with mutually independent Gaussian innovations (arepsilon_i) and a shared deterministic envelope (a(t)).

Familywise unbiased-HSIC on RAW rejects the no-dependence null even though the stochastic innovation sources are independent.

The existing v0.12 half-split nonstationarity heuristic can miss a periodic shared envelope.

Therefore the relevant question is not unconditional dependence of aligned samples. It is residual run dependence after conditioning on externally frozen experimental covariates.

## v0.19 candidate

v0.19 requires a conditioner provenance packet that states and commits that the conditioner:

- was frozen before target access;
- has externally verified chronology;
- was not fitted from the target;
- is explicitly not target-derived;
- has a source id;
- has operator, covariate, and conditioned-output commitments.

Target-derived conditioning is rejected before statistics.

The conditioned innovations are audited with a familywise omnibus statistic:

- Gaussian RBF kernels over a fixed multi-scale bandwidth bank;
- unbiased HSIC U-statistic;
- maximum over all predeclared run edges and all bandwidth pairs;
- independent IAAFT surrogate for every run in each null world;
- one Monte-Carlo p-value for the complete edge/bandwidth family.

## Pinned red-team findings

1. High-order deterministic Chebyshev relations (T_5,T_7,T_{17}) are detectable by the unbiased-HSIC family in the tested finite witness where the earlier low-order v0.18 feature bank fails for high order.

2. Shared deterministic envelope:
   RAW audit rejects; exact external conditioning removes the rejection.

3. Target-derived cross-run centering/scaling can manufacture apparent dependence from independent white runs. Such conditioning is therefore forbidden.

4. External conditioning does not automatically erase real dependence. In a shared-envelope + (T_7) witness, the conditioned audit still rejects and points to the true dependent pair.

5. A sufficiently wrong frozen conditioner leaves detectable residual dependence and therefore fails closed.

## Interpretation

A conditioned PASS means only:

NO DETECTED RUN DEPENDENCE UNDER THIS FROZEN CONDITIONER AND THIS CALIBRATED NULL.

It does not prove stochastic independence.

It does not prove causal independence.

It does not prove the external provenance authority or conditioner model is truthful.

Experiment-design independence and external provenance remain separate requirements.

## Operator-order rule

Dependence diagnostics that are intended to validate replication structure must not blindly notch or destructively remove target structure before the dependence question is posed. Preprocessing may destroy nonlinear relations and create false reassurance.

Conditioning is allowed only when its operator and covariates are independently frozen and committed before target access.

## Claim boundary

No v0.19 result establishes physical mechanism, new physics, or time fluctuations.
