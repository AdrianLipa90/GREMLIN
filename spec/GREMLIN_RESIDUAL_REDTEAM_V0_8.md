# GREMLIN Residual Red-Team v0.8

Status: CANDIDATE / FREQUENCY-WANDERING SPECTRAL PATH / NO CANON PROMOTION

Date: 2026-09-28

## Failure pinned

v0.4-v0.7 assume that a reproducible narrowband structure remains near one frequency bin across runs.

A line whose frequency changes systematically between runs can therefore disappear from the stacked fixed-frequency spectrum.

Synthetic linear frequency wander with

k_i = k_0 + delta_k i

was missed by the fixed-bin stack across all tested 30-seed banks at amplitudes 0.2, 0.4, 0.8 and 1.2 sigma.

That is a false-negative mode, not evidence that the moving structure is noise.

## v0.8 spectral-path gate

v0.8 keeps all previous fixed-frequency gates and adds a separate preregistered path family.

Current path family:

k(i) = k_mid + s (i-i_mid)

with a declared finite slope bank.

For every directed cross-fit:

1. build per-run locally normalized spectral-prominence curves;
2. search (k_mid,s) only on training runs;
3. evaluate the selected path on held-out runs;
4. rank its held-out score against the complete preregistered path bank;
5. repeat on a first-difference analysis copy;
6. require at least 3/4 fold passes;
7. require agreement of both mid-frequency and slope across folds.

A nonzero stable slope is required for the frequency-wandering class.

The class is

UNRESOLVED_FREQUENCY_WANDERING_STRUCTURE_CANDIDATE.

It is not physical attribution.

## Deterministic witness

Seed 250000:

- 16 runs x 2048 samples;
- white noise sigma 1;
- line amplitude 0.4 sigma;
- k0=120;
- drift 0.75 bin/run.

The prototype gate passed 4/4 directed folds.

Recovered fold path slopes were 0.75-1.0 bin/run and mid-frequency approximately 124-125 bins.

The existing v0.7 fixed-frequency accumulation path did not recover this class.

## Exploratory red-team

Small independent seed banks for the spectral-path prototype:

False path detections:

- white: 0/20;
- AR(1), phi=0.8: 0/10;
- 1/f: 0/10;
- random run-by-run frequencies: 0/20.

Linear-wander power, 16x2048, drift 0.75 bin/run:

- amplitude 0.10 sigma: 5/20;
- amplitude 0.20 sigma: 17/20;
- amplitude 0.40 sigma: 17/20.

These are exploratory finite banks, not calibrated detection probabilities.

## Firewalls

The path bank must be declared before target inspection.

The current linear path family is not universal.

A curved/chirped/nonlinear path that does not fit this bank remains unresolved rather than being called noise.

Low-frequency finite-window ambiguity from v0.6 still has precedence.

Instrument drift, clock drift, pixel registration and wavelength calibration can all generate frequency paths and must be tested downstream before interpretation.

The empirical frequency-rank values are diagnostics, not universally calibrated p-values.

## Rule

Moving structure is still structure.

Failure of a fixed-bin model is not permission to erase a reproducible spectral trajectory.
