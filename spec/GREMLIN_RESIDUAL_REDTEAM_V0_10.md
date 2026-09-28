# GREMLIN Residual Red-Team v0.10 — Shared-Run Leakage

Status: CANDIDATE / ADVERSARIAL / FAILURES PRESERVED / NO CANON PROMOTION

Date: 2026-09-28

## Objective

Attack residual spectroscopy as if every apparent repeated structure were an artifact until the data defeat the artifact model.

The key new failure mode is cross-run non-independence.

Cross-fit is not valid merely because arrays were split into train and holdout sets. If both sets contain the same stochastic realization, overlapping windows, duplicated exposures, or shifted copies of one background realization, a persistent spectral feature can reproduce across folds without being an independent replication.

## Failures found before v0.10

Earlier red-team work already pinned four failures:

1. v0.2 promoted broad AR(1) colored noise to unresolved structured;
2. v0.2 lost offset sign and called alternating offsets persistent;
3. v0.2 exact-bin logic lost a half-bin weak line;
4. v0.3 accepted a pure-noise nuisance proxy when searching a 64-candidate family.

v0.4 addressed those with colored-noise typing, signed offsets, cross-fit band validation, and familywise max-null control.

Subsequent v0.5-v0.9 added phase-trajectory, low-frequency ambiguity, weak replicate accumulation, spectral paths, and transient cohorts.

## New failure: shared-run leakage

Independent Monte Carlo against the v0.4-style cross-fit narrowband gate showed that shared background realizations can pass as repeated structure.

For 100 experiments of 16 runs x 2048 samples:

- independent white noise: 0/100 narrowband passes;
- independent AR(1), phi=0.8: 0/100;
- independent 1/f: 0/100;
- periodic heteroskedastic white noise: 0/100;
- 50% shared white-noise variance: 8/100 at 50% sharing, 34/100 at 80%, 58/100 at 95%, 65/100 at 99%, and 73/100 for identical shared realizations in the original stress series.

This demonstrates that train/holdout splitting does not itself establish replicate independence.

## Rejected fix: absolute correlation thresholds

A first attempted firewall used absolute background-correlation thresholds after notching the candidate line.

It worked on ordinary white/AR(1)/1/f cases, but failed on independent long-memory processes.

Examples from 50-seed stress tests:

- n=256, AR(1) phi=0.95: false run-dependence flag 50/50;
- n=512, phi=0.95: 34/50;
- n=1024, phi=0.98: 40/50;
- n=2048, phi=0.99: 44/50.

Therefore fixed 0.10/0.35 correlation thresholds are rejected as universal gates.

## v0.10 relation-preserving surrogate test

v0.10 removes the candidate narrowband neighborhood, then constructs independent phase-randomized surrogates for every run.

Each surrogate preserves that run's Fourier power spectrum, and therefore its second-order spectral/autocorrelation structure, while destroying the specific cross-run phase relation.

Two cross-run dependence statistics are measured:

- median absolute zero-lag pairwise correlation;
- median maximum circular pairwise correlation.

They are combined relative to the surrogate medians, and a Monte-Carlo p-value is calculated from the surrogate ensemble.

Default gate:

- 255 null worlds;
- alpha = 0.01;
- no absolute correlation threshold is authoritative.

## Extreme long-memory firewall

Finite-window near-unit-root processes can still violate the phase-randomization calibration.

Independent AR(1) phi=0.99 produced an elevated false-flag rate under a looser alpha=0.05 surrogate audit.

Therefore v0.10 does not force a binary decision when median background |lag-1| >= 0.97.

It returns:

RUN_DEPENDENCE_AUDIT_LONG_MEMORY_UNCALIBRATED

and invalidates cross-fit interpretation until a long-memory-specific calibration is supplied.

This is an abstention, not a noise label.

## Independent reference Monte Carlo

Narrowband v0.4-style gate, 100 seeds each:

- white: 0/100 false narrowband;
- AR(1) phi=0.8: 0/100;
- 1/f: 0/100;
- periodic heteroskedastic: 0/100;
- stochastic quasi-oscillatory AR(2): 43/100 narrowband.

The AR(2) result is not treated as a false positive: it is genuinely narrowband stochastic structure. It motivated the later phase-trajectory typing rather than deletion as noise.

Recursive nuisance familywise gate at alpha=0.05:

- pure-noise family size 1: 0/100 accepts;
- size 8: 0/100;
- size 32: 0/80;
- size 64: 0/60.
- true nuisance + 31 noise proxies: true nuisance accepted 30/30, extra false layer 0/30.

v0.10 surrogate calibration, representative 255-null experiments at alpha=0.01:

- independent white: 0/12 shared-run flags;
- shared 20% white background: 12/12;
- shifted copies of one white realization: 12/12;
- independent AR(1) phi=0.99: 1/12 raw surrogate flags, but median lag-1 ~0.982 activates the long-memory abstention.

Deterministic reference seeds with 127 nulls:

- shared 20%: p = 1/128;
- shifted copy: p = 1/128;
- independent weak line: p = 0.953125;
- independent AR(1) phi=0.99: lag-1 ~0.983, therefore abstain.

## Claim boundary

Passing the run-independence audit does not prove that a residual structure is physical.

Failing it does not prove that the repeated structure is instrumental.

It means only that the data do not supply independent replication for the cross-fit claim.

The correct hierarchy is:

RAW
-> residual preservation
-> nuisance/model provenance
-> replicate independence
-> cross-fit structure
-> domain controls
-> independent dataset replication
-> interpretation last.
