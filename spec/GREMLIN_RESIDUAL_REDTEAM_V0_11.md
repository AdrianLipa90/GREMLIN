# GREMLIN Residual Red-Team v0.11

Status: CANDIDATE / RUN-INDEPENDENCE NULL CALIBRATION / NO CANON PROMOTION

Date: 2026-09-28

## Failure pinned in v0.10

v0.10 used fixed absolute thresholds for background run-dependence:

- median absolute zero-lag correlation > 0.10;
- median maximum circular correlation > 0.35.

Independent Monte Carlo showed that these thresholds are not invariant to sample count or background color.

Observed false INVALID rates for 16 independent runs:

- white: 0/100 for N=128,256,512,1024,2048;
- AR(1), phi=0.8: 100/100 at N=128; 29/100 at N=256; 0/100 at N>=512 in the tested bank;
- 1/f: 100/100 at N=128; 92/100 at N=256; 50/100 at N=512; 19/100 at N=1024; 0/100 at N=2048.

Therefore fixed correlation cutoffs are rejected.

## Rejected prototype

A first attempted repair randomized Fourier phase after detrend/notch preprocessing.

That prototype is invalid for strongly colored backgrounds because preprocessing can create amplitude-phase dependence that the post-processing randomization does not preserve.

For independent 1/f backgrounds the rejected prototype produced false INVALID rates as high as 62-70 percent in tested banks.

It is forbidden by v0.11.

## v0.11 null

For a stationary-within-run background declaration:

1. start from the raw residual;
2. preserve each run's complete Fourier amplitude spectrum;
3. randomize its Fourier phase independently;
4. reconstruct the surrogate raw residual;
5. apply the exact same detrend and candidate-band notch as the observed data;
6. compute the two run-dependence statistics;
7. repeat over a Monte Carlo null ensemble.

The two statistics are:

- median absolute zero-lag inter-run correlation;
- median maximum circular inter-run correlation.

Each receives a rank-based Monte Carlo p-value.

The declared run-dependence alpha is split across the two statistics by Bonferroni:

[
alpha_metric = alpha_run / 2.
]

The audit fails closed when the null ensemble cannot resolve alpha_metric.

## Stationarity firewall

The raw-phase surrogate is a second-order stationary spectral null.

Therefore v0.11 requires an explicit stationarity declaration before treating its p-values as calibrated.

Without that declaration the residual is preserved, but the dependence audit status is:

UNCALIBRATED_STATIONARITY_NOT_DECLARED.

No fixed-threshold fallback is allowed.

## Deterministic core replay

Standalone replay of the v0.11 dependence core passed 6/6 checks.

Independent AR(1), seed 123, 16x128:

- observed median zero-lag correlation: 0.1205316978;
- observed median max circular correlation: 0.4172217346;
- v0.10 fixed thresholds: INVALID;
- v0.11 p_zero: 0.9296875;
- v0.11 p_circular: 0.703125;
- v0.11: not invalidated.

Independent 1/f, seed 123, 16x256:

- observed median zero-lag correlation: 0.1200414041;
- observed median max circular correlation: 0.3681232382;
- v0.10 fixed thresholds: INVALID;
- v0.11 p_zero: 0.40625;
- v0.11 p_circular: 0.1875;
- v0.11: not invalidated.

Shared-realization controls at rho=0.2 were detected for both white and AR(1) witnesses.

## Exploratory Monte Carlo

Raw-phase-surrogate prototype, alpha_run=0.01, null_count=255:

Independent backgrounds:
- AR(1): 0/20 false INVALID at N=128,256,512 in tested banks;
- 1/f: 0/20 false INVALID at N=128,256,512 in tested banks;
- white: 0 observed in tested short-background banks.

Shared-realization power at N=512, 10 seeds per cell:
- white rho=0.05: 9/10; rho>=0.10: 10/10;
- AR(1) rho=0.05: 1/10; rho=0.10: 9/10; rho>=0.20: 10/10;
- 1/f rho=0.05: 0/10; rho=0.10: 1/10; rho=0.20: 10/10.

These are finite exploratory banks, not universal calibrated power curves.

## Claim boundary

A detected shared realization invalidates naive independent-run cross-fit.

It does not identify the source of dependence.

A non-detection does not prove independence.

The stationarity declaration is methodological, not physical attribution.

No result here establishes new physics or time fluctuations.
