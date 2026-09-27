# GREMLIN Recursive Residual Decomposition v0.3

Status: CANDIDATE / RECURSIVE / CROSSFIT-GATED / PHASE-SCRAMBLED-NULL / INTERPRETATION-LAST

Date: 2026-09-27

## Principle

Residual layers may contain several superposed mechanisms. A new nuisance layer is not admitted because it improves the same-data fit.

For each frozen nuisance candidate the engine evaluates incremental explanatory value on held-out runs under four directed cross-fit surfaces:

- even runs -> odd runs;
- odd runs -> even runs;
- first half -> second half;
- second half -> first half.

A layer is admitted only if its conservative holdout gain passes a fixed minimum, beats a phase-scrambled null candidate, and keeps a stable coefficient sign across the cross-fit surfaces.

## Null control

The null twin of a nuisance channel is built by a deterministic per-run circular shift.

This preserves the channel's per-run power spectrum exactly while breaking the original phase/time alignment used for attribution.

Therefore a spectral match alone is insufficient: the aligned nuisance must predict held-out raw data better than its spectrum-preserving scrambled twin.

## Provenance firewall

Every nuisance component must be frozen before the target fit and independently sourced as one of:

- instrument channel;
- environment channel;
- clock channel;
- preregistered template;
- known systematic template.

Target-derived nuisance candidates are rejected before fitting.

Raw data are never rewritten. Every accepted stage has separate RAW, MODEL and RESIDUAL commitments plus a previous-stage hash, producing an append-only decomposition chain.

## Ordering rule

Input mapping order is non-authoritative.

At each round the engine evaluates every remaining candidate conditionally on all accepted components and selects the maximum

[
	ext{conservative holdout gain}
-
	ext{conservative phase-scrambled-null gain}.
]

A lexical tie break is used only after the numerical scores.

After each acceptance all accepted coefficients are jointly refit, so the model is not a sequence of irreversible destructive subtractions.

## Alias / attribution firewall

Highly correlated nuisance channels are recorded as alias pairs.

If an accepted component has an alias, the engine may close the predictive decomposition while leaving mechanism attribution OPEN:

[
oxed{	ext{predictive nuisance removal} 
eq 	ext{unique causal attribution}.}
]

## Discovery layer

After the accepted nuisance set is jointly modeled, the unchanged raw acquisition is passed again through Residual-Preserving Spectroscopy v0.2.

A remaining structured residual may therefore surface after several independently justified nuisance layers.

It remains an UNRESOLVED structure until downstream instrument/environment/clock, sampling/alias, known-physics and independent-replication gates are passed.

No decomposition stage may establish new physics or time fluctuations by itself.
