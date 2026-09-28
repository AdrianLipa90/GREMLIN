# GREMLIN Residual Red-Team v0.9

Status: CANDIDATE / TRANSIENT COHORT PRESERVATION / NO CANON PROMOTION

Date: 2026-09-28

## Failure pinned

Persistent stack gates can miss a real structure that exists only during a short subset of ordered runs.

That is not evidence that the structure is noise. It is a different temporal support class.

A separate transient lane is required rather than lowering the persistence threshold.

## v0.9 transient cohort gate

Each run is split into two non-overlapping sample halves.

For every run:

1. the first half discovers its strongest locally normalized spectral feature;
2. the second half validates that first-half frequency by frequency rank;
3. the direction is reversed;
4. both directions must agree within two half-run bins and pass the declared rank threshold.

A run that passes is a reproducible single-run spectral anomaly diagnostic.

Single-run anomalies are not promoted to a top-level transient class because multiple testing across runs makes isolated hits expected.

If run order is declared meaningful, adjacent reproducible runs are clustered when their frequencies agree within the declared tolerance.

A top-level class requires at least two adjacent members:

UNRESOLVED_TRANSIENT_COHORT_STRUCTURE_CANDIDATE.

## Deterministic witness

Seed 340001, 16 runs x 2048 samples, white noise sigma 1, amplitude 0.8 sigma, line present only in runs 5-7.

The exploratory cross-half gate recovered a contiguous cohort [5,6,7].

The same data without declared run order cannot form a transient cohort.

## Exploratory Monte Carlo

Amplitude 0.8 sigma, 16x2048, fixed transient frequency:

- one active run: no cohort by construction; isolated run diagnostics can occur;
- two active runs: 17/50 cohort detections;
- three active runs: 26/50;
- four active runs: 37/50;
- six active runs: 42/50.

Null/background stress:

- white noise: 0/200 transient cohorts; 12/200 stacks contained an isolated reproducible-run diagnostic;
- AR(1), phi=0.8: 0/100 transient cohorts; 3/100 isolated diagnostics;
- 1/f: 0/100 transient cohorts; 0/100 isolated diagnostics.

These finite banks are exploratory and do not establish calibrated probabilities.

## Why isolated anomalies remain visible

An isolated reproducible run is not erased.

It is retained in the per-run audit with its two cross-half frequencies and rank values.

But v0.9 refuses to equate one isolated event with a persistent or cohort structure.

This separates information preservation from claim strength.

## Firewalls

- ordered-run provenance is required for cohort claims;
- single-run anomalies are diagnostic only;
- a transient cohort is not a physical mechanism;
- instrument, environment, clock, registration and acquisition-state controls remain mandatory;
- half-run rank values are diagnostic until background-class calibration is frozen;
- low-frequency ambiguity, fixed-frequency accumulation and frequency-wandering gates retain precedence where applicable.

## Rule

Persistence is one type of structure, not the definition of structure.

A transient state must not be deleted merely because it occupies a minority of the acquisition.
