# GREMLIN Evidence Origin Lineage v0.1

Status: `CANDIDATE_ONLY / CHYBA`

Authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## Purpose

Distinct documents, distinct provenance families and even correct evidence-kind labels do not prove that the underlying evidence is independent.

Two papers may reuse the same dataset, experiment or observation campaign. Evidence Origin Lineage adds an explicit, commitment-bound representation of the underlying origin used by direct evidence and conservatively collapses shared origins into one lineage group.

## Origin kinds

```text
EXPERIMENT
DATASET
OBSERVATION_CAMPAIGN
SIMULATION_RUN
DERIVATION_LINEAGE
ENGINEERING_TEST_SERIES
UNKNOWN
```

## Origin usage

```text
PRIMARY_GENERATION
REANALYSIS
REUSE
REPLICATION
DERIVED
UNKNOWN
```

A replication should use its own origin identifier when it represents a genuinely distinct underlying run. Reanalysis/reuse of the same dataset or experiment should reuse the same origin identifier.

## Assignment integrity

Every origin assignment binds to:

```text
source_id
content_commitment
origin_refs[]
producer_id
producer_version
model_id
mode
rationale_code
assignment_commitment
```

An origin ref contains:

```text
origin_id
origin_kind
usage
```

Origin assignments are candidate metadata. Their commitments prove what was assigned, not that the claimed lineage is physically or statistically independent.

v0.1 performs no automatic origin inference from titles, provider metadata or citation counts.

## Connected-lineage rule

For direct evidence sources, each source is represented by its set of known origin IDs.

Two source nodes are connected when their origin sets overlap.

Connected components are treated conservatively as one origin-lineage group:

```text
A uses X
B uses Y
C uses X and Y

=> {A, B, C} is one connected lineage group
```

Thus a bridge source can expose dependence between otherwise separate-looking evidence streams.

## Claim-mode defaults

Strict default minimum lineage groups:

```text
EMPIRICAL   -> 2
THEORETICAL -> 1
ENGINEERING -> 2
UNKNOWN     -> fail closed
```

Only evidence sources whose evidence kind counts as direct for the declared claim mode enter the origin-lineage gate.

Review/meta evidence does not create direct lineage groups for empirical claims merely by citing a primary source.

## Unknown origin

An explicit or missing `UNKNOWN` origin never counts as an independent lineage group.

If a direct evidence source lacks a known origin under strict mode, the result fails closed.

## Gate order

```text
semantic classification
 -> source/content/excerpt verification
 -> deterministic provenance-family binding
 -> family quorum
 -> evidence-kind verification
 -> claim-mode evidence-kind gate
 -> evidence-origin assignment verification
 -> origin-lineage connected-component gate
 -> synthesis retained or quarantined
```

Any SUPPORT/CONTRADICT conflict remains HOUND-controlled before origin counting.

## States

```text
EVIDENCE_ORIGIN_LINEAGE_SUFFICIENT
EVIDENCE_ORIGIN_LINEAGE_INSUFFICIENT
EVIDENCE_ORIGIN_ASSIGNMENT_INCOMPLETE
EVIDENCE_ORIGIN_ASSIGNMENT_INVALID
EVIDENCE_ORIGIN_UNKNOWN_FAIL_CLOSED
EVIDENCE_ORIGIN_CONFLICT_DEFER_TO_HOUND
NO_DIRECT_EVIDENCE_FOR_ORIGIN_POLICY
```

## Invariants

1. Distinct `source_id` or DOI values do not imply independent underlying evidence.
2. Direct sources sharing any known origin ID collapse into one connected lineage group.
3. A multi-origin bridge can join previously separate components.
4. Unknown origins do not count as independent lineage.
5. Origin assignments bind to exact source content commitments.
6. Origin lineage is explicit candidate metadata, not automatically inferred truth.
7. Family quorum and evidence-kind policy execute before origin-lineage policy.
8. Contradiction remains HOUND-controlled; origin count cannot vote away conflict.
9. Lineage-group count is not claimed as proof of causal/statistical independence.
10. Origin policy cannot grant production, execution or canon authority.
