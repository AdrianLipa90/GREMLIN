# GREMLIN Acquisition-Bound PhaseNav IR v0.3

Status: IMPLEMENTED FEATURE-BRANCH CANDIDATE / no production execution authority / no canon promotion

## Purpose

Scalar acquisition v0.2 binds observed values to live NOEMA/CIEL producers and then into KAKU/Radical admission. v0.3 preserves that complete acquisition lineage across the next boundary into PhaseNav IR.

The route is:

```text
live NOEMA / CIEL observation
-> SCALAR_OBSERVATION_RECEIPT_V0_2
-> ACQUIRED_KAKU_SCALAR_PACKET_V0_2
-> ACQUIRED_RADICAL_SCALAR_ADMISSION_V0_2
-> PRE_VECTOR_ADMITTED
-> ACQUISITION_BOUND_PHASENAV_IR_V0_3
-> exact realization stage
```

## Full-envelope binding

The v0.3 record embeds the complete validated:

```text
acquired_radical_v02
```

rather than carrying only detached acquisition hashes.

The validator therefore re-validates the source acquired Radical envelope, including its nested acquired KAKU packets and scalar observation receipts, before accepting the PhaseNav binding.

## Materialized acquisition lineage

For UI, audit and inverse lineage, v0.3 also materializes a compact acquisition index:

```text
acquisition_lineage
  acquired_radical_commitment
  radical_observations
    <scalar name> -> observation_receipt_commitment
  ordered_kaku[]
    kaku_id
    acquired_kaku_commitment
    observations
      <scalar name> -> observation_receipt_commitment
```

This index is not an independent source of truth. During validation it is reconstructed from the embedded `acquired_radical_v02` and exact equality is required.

Therefore a copied lineage hash cannot diverge silently from its source envelope.

## PhaseNav binding

v0.3 delegates the actual scalar-admitted compilation to the existing:

```text
GREMLIN_SCALAR_ADMITTED_PHASENAV_IR_V0_2
```

That layer continues to require:

- a `PRE_VECTOR_ADMITTED` Radical;
- candidate/Radical identity equality;
- exact candidate relation lineage equality;
- hard-gate state:
  - consent `GRANTED`;
  - reversibility `SATISFIED`;
  - NO-GO `CLEAR`.

The resulting v0.3 object binds together:

```text
candidate identity
Radical identity
Radical scalar commitment
full acquired Radical envelope
materialized acquisition lineage
scalar-admitted PhaseNav IR v0.2
```

under one `acquisition_bound_ir_commitment`.

## Admission boundary

A blocked acquired Radical cannot enter v0.3 compilation.

In particular:

```text
consent DENIED/UNRESOLVED -> BLOCK
reversibility FAILED/UNRESOLVED -> BLOCK
NO-GO HIT/UNRESOLVED -> BLOCK
```

The acquisition layer therefore adds provenance without weakening the existing hard gates.

## Realization state

v0.3 remains before post-realization closure:

```text
realization_stage = ACQUISITION_BOUND_PHASENAV_IR_AFTER_PRE_VECTOR_ADMISSION
post_realization_complete = false
```

The existing v0.2 PhaseNav envelope still declares the required post-realization quantities:

```text
PHASE_COHERENCE_R_K
SEMANTIC_MASS
MASS_AWARE_GRAPH_COST
OPERATOR_STABILITY_BOUND
```

The next bridge is the exact T^36 realization binding and `POST_REALIZATION_ADMISSION` receipt.

## Authority state

v0.3 carries:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Pre-vector scalar admission and acquisition-bound PhaseNav compilation remain separate from production execution and canon authority.

## Validation

The v0.3 test suite covers:

- admitted acquired Radical -> PhaseNav IR construction;
- preservation of all KAKU and Radical observation receipt commitments;
- deterministic v0.3 commitment;
- rejection of a tampered nested observation receipt;
- rejection of divergence between materialized acquisition lineage and the embedded source envelope;
- denied-consent blocking;
- relation-lineage mismatch blocking;
- rejection of premature post-realization completion;
- outer commitment tamper rejection.

Unit fixtures are explicitly `TEST_FIXTURE_ONLY`. They exercise deterministic validation logic and do not act as an operational replacement for the live `/dev/shm/ciel_noema` acquisition path.
