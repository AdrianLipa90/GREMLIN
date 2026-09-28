# GREMLIN Residual Red-Team v0.20 — Shared Sample-Index Confound Firewall

Status: CANDIDATE / SHARED-ENVELOPE FIREWALL / NO CANON PROMOTION

Date: 2026-09-28

## New no-go from v0.19 operator matrix

v0.19 established that dependence must be tested before destructive preprocessing.

The same m=17 deterministic Chebyshev witness was passed through several common operators.

With a content-addressed 199-world joint IAAFT KSG audit:

- RAW: p=0.005, correct witness pair (0,1);
- per-run z-score: p=0.005, correct witness pair;
- linear detrend: p=0.095;
- first difference: p=0.115;
- 5-sample moving average: p=0.12;
- notch around bin 20: p=0.39.

Thus non-invertible temporal preprocessing can remove detectable dependence.

A common Hann window exposed the opposite failure mode.

Independent white runs multiplied by the same Hann envelope produced a strict dependence rejection and a family maximum on an unrelated run pair.

Therefore:

[
\boxed{
\text{preprocessing can erase dependence}
\quad\text{or}\quad
\text{preprocessing can create apparent dependence}.
}
]

## Why common windows create a confound

If every run shares the same deterministic sample-index envelope, then sample index becomes a common latent coordinate.

Even with independent innovations, paired samples from different runs can share scale or location structure conditional on that common coordinate.

This is not equivalent to stochastic run coupling.

Therefore a shared envelope must be typed as a confound and modeled explicitly, not interpreted as a hidden common physical mechanism.

## v0.20 shared-profile audit

Split each RAW residual run into eight contiguous blocks.

For every run build two robust profiles:

- block location: block median relative to the run global MAD scale;
- block scale: log(block MAD / global MAD).

Across all run pairs compute:

- median pairwise scale-profile correlation;
- median pairwise location-profile correlation.

The observed statistic is the larger of the two.

The null independently circular-shifts each complete run by a content-addressed random offset.

This preserves each run's values and internal pattern while breaking common sample-index alignment.

The family over location-vs-scale is paid inside the max statistic.

Monte-Carlo p-value:

[
p=
\frac{1+\#\{T_{\rm shift}\ge T_{\rm obs}\}}
     {B+1}.
]

## Prototype detection

At alpha 0.005, 199 shift-null worlds, 8 runs x 256 samples:

Five seeds each:

- Hann-windowed independent white: 5/5 detected as shared scale profile;
- shared sinusoidal location envelope: 5/5 detected;
- shared multiplicative scale envelope: 5/5 detected.

All detections reached the minimum p=1/200=0.005.

## Independent controls

Five seeds each under the same gate:

- white Gaussian: 5/5 no false confound;
- AR(1), phi=0.8: 5/5;
- GARCH-like: 5/5;
- bursty heavy-tail: 5/5.

Total exploratory controls: 20/20 without false confound.

This is not a formal FPR bound.

## Pipeline order

The v0.20 ordering is:

[
\boxed{
RAW
\to
\text{shared sample-index confound audit}
\to
\text{RAW run-dependence audit}
\to
\text{only then domain preprocessing}.
}
]

If the shared-profile gate rejects, the status is

RAW_SHARED_SAMPLE_INDEX_CONFOUND_REQUIRES_MODELING.

The next action is to model or provenance-bind the shared window/gain/drift.

It is not to declare stochastic run dependence.

## Claim boundary

A shared-profile reject does not identify cause.

A shared-profile PASS does not prove stationarity.

Circular-shift calibration tests alignment, not every form of nonstationarity.

The gate does not establish physical mechanism, new physics or time fluctuations.
