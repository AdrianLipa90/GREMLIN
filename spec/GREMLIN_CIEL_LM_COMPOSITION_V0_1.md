# GREMLIN CIEL-LM Composition v0.1

Status: `CANDIDATE_ONLY / PREREGISTRATION_REQUIRED_FOR_NEXT_BENCHMARK`

## Purpose

This specification records the GREMLIN/BEELZEBUB composition frontier obtained from the bounded CIEL-LM text-generation audits. GREMLIN remains the candidate generator/auditor; promotion requires an explicit validation path.

## Evidence carried forward

The text-only experiments separated several mechanisms rather than treating CIELingo/Lingophysics as one undifferentiated sidecar.

| Experiment | Mechanism | Result |
| --- | --- | --- |
| V0.3 | full attention + SentenceEquation global conditioning, whole-file holdout | `BLOCK_REPLICATION`, mean delta NLL `-0.03313` |
| V0.4 | attention-only, independent file holdout | `BLOCK`, mean delta NLL `-0.00122` |
| V0.5 | relation-excess attention pilot | frozen pilot gate passed, mean delta NLL `+0.002399` |
| V0.6 | independent relation-excess confirmation | `BLOCK_CONFIRMATION`, mean delta NLL `-0.000375`, 7/12 positive, sign-flip p=`0.6951` |
| V0.7 | training-only Lingophysics auxiliary objectives through shared backbone | `BLOCK`, mean delta NLL `-0.02744`, 2/12 positive, sign-flip p=`0.9993` |

V0.7 auxiliary loss fell from approximately `0.347` to `0.264`, showing that the auxiliary labels were learnable while the language objective exhibited negative transfer in that architecture.

## Upstream binder finding

The CIELingo regional binder audit identified two concrete defects:

1. atlas shadowing: the loader selected the first materialized atlas and therefore preferred the controlled 24-slot file while a deterministic 48-slot atlas generator already existed;
2. substring overbinding: `fl in token or token in fl` emitted broad score-0.75 candidates for unrelated short forms.

The repair contract is `CIELINGO_BINDER_REPAIR_SPEC_V0_8`, frozen SHA-256:

`cbdeb0cb6db1d0df5ec2de524ccabc1328d1bc4d4fd1e13a236e9328cdb0ae64`

## Lingophysics attention decomposition

For the v1.9 attention rules, the pair score can be exposed as

```text
B_pair = B_operator_argument
       + B_same_event_frame
       + B_case_role
       + B_phase_compatibility
       - B_conflict
```

The configured compatible-phase contribution is `+0.45`. For an otherwise neutral pair this term is common to every non-self key. The new diagnostic `relation_excess` exposes the typed relation/conflict contribution separately while preserving the existing `pair_bias` interface.

## Selected GREMLIN candidate

The next composition candidate protects the lexical prior and isolates structural learning:

```text
text tokens
   -> base decoder LM ---------------------------> base logits
          |                                           |
          | frozen/preserved lexical backbone         |
          v                                           v
   CIELingo repaired binder -> Lingophysics graph -> residual/reranking expert
                                                      |
                                                      v
                                             candidate logits/ranking
```

A minimal residual form is

```text
L_final = L_base + g(x) * R_CIEL(x)
```

with the following admission requirements:

- `R_CIEL` starts at exact zero, so the initial model reproduces the base LM;
- the base lexical backbone has gradient isolation from the structural expert;
- CIELingo binding uses the repaired exact-boundary matcher and 48-slot priority;
- GREMLIN/BEELZEBUB may emit candidate architectures and falsification tests;
- benchmark thresholds, files, seeds and the residual gate are frozen before the next outcome is observed;
- any positive result requires an independent whole-file replication before promotion.

A reranking variant may instead score base-LM beam candidates with a bounded CIEL structural score. The baseline beam and candidate set must be identical between arms.

## Required falsification tests

1. zero residual reproduces base logits exactly;
2. shuffled CIEL relations provide a negative control;
3. binder regression rejects substring-only card matches;
4. base-LM parameters remain byte-identical in a frozen-backbone experiment;
5. held-out NLL/perplexity and generation quality are evaluated on file-disjoint data;
6. independent replication uses new holdout files and new seeds;
7. GREMLIN output remains `CANDIDATE_ONLY` until the declared gates pass.

## Current disposition

`CIEL_BINDER_REPAIR -> VALIDATE -> FROZEN_BASE_RESIDUAL_EXPERT -> PREREGISTERED_A/B`

`canon_allowed=false`
