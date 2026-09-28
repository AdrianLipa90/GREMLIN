# GREMLIN Residual Red-Team v0.10 — Shared-Run Leakage

Status: CANDIDATE / ADVERSARIAL / FAILURES PRESERVED / NO CANON PROMOTION

Date: 2026-09-28

## Objective

Attack residual spectroscopy as if every repeated structure were an artifact until the data defeat the artifact model.

The new failure mode is cross-run non-independence: train/holdout arrays are not independent evidence if they contain the same stochastic realization, overlapping windows, duplicated exposures, or shifted copies of one background realization.

## Pre-v0.10 failures preserved

Earlier red-team receipts pinned:

1. v0.2 promoted broad AR(1) colored noise to unresolved structured;
2. v0.2 lost offset sign and called alternating offsets persistent;
3. v0.2 exact-bin logic lost a half-bin weak line;
4. v0.3 accepted a pure-noise nuisance proxy while searching a 64-candidate family.

v0.4 introduced colored-noise typing, signed offsets, cross-fit band validation and familywise max-null control. v0.5-v0.9 added phase-trajectory, low-frequency ambiguity, weak replicate accumulation, spectral paths and transient cohorts.

## Shared-run leakage

Independent Monte Carlo against the v0.4-style cross-fit narrowband gate showed:

- independent white: 0/100 narrowband passes;
- independent AR(1), phi=0.8: 0/100;
- independent 1/f: 0/100;
- periodic heteroskedastic white noise: 0/100;
- shared-background pass rate rose sharply with shared variance;
- shifted copies of the same realization can also reproduce across folds.

Therefore cross-fit splitting does not establish replicate independence.

## Rejected fix 1: absolute correlation thresholds

After notching the candidate line, fixed thresholds on zero-lag and maximum circular cross-run correlation separated ordinary white/AR(1)/1/f from shared realizations.

They failed on independent long-memory processes.

Examples:

- n=256, AR(1) phi=0.95: 50/50 false flags;
- n=512, phi=0.95: 34/50;
- n=1024, phi=0.98: 40/50;
- n=2048, phi=0.99: 44/50.

Absolute correlation thresholds are therefore rejected as universal gates.

## Rejected fix 2: PSD-only phase-randomized surrogate

A phase-randomized null preserved each run's Fourier power spectrum and fixed the ordinary long-memory calibration substantially.

But it destroyed the empirical amplitude distribution and higher-order burst/volatility structure.

At alpha=0.05 with 63 null worlds, independent backgrounds produced false run-dependence flags:

- Student-t3: 5/20;
- GARCH-like volatility clustering: 3/20;
- bursty/spike noise: 20/20.

Therefore PSD preservation alone is insufficient.

## v0.10.2: IAAFT surrogate

v0.10.2 removes the candidate narrowband neighborhood and constructs independent IAAFT surrogates for every run.

IAAFT preserves:

- the empirical sample-value distribution exactly by rank remapping;
- the Fourier magnitude spectrum approximately by iterative amplitude adjustment.

Two cross-run statistics are evaluated:

- median absolute zero-lag pairwise correlation;
- median maximum circular pairwise correlation.

The observed pair is combined relative to the surrogate medians, and an empirical Monte-Carlo p-value is calculated.

Default gate:

- 127 IAAFT null worlds;
- alpha = 0.01;
- 20 IAAFT iterations;
- no absolute correlation threshold is authoritative;
- median surrogate PSD relative error >0.15 causes abstention.

## Extreme long-memory firewall

Near-unit-root finite-window processes can still violate surrogate calibration.

Long-memory is checked before candidate notching as well as after it, because notching a low-frequency candidate can hide the very persistence that invalidates the null.

If the conservative median |lag-1| reaches 0.97, v0.10.2 returns:

RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED

and invalidates cross-fit interpretation.

This is abstention, not a noise label.

## Independent reference Monte Carlo

Narrowband v0.4-style gate:

- white: 0/100 false narrowband;
- AR(1) phi=0.8: 0/100;
- 1/f: 0/100;
- periodic heteroskedastic: 0/100;
- stochastic quasi-oscillatory AR(2): 43/100 narrowband.

The AR(2) result is retained as genuine stochastic narrowband structure, not promoted to a coherent physical line.

Recursive familywise nuisance gate at alpha=0.05:

- pure-noise family size 1: 0/100 accepts;
- size 8: 0/100;
- size 32: 0/80;
- size 64: 0/60;
- true nuisance + 31 noise proxies: true accepted 30/30, extra false layer 0/30.

PSD-only phase randomization at alpha=0.05 exposed the heavy-tail/bursty failure above.

IAAFT at 31 null worlds, alpha=0.05:

- Student-t3: 0/10 false flags;
- GARCH-like: 0/10;
- bursty: 0/10;
- shared 20%: 10/10;
- shifted-copy white: 10/10;
- weak independent line: 0/10.

IAAFT at 127 null worlds, alpha=0.01:

- Student-t3: 1/20 flags in the larger calibration series;
- shared 20% deterministic reference: p=1/128;
- shifted-copy deterministic reference: p=1/128;
- independent weak line deterministic reference: p=0.9375;
- independent AR(1) phi=0.99 is routed to long-memory abstention before interpreting its surrogate p-value.

The Student-t3 1/20 result is not hidden: it is above the nominal point estimate but too small a sample to infer a stable tail error rate. Empirical calibration remains open.

## Claim boundary

Passing the run-independence audit does not prove that residual structure is physical.

Failing it does not prove instrumental origin.

It means only that the run set does not currently support an independent-replication interpretation of the cross-fit result.

Hierarchy:

RAW
-> residual preservation
-> nuisance/model provenance
-> replicate-independence audit
-> cross-fit structure
-> domain controls
-> independent dataset replication
-> interpretation last.
