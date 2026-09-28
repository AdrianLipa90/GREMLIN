# GREMLIN Residual Red-Team v0.6

Status: CANDIDATE / MERCILESS VALIDATION / NO CANON PROMOTION

Date: 2026-09-28

## New failure pinned

v0.4/v0.5 can classify a strong smooth cubic baseline as a narrowband candidate.

Independent Monte Carlo reproduced the failure in 30/30 tested seeds for

- 16 runs;
- 2048 samples per run;
- cubic baseline amplitude 5 sigma relative to white-noise sigma;
- selected median discovery bin k=1.

The first-difference gate is therefore insufficient to separate a finite-window low-frequency trend from a narrowband process.

## v0.6 repair

v0.6 does not discard low-frequency structure and does not force a trend interpretation.

Any narrowband candidate with fewer than a declared number of cycles across the finite run is typed as

LOW_FREQUENCY_TREND_OR_NARROWBAND_AMBIGUOUS_CANDIDATE.

The default diagnostic guard is 3 cycles across the run.

This is a finite-window identifiability firewall:

trend-like structure and a sufficiently low-frequency oscillation may be observationally confounded on a short baseline.

A real low-frequency sinusoid is therefore preserved in the same ambiguous class rather than filtered out.

The ambiguity may be resolved only by a longer baseline or an independently justified trend model/control.

## Sensitivity red-team

Exploratory independent Monte Carlo also shows that detection sensitivity is strongly conditional on sample count and background.

White background, 16 runs, half-bin or integer narrow line:

- at 1024 samples/run, amplitude 0.10 sigma: 0/50 detections;
- at 1024 samples/run, amplitude 0.15 sigma: about 14-18 percent;
- at 1024 samples/run, amplitude 0.25 sigma: 50/50 detections.

Length scan for amplitude 0.10 sigma on white background:

- 512 samples/run: 0/30;
- 1024: 0/30;
- 2048: 2/30;
- 4096: 28/30.

AR(1), phi=0.8, amplitude 0.35 sigma:

- 512: 0/30;
- 1024: 0/30;
- 2048: 3/30;
- 4096: 26/30.

Therefore no single amplitude sensitivity threshold may be reported independently of run count, samples per run, background class and spectral location.

## False-positive stress

Independent exploratory Monte Carlo:

- white noise: 0/1000 false narrowband classifications for 16x512;
- white noise: 100/100 white-background compatible for 16x2048;
- AR(1), phi=0.8: 100/100 colored-background compatible;
- 1/f: 100/100 colored-background compatible;
- pure-noise nuisance families of size 1, 8, 16, 32 and 64: no false first-round acceptance observed in the tested seed banks.

These are finite Monte Carlo observations, not a proof of the nominal false-positive rate.

## Recursive error-control note

v0.5 introduced experimentwise alpha spending across planned recursive rounds.

Rare false accepts are still mathematically possible at nonzero alpha and must not be described as implementation failures merely because a seed exists.

The correct requirement is calibration of the empirical experimentwise false-discovery probability against the preregistered alpha budget.

## Claim boundary

A low-frequency ambiguity is not noise.

A narrowband classification is not physical attribution.

A phase-ordered classification is not new physics.

No residual class establishes time fluctuations.
