# GREMLIN Residual Red-Team v0.12 — IAAFT + Stationarity Firewall

Status: CANDIDATE / ADVERSARIAL / V0.11 REGRESSION REPAIRED IN PROTOTYPE / EXACT PACKAGE REPLAY OPEN

Date: 2026-09-28

## Failure found in v0.11

v0.11 repaired fixed-threshold run-dependence checks by using a raw Fourier-phase surrogate before the identical detrend/notch operator.

That operator ordering is correct, but the surrogate family is still too weak for non-Gaussian heavy-tailed backgrounds.

Independent stationary Student-t3 runs were falsely classified as run-dependent in 18/20 tested seeds under the v0.11 phase-only surrogate at alpha_run=0.01 and 255 null worlds.

The failure is structural:

- Fourier phase randomization preserves the raw Fourier magnitude spectrum;
- it does not preserve the empirical sample-value distribution;
- therefore heavy tails, bursts and higher-order amplitude structure can be turned into an invalid null.

This is a regression relative to the later v0.10.2 IAAFT work because v0.11 forked from an earlier v0.10 lineage.

## v0.12 repair

v0.12 combines:

1. the v0.10.2 IAAFT marginal-preserving surrogate family;
2. the v0.11 operator ordering rule:
   RAW surrogate first, then the exact observed detrend/notch operator;
3. explicit null-applicability declaration;
4. a hard abstention for obvious half-run nonstationarity;
5. the existing extreme-long-memory abstention;
6. surrogate spectral-fidelity abstention;
7. Bonferroni split across the two run-dependence statistics.

Each IAAFT row preserves the empirical marginal exactly by rank remapping and approximately preserves the raw Fourier magnitude spectrum.

The two run-dependence statistics remain:

- median absolute zero-lag inter-run correlation;
- median maximum circular inter-run correlation.

At alpha_run=0.01 the default 255-null ensemble can resolve alpha/2=0.005.

## Nonstationarity firewall

IAAFT is not a universal null for arbitrary nonstationary processes.

v0.12 therefore includes a deliberately conservative hard-abstention diagnostic for obvious run-wide change points:

- robust first-half vs second-half scale shift;
- robust first-half vs second-half location shift;
- cross-run directional consistency.

This diagnostic is explicitly heuristic. It may abstain conservatively; it may not establish a physical cause.

## Independent prototype red-team

The following tests were executed outside the package import chain against the v0.12 core logic.

Default strict surface:
- alpha_run=0.01;
- 255 null worlds;
- IAAFT iterations=20.

Stationary Student-t3:
- v0.11 phase-surrogate reproducer: 18/20 false INVALID in seeds 300..319;
- deterministic seed 300: v0.11 false INVALID; v0.12 PASS;
- v0.12 independent bank seeds 3000..3019: 20/20 PASS.

GARCH-like volatility clustering:
- 5/5 PASS.

Bursty/spike heavy-tail background:
- 5/5 PASS.

Shared white realization, rho=0.20:
- 3/3 correctly INVALID;
- each tested case returned the minimum Monte-Carlo rank p=1/256 for both statistics.

Variance change point:
- 5/5 routed to NONSTATIONARY hard abstention in the prototype bank.

Near-unit-root AR(1):
- phi=0.99, N=2048 routed to LONG_MEMORY hard abstention.

Typical median IAAFT raw-spectrum relative error in the tested heavy-tail banks was approximately 1-3 percent, below the candidate 15-percent quality ceiling.

These are finite adversarial banks, not a universal calibration theorem.

## Open gates

The following remain open and must not be hidden:

- exact package replay of test_residual_spectroscopy_v12.py;
- larger Student-t tail calibration;
- alpha calibration across acquisition geometries;
- power curves for weak shared realizations under heavy-tail backgrounds;
- systematic calibration of the nonstationarity hard-abstention heuristic;
- IAAFT iteration/convergence sensitivity;
- multivariate nuisance/run dependence;
- post-selection error across recursive decomposition rounds.

## Claim boundary

PASS means only that the tested run set did not reject the declared IAAFT run-independence null.

INVALID means only that naive independent-run cross-fit is not supported.

ABSTAIN means the null is not calibrated for the observed regime.

None of these establishes an instrumental cause, astrophysical origin, new physics, or time fluctuations.
