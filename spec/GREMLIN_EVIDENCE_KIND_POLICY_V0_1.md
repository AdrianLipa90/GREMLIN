# GREMLIN Evidence Kind Policy v0.1

Status: `CANDIDATE_ONLY / CHYBA`

Authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## Purpose

Provenance-family diversity answers whether evidence comes from distinct deterministic source/work families. It does not answer what kind of evidence each source provides.

Evidence Kind Policy adds a separate, commitment-bound candidate classification for evidence type and prevents review/theory/simulation material from silently standing in for direct evidence when a claim mode requires direct validation.

## Evidence kinds

```text
PRIMARY_EXPERIMENT
OBSERVATIONAL
REPLICATION
DATASET_MEASUREMENT
THEORY_DERIVATION
SIMULATION
ENGINEERING_TEST
REVIEW_META
UNKNOWN
```

Evidence kind is never inferred automatically from title, provider metadata or source prestige in v0.1.

A missing kind becomes `UNKNOWN`.

## Claim modes

```text
EMPIRICAL
THEORETICAL
ENGINEERING
UNKNOWN
```

Missing or unknown claim mode fails closed in the strict bridge.

## Direct-evidence policies

### EMPIRICAL

At least one direct provenance family must contain one of:

```text
PRIMARY_EXPERIMENT
OBSERVATIONAL
REPLICATION
DATASET_MEASUREMENT
```

### THEORETICAL

At least one direct provenance family must contain:

```text
THEORY_DERIVATION
```

`SIMULATION` may support a theoretical claim but does not replace an explicit derivation under this strict v0.1 policy.

### ENGINEERING

At least one direct provenance family must contain:

```text
ENGINEERING_TEST
REPLICATION
```

Simulation remains useful evidence but does not replace implementation/test evidence in the strict profile.

## Assignment integrity

Every evidence-kind assignment binds to:

```text
source_id
content_commitment
evidence_kind
producer_id
producer_version
model_id
mode
rationale_code
assignment_commitment
```

The assignment is accepted only when its `source_id` and `content_commitment` match a verified source receipt from the same execution.

The evidence kind itself remains candidate metadata; its commitment proves what was assigned, not that the assignment is semantically correct.

## Gate order

Strict pipeline:

```text
semantic classification
  -> source/content/excerpt verification
  -> deterministic provenance-family binding
  -> provenance-family quorum
  -> evidence-kind assignment verification
  -> claim-mode evidence-kind policy
  -> candidate synthesis remains or is quarantined
```

Contradiction handling remains earlier and stronger:

```text
SUPPORT + CONTRADICT -> HOUND
```

Evidence kind cannot majority-vote or type-vote a contradiction away.

## States

```text
EVIDENCE_KIND_POLICY_SUFFICIENT
EVIDENCE_KIND_POLICY_INSUFFICIENT
EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE
EVIDENCE_KIND_ASSIGNMENT_INVALID
CLAIM_MODE_UNKNOWN_FAIL_CLOSED
EVIDENCE_KIND_CONFLICT_DEFER_TO_HOUND
NO_RESOLVED_EVIDENCE
```

Strict bridge quarantine statuses include:

```text
SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INVALID
SEMANTIC_EVIDENCE_KIND_ASSIGNMENT_INCOMPLETE
SEMANTIC_EVIDENCE_KIND_POLICY_INSUFFICIENT
SEMANTIC_CLAIM_MODE_UNKNOWN_FAIL_CLOSED
```

## Invariants

1. Evidence kind is explicit candidate metadata, not inferred from title/provider metadata.
2. Missing evidence kind becomes `UNKNOWN`.
3. Evidence-kind assignments must bind to exact execution source content commitments.
4. Provenance-family quorum is evaluated before evidence-kind policy.
5. Review/meta evidence does not silently become direct empirical evidence.
6. Simulation does not silently become theory derivation or engineering test evidence.
7. Unknown claim mode fails closed in the strict bridge.
8. SUPPORT/CONTRADICT conflict remains under HOUND and cannot be resolved by evidence type.
9. Evidence-kind policy cannot grant canon, production-write or execution authority.
10. Existing family-quorum and semantic bridges remain available independently; this is an additional strict profile.
