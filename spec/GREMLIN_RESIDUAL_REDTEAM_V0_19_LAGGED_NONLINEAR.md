# GREMLIN Residual Red-Team v0.19 — Lagged Nonlinear Run Dependence

Status: CANDIDATE / HARD-DEPENDENCE FIREWALL / LOW-POWER WARNING / NO CANON PROMOTION

Date: 2026-09-28

## v0.18 gap

v0.18 tests a bounded nonlinear feature family

- x;
- x^2;
- x^3;
- |x|,

and takes the maximum zero-lag cross-feature correlation across all run pairs.

v0.12 separately tests circular lag dependence, but only on the raw linear channels.

Therefore a deterministic relation can lie between the two surfaces.

Pinned witness:

x0(t) = z(t)

x1(t) = standardized(z(t-L)^2)

with fourteen additional independent Gaussian runs.

For seed 19019, N=512 and L=37:

- raw zero-lag correlation is about 0.031;
- raw max circular linear correlation for the dependent pair is about 0.154;
- v0.18-like zero-lag nonlinear maximum does not select the dependent pair;
- exact replay of the v0.18 nonlinear IAAFT algorithm gives p=0.03515625 and does not invalidate cross-fit;
- the lagged nonlinear maximum is about 0.951 after the identical detrend/notch path and identifies run pair 0/1.

This is a deterministic shared-source dependency that v0.18 can miss.

## v0.19 candidate repair

Use the same bounded feature bank as v0.18.

For every run pair and every feature pair, compute the maximum absolute circular correlation across every circular lag.

The omnibus statistic is then the maximum across:

run pairs x feature pairs x circular lags.

The null is generated exactly upstream of preprocessing:

RAW IAAFT
-> identical detrend/notch
-> lagged nonlinear family maximum.

The Monte-Carlo p value therefore calibrates the full bounded family jointly.

## Experimentwise alpha

v0.19 does not add a third dependence test with a fresh alpha.

The declared total run-dependence alpha is split into three equal family budgets:

1. v0.12 linear/circular family;
2. v0.18 zero-lag nonlinear family;
3. v0.19 lagged-nonlinear family.

The v0.12 family may further Bonferroni-split its own share internally.

## Independent prototype

Strict alpha: 0.005.
255 IAAFT null worlds.
10 IAAFT iterations.

Pinned lagged-nonlinear witness:

- observed maximum about 0.95097;
- witness pair 0/1;
- witness features x^2 versus x;
- circular lag 475 (= -37 mod 512);
- p=1/256;
- q95 null about 0.5800;
- q99 null about 0.6025.

Controls:

- white: p=0.8046875;
- AR(1), phi=0.8: p=0.0234375;
- Student-t3: p=0.1875;
- GARCH-like: p=0.98046875;
- bursty heavy-tail: p=0.84765625.

No control crossed p<=0.005 in this tiny control bank.

## Power warning

This gate is not a proof of run independence.

Single-seed exploratory lagged sparse dependence:

- rho=0.30: p=0.171875, not detected;
- rho=0.50: p=1/256, detected;
- rho=0.70: p=1/256, detected.

These are not calibrated power estimates.

The maximum across all run pairs, feature pairs and lags carries a substantial multiplicity cost.

## Heavy-tail saturation warning

For Student-t and bursty controls, cubic feature correlations can approach one in both observed and null worlds.

Therefore the raw statistic magnitude is non-interpretable by itself.

Only the calibrated null comparison is admissible.

## Rejected alternative: max-pair distance correlation

A separate model-free distance-correlation probe was tested.

At 16x128 with 255 circular-shift nulls:

- exact sparse nonlinear witness: p=0.0078125;
- harmonic shared-latent witness: p=0.01171875;
- rho=0.8 sparse dependence: only 1/3 exploratory trials reached p<=0.005.

It did not outperform the bounded v0.18/v0.19 strategy on this attack surface and is retained as a NO-GO / auxiliary low-power alternative, not an upgrade.

## Claim boundary

A v0.19 FAIL means the independent-run assumption is unsupported under this bounded lagged-nonlinear family.

A v0.19 PASS means only that this family did not reject.

PASS does not prove independence.

FAIL does not identify cause.

Circular lag is an index relation, not automatically a physical time delay.

No result establishes a physical mechanism, new physics or time fluctuations.
