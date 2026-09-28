# GREMLIN residual red-team v0.5 findings

Status: MIXED / PHASE-AXIS CANDIDATE PASS / RECURSIVE GLOBAL-ALPHA CANDIDATE FAIL

Date: 2026-09-28

## v0.4 failures pinned

Two distinct v0.4 gaps are preserved as deterministic reproducers.

1. Recursive alpha refresh:
   after a true nuisance layer is accepted, a later round can admit a pure-noise proxy because each round receives a fresh familywise alpha.

2. Narrowband semantics:
   stable narrowband power with random run-to-run phase is typed the same way as a phase-related line.

## v0.5 phase-axis result

The v0.5 phase layer separates narrowband power from a run-index phase relation.

The final candidate gate requires all four out-of-fold phase-law validations to reach holdout coherence >= 0.70.

Red-team calibration:

- 2,000 random-phase trials: 0 false run-phase-relation promotions;
- weak linear phase law, amplitude 0.10 noise sigma: 41/50 pass;
- the run index is not physical time;
- phase relation is not a mechanism assignment.

This part remains a CANDIDATE PASS.

## v0.5 recursive global-alpha result

A simple global alpha budget does not close adaptive recursive selection.

Paired Monte Carlo after one real nuisance layer:

- fresh per-round alpha 0.01: 10/1000 false additional nuisance layers;
- global two-round budget alpha_round=0.005: 9/1000 false additions.

A stricter trial using alpha_round=0.00125 and 1023 null worlds still produced 1/500 false additions.

Therefore:

[
\boxed{\text{v0.5 global-alpha recursion: FAIL}}
]

The branch code is retained as an explicit failed candidate, not promoted.

## Why the failure matters

Within-round familywise control does not by itself protect against an adaptive path that is repeatedly selected on the same observations.

Finite Monte Carlo p-resolution and repeated search/configuration are additional attack surfaces.

A frozen analysis-plan hash is necessary but not sufficient.

## Next gate

The next candidate is a sealed A/B/C design:

- A: discovery and coefficient fitting only;
- B: independent confirmation with no refit;
- C: independent replication with no refit.

A candidate layer must first pass the full A discovery gate and then independently survive B and C.

Initial faithful synthetic results:

- pure false additions: 0/1000 promoted through A/B/C;
- true second layer amplitude 0.20 sigma: 40/100 promoted;
- amplitude 0.30 sigma: 89/100;
- amplitude 0.40 sigma: 97/100.

These numbers are synthetic calibration, not empirical instrument performance.
