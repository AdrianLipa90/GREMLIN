# GREMLIN Residual Red-Team v0.14 — Finite-Window Identifiability

Status: CANDIDATE / BASELINE-EXTENSION DIAGNOSTIC / NO MECHANISM PROMOTION

Date: 2026-09-28

## Failure pinned

A reproducible narrowband peak is not enough to distinguish a deterministic line from a stochastic high-Q resonator on a finite observation window.

Independent red-team witnesses used an AR(2) process

x_t = 2 r cos(omega) x_(t-1) - r^2 x_(t-2) + epsilon_t

with r close to one.

For r=0.9998 at N=4096, the stochastic process can have within-run segment phase coherence overlapping a weak deterministic sinusoid at amplitude 0.10 sigma.

Changing the number of phase segments also changes the absolute coherence strongly. In one tested bank, at N=4096:

- 4 segments: AR(2) median about 0.85, line about 0.93;
- 8 segments: AR(2) about 0.78, line about 0.80;
- 16 segments: AR(2) about 0.76, line about 0.65.

Therefore no universal absolute coherence threshold is admitted.

## Rejected repair: IAAFT coherence null

An IAAFT null preserving the empirical marginal and approximately the power spectrum was also tested against within-run phase coherence.

Both a deterministic weak line and an extreme high-Q stochastic resonator could beat the surrogate coherence null on the same finite window.

This is retained as a no-go for one-window mechanism identification, not hidden as a failed tuning attempt.

## v0.14 diagnostic

The candidate frequency is frozen before the baseline-extension audit.

The same frequency in cycles/sample is evaluated on increasingly long observation baselines. For each baseline, median within-run segment phase coherence is computed independently for several preregistered segment counts.

The default diagnostic segment family is 4, 8 and 16.

The code does not ask whether coherence is above a magic threshold. It asks whether the direction of coherence change with increasing baseline is consistent across segmentations.

Possible statuses:

- COHERENCE_STRENGTHENS_WITH_BASELINE_CANDIDATE;
- COHERENCE_DECAYS_WITH_BASELINE_CANDIDATE;
- BASELINE_EXTENSION_AMBIGUOUS;
- INSUFFICIENT_BASELINE_EXTENSION.

None identifies a physical mechanism.

## Corrected baseline witness

An earlier exploratory scan accidentally held Fourier-bin index fixed while changing N. That scan is rejected as evidence for a fixed-frequency process.

The corrected scan holds physical/normalized frequency fixed:

f0 = 137.5 / 4096 cycles/sample,

so the expected bins are 137.5, 275 and 550 for N=4096,8192,16384.

Across an independent 12-seed exploratory bank with 8 segments:

high-Q AR(2), r=0.9998:
- N4096 median coherence about 0.801;
- N8192 about 0.744;
- N16384 about 0.612.

weak deterministic line, A=0.10 sigma:
- N4096 about 0.798;
- N8192 about 0.912;
- N16384 about 0.959.

Thus the mechanisms are badly overlapped at the shortest window while the baseline extension exposes different phase-stability behavior in this witness.

## Exact test seeds

The committed test seeds give endpoint changes N4096 -> N16384:

deterministic-line witness:
- 4 segments: +0.0781;
- 8 segments: +0.2157;
- 16 segments: +0.3646.

high-Q AR(2) witness:
- 4 segments: -0.0596;
- 8 segments: -0.2701;
- 16 segments: -0.2158.

These are synthetic witnesses, not universal effect sizes.

## Claim boundary

Coherence strengthening with baseline does not prove a deterministic physical oscillator.

Coherence decay does not prove stochastic origin.

A deterministic chirp, clock error, instrument drift, changing amplitude/SNR, nonlinear observation operator or nonstationary stochastic process can alter these trends.

The diagnostic only records finite-window identifiability behavior.

Independent dataset replication and domain controls remain mandatory.

No result establishes new physics or time fluctuations.
