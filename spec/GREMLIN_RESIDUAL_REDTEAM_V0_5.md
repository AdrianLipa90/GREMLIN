# GREMLIN Residual Red-Team v0.5

Status: CANDIDATE / MERCILESS VALIDATION / NO CANON PROMOTION

Date: 2026-09-28

## Purpose

v0.5 exists because v0.4 still had two unresolved methodological weaknesses:

1. narrowband structure did not distinguish ordered phase trajectories from phase-unordered narrowband processes;
2. familywise error was controlled inside each recursive round, but not across the full sequence of adaptive rounds.

Neither weakness justifies discarding residual structure. Both require tighter typing.

## Pinned earlier failures

The red-team keeps deterministic reproducers for failures discovered in earlier versions:

- AR(1) colored noise promoted by v0.2 to UNRESOLVED_STRUCTURED_CANDIDATE;
- alternating-sign run offsets promoted by v0.2 to a persistent-offset class;
- half-bin leakage causing a weak line to miss the v0.2 exact-bin gate;
- a 64-candidate pure-noise nuisance bank producing a false v0.3 acceptance.

v0.4 repaired these with colored-noise separation, signed offset typing, band-based cross-fit narrowband validation, and a within-round familywise max-null gate.

## New failure A: narrowband does not imply phase ordering

A fixed-frequency narrowband process with random phase between runs passes the v0.4 narrowband gate.

That is not a false spectral detection: the narrowband structure is real.

But it is a taxonomy failure if the same label is used for an ordered phase trajectory and a phase-unordered narrowband process.

v0.5 therefore adds a diagnostic phase-trajectory audit at the cross-fit-selected frequency.

For ordered runs, let

[
z_r = rac{langle r_r,e^{-i2pi k n/N}angle}
{|langle r_r,e^{-i2pi k n/N}angle|}.
]

The run-to-run phase increment is

[
q_r=z_{r+1}z_r^ast.
]

The observed increment coherence

[
R_Delta=left|rac1{R-1}sum_r q_right|
]

is compared with a content-addressed permutation null over run order.

A narrowband result is typed as one of:

- UNRESOLVED_NARROWBAND_PHASE_ORDERED_CANDIDATE;
- UNRESOLVED_NARROWBAND_PHASE_UNORDERED_CANDIDATE;
- UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE when run order is not declared meaningful.

These remain diagnostic subclasses only. Phase ordering is not physical attribution.

## New failure B: recursive rounds spend error repeatedly

A per-round familywise test at alpha does not by itself guarantee experimentwise alpha across adaptive recursive rounds.

v0.5 freezes a total

[
alpha_{m exp}
]

before the search and uses fixed Bonferroni spending across the planned maximum number of rounds,

[
alpha_{m round}
=
rac{alpha_{m exp}}{R_{m planned}}.
]

Within each round, the nuisance family is tested against the max-null distribution. Candidate familywise Monte Carlo p-values are computed by rank,

[
p
=
rac{1+#{M_bge T_{m obs}}}{B+1},
]

where (M_b) is the maximum null gain across the remaining nuisance family in null world b.

A candidate may enter only when

[
plealpha_{m round}.
]

The engine fails closed if the requested null ensemble cannot resolve the spent alpha:

[
rac1{B+1}>alpha_{m round}.
]

This is intentionally conservative.

## What remains deliberately open

- empirical calibration of power under strongly colored backgrounds;
- frequency-wandering or chirped structures;
- nonlinear nuisance transforms;
- hidden confounders not represented by source-owned channels;
- cross-instrument replication;
- physical interpretation of any surviving structure.

The current red-team already shows a real power trade-off: stricter gates sharply suppress false positives, but weak lines on strong AR(1) backgrounds can become false negatives. That is a sensitivity frontier, not a reason to lower thresholds after looking at the target data.

## Rule

A failure to classify a residual is not permission to erase it.

A successful classification is not permission to over-interpret it.

RAW and every residual layer remain preserved.
