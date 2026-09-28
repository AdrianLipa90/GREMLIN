# GREMLIN Residual Red-Team v0.13 — Sealed Confirmation

Status: CANDIDATE / POST-SELECTION CONFIRMATION / NO CANON PROMOTION

Date: 2026-09-28

## Failure pinned

v0.5 correctly introduced experimentwise alpha spending across adaptive recursive rounds.

That controls the discovery procedure, but it cannot make the type-I error probability zero.

A deterministic reproducer was found at seed 30116:

- 8 runs x 128 samples;
- three real nuisance channels with coefficients 0.6, 0.5 and 0.4;
- five independent noise-proxy channels;
- v0.5 discovery with experimentwise alpha 0.01 and 1023 null worlds;
- the three real channels are accepted;
- a fourth pure-noise channel, noise_01, is also accepted in round 4;
- its familywise Monte-Carlo p value is the minimum resolvable value 1/1024.

This is not a contradiction of alpha control. It is an allowed rare type-I event.

For high-consequence interpretation, discovery therefore cannot be the final gate.

## v0.13 repair

v0.13 adds a sealed confirmatory dataset after the recursive discovery search is complete.

The confirmation rules are deliberately asymmetric:

1. the confirmatory dataset must be declared sealed before discovery;
2. it must be a distinct dataset; reusing the discovery RAW fails closed;
3. the nuisance components must be independently available on the confirmatory dataset;
4. all discovery coefficients are frozen;
5. no coefficient may be refit on confirmation;
6. every selected discovery layer receives a drop-one confirmatory gain;
7. each selected layer is compared with a typed null ensemble;
8. familywise max-null control is applied across all selected layers in the single confirmatory stage.

A discovery layer that fails confirmation is retained in provenance but is not confirmed.

## Seed 30116 witness

Using an independent confirmatory realization and the frozen discovery coefficients:

- true_0 confirmatory gain: about 0.282;
- true_1: about 0.169;
- true_2: about 0.148;
- noise_01: about -0.024.

The three true layers pass the confirmatory familywise gate.

The false discovery layer fails.

Thus:

selection != confirmation.

## Claim boundary

A confirmed nuisance relation is still not unique causal attribution.

A sealed-confirmation PASS does not establish a physical mechanism.

A surviving residual remains unresolved until domain controls and independent physical replication.

No confirmation result establishes new physics or time fluctuations.
