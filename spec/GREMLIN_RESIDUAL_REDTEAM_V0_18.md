# GREMLIN Residual Red-Team v0.18 — Nonlinear / Sparse Run Dependence

Status: CANDIDATE / FAIL-CLOSED DEPENDENCE FIREWALL / LOW-POWER WARNING / NO CANON PROMOTION

Date: 2026-09-28

## v0.12 gap

The v0.12 run-dependence audit uses:

- median absolute zero-lag correlation;
- median maximum circular correlation.

Both are linear statistics and both aggregate over run pairs by median.

A deterministic nonlinear shared source can therefore pass.

Pinned sparse witness:

[
x_0=z,
qquad
x_1=(z^2-1)/\sqrt2,
]

with fourteen additional independent Gaussian runs.

For the deterministic seed:

- Pearson corr(x0,x1) about 0.023;
- nonlinear relation R2 exactly 1 by construction;
- v0.12-style median zero-lag statistic about 0.0289;
- v0.12-style median circular statistic about 0.1438;
- v0.12 IAAFT p_zero about 0.672;
- v0.12 IAAFT p_circular about 0.355.

Thus v0.12 does not invalidate cross-fit despite exact nonlinear dependence.

A second witness uses a common latent phase phi_t with runs

[
x_m(t)=\sqrt2\cos(m\phi_t).
]

v0.12 again passes the linear dependence null while pairs are deterministically
related through harmonic identities.

## v0.18 candidate repair

For each preprocessed run, build a bounded feature bank:

- x;
- x^2;
- x^3;
- |x|.

For every run pair, compute every cross-feature correlation.

Use the maximum absolute dependence across all run pairs and feature pairs as one
omnibus statistic.

This directly attacks two v0.12 gaps:

- nonlinear dependence;
- sparse-pair dilution by median aggregation.

The null is generated with the same v0.12 raw IAAFT procedure first, followed by
the identical detrend/notch operator and then the nonlinear max statistic.

Because the statistic is already the maximum over the full feature/pair family,
its Monte-Carlo null controls that family internally.

The total run-dependence alpha is split between:

- v0.12 linear/circular audit;
- v0.18 nonlinear max audit.

## Independent prototype results

Strict nonlinear alpha: 0.005.
255 null worlds.
IAAFT iterations: 10.

Detected:

- sparse deterministic nonlinear pair: p=1/256;
- harmonic shared-latent bank: p=1/256.

Independent controls observed with no p<=0.005:

- white: 3/3;
- Student-t3: 8/8;
- AR(1), phi=0.8: 3/3;
- GARCH-like: 8/8;
- bursty heavy-tail: 3/3.

These 25 trials are not a universal false-positive bound.

## Power warning

The gate is deliberately conservative and weak dependence can pass undetected.

For a sparse nonlinear pair at 16x256 in a tiny three-seed exploratory bank:

- rho=0.10: 0/3 detections at p<=0.005;
- rho=0.20: 0/3;
- rho=0.30: 1/3;
- rho=0.40: 0/3.

The non-monotone tiny-bank counts themselves show that these are not calibrated
power estimates.

Therefore a v0.18 PASS must never be interpreted as proof of independence.

## Claim boundary

FAIL means the independent-run assumption is not supported under this feature
family.

PASS means only that this finite nonlinear feature bank did not reject.

It does not exclude arbitrary nonlinear dependence.

It does not identify cause.

No result establishes physical mechanism, new physics or time fluctuations.


## High-order deterministic no-go

The finite feature bank was attacked with a dependence outside its low-order span.

Let

[
x_0=\sqrt2\cos\phi,
\qquad
x_1=\sqrt2\cos(m\phi)
=\sqrt2\,T_m(x_0/\sqrt2).
]

Thus x1 is a deterministic Chebyshev-polynomial function of x0.

Nevertheless, with the v0.18 feature family {x,x^2,x^3,|x|} and the strict
nonlinear alpha 0.005:

- m=5 produced p=0.3984375;
- m=7 produced p=0.671875;
- m=17 produced p=0.015625.

All three therefore fail to invalidate cross-fit at the strict threshold despite
deterministic dependence.

This is retained as an explicit no-go:

[
\boxed{\text{finite handcrafted feature bank} \neq \text{universal independence test}.}
]

The next candidate should use a characteristic-kernel or equivalent universal
dependence statistic rather than extending the polynomial list ad hoc.
