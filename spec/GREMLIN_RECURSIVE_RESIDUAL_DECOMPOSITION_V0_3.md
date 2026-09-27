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

A layer is admitted only if its conservative holdout gain passes a fixed minimum, beats the q0.90 gain of a typed content-addressed null ensemble, and keeps a stable coefficient sign across the cross-fit surfaces.

## Typed null ensemble

The null policy is frozen in nuisance provenance.

Two v0.3 null policies are admitted:

- sample_circular_shift: for phase/spectral templates; each proxy preserves the per-run power spectrum while changing sample/phase alignment;
- run_permutation: for measured instrument/environment/clock channels; each proxy preserves complete run observations while changing run-to-channel alignment.

Null generation is content-addressed, not label-addressed, so identical nuisance arrays receive identical null ensembles regardless of channel naming.

The engine evaluates an ensemble of deterministic null proxies and uses the q0.90 conservative null gain. Therefore admission is not controlled by one lucky or unlucky scramble.

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
