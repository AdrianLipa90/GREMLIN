# GREMLIN Residual Red-Team v0.7

Status: CANDIDATE / WEAK-REPLICATE ACCUMULATION / NO CANON PROMOTION

Date: 2026-09-28

## Failure in the fixed-prominence gate

The v0.4 narrowband validation threshold is an effect-size threshold, not merely a significance threshold.

For an exact-bin sinusoid of amplitude A in white noise sigma, a five-bin band and a prominence threshold tau have the idealized large-replicate floor

A/sigma >= 2 sqrt[w(tau-1)/N].

For w=5 and tau=2.5:

- N=1024: floor about 0.171 sigma;
- N=2048: floor about 0.121 sigma;
- N=4096: floor about 0.086 sigma.

Therefore a sufficiently weak but perfectly persistent line cannot be recovered merely by collecting more runs if the classifier requires the same fixed prominence in each holdout.

This conflicts with the residual-preserving principle: repeated independent evidence should be allowed to accumulate.

## v0.7 accumulation gate

v0.7 keeps all previous v0.6 firewalls and adds a second narrowband route for signals below the fixed-prominence floor.

For every cross-fit direction:

1. discover a candidate frequency only on training runs;
2. use a 10-percent trimmed-mean PSD to reduce sensitivity to a few extreme runs;
3. locally normalize band power by a surrounding spectral neighborhood;
4. validate the training-selected frequency on held-out runs by its rank among valid holdout frequencies;
5. repeat the validation on a first-difference analysis copy;
6. require at least 3/4 directed folds to pass and cross-fold frequency agreement within two bins.

No individual run is required to exceed a fixed 2.5x prominence threshold.

The new class is

UNRESOLVED_WEAK_NARROWBAND_ACCUMULATION_CANDIDATE.

It is a diagnostic class only.

## Deterministic witness

Seed 130000, 32 runs x 2048 samples, white noise sigma 1, half-bin line amplitude 0.10 sigma:

- v0.6 legacy classification: STOCHASTIC_WHITE_BACKGROUND_COMPATIBLE;
- v0.7 accumulation gate: 4/4 directions pass;
- training discovery bins: 136-138;
- held-out raw rank p values approximately 0.003-0.005;
- held-out first-difference rank p values approximately 0.004-0.005.

Thus the new gate recovers a reproducible weak line that the fixed effect-size floor misses.

## Exploratory Monte Carlo

Prototype red-team before implementation:

White background, A=0.10 sigma, N=2048:

- 8 runs: about 14 percent detection;
- 16 runs: about 74 percent;
- 32 runs: 100 percent in 50 tested seeds;
- 64 runs: 100 percent in 50 tested seeds.

AR(1), phi=0.8, A=0.35 sigma, N=2048:

- 8 runs: 46/50;
- 16, 32 and 64 runs: 50/50 in the tested banks.

False-positive stress of the prototype:

- white: 0/100;
- AR(1): 0/50;
- 1/f: 0/50;
- one to three extreme sinusoidal outlier runs inside 16-run white stacks: 0/100 for each tested contamination count.

These finite banks do not establish a calibrated p-value or universal false-positive rate.

## Important statistical boundary

The frequency-rank number is an empirical holdout diagnostic, not yet a universally calibrated probability.

Frequency bins are not perfectly exchangeable under arbitrary colored/nonstationary spectra.

Therefore v0.7 explicitly records:

local_frequency_rank_is_diagnostic_not_fully_calibrated_p_value = true.

External Monte Carlo calibration must be indexed by background class and acquisition geometry before any discovery threshold is frozen.

## Low-frequency firewall

v0.7 inherits v0.6:

a candidate below the finite-window trend-ambiguity cycle guard remains

LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE

and cannot be upgraded through the accumulation path.

## Rule

More independent runs may increase evidence for a weak persistent structure.

More runs must not be converted into permission to lower a target-specific threshold after looking at the data.

Thresholds and background calibration remain preregistered.
