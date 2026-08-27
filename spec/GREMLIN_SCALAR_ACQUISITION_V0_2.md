# GREMLIN Scalar Acquisition v0.2

Status: IMPLEMENTED FEATURE-BRANCH CANDIDATE / live NOEMA acquisition path / no production execution authority / no canon promotion

## Purpose

v0.1 introduced scalar-first KAKU and Radical admission. v0.2 closes the provenance gap between a scalar value and the system that produced the observation.

The acquisition route is:

```text
live NOEMA / CIEL source
-> deterministic extraction
-> GREMLIN_SCALAR_OBSERVATION_RECEIPT_V0_2
-> acquired KAKU packet
-> acquired Radical admission
-> existing PRE_VECTOR_ADMISSION
```

A scalar value is therefore accompanied by an exact source snapshot hash, extraction description, live-surface witness and content commitment before it enters KAKU/Radical composition.

## Producers

### NOEMA_LIVE_F64

Reads a contained relative file from the canonical operational surface:

```text
/dev/shm/ciel_noema
```

Supported deterministic reducers are:

```text
INDEX
MEAN
RMS
CIRCULAR_COHERENCE
```

The acquisition function requires:

- `/dev/shm/ciel_noema/ciel_binding_status == ACTIVE`;
- `tether_runtime_status.json.status == ACTIVE`;
- `phi` exactly 36 finite little-endian float64 values;
- the requested source to be a contained file under the live root.

The root is fixed. A temporary, repository, Library or arbitrary filesystem path cannot be substituted through the acquisition API.

### CIEL_NOEMA_JSONL_FIELD

Reads a live CIEL/PhaseNav registry under:

```text
/dev/shm/ciel_noema/phasenav/*.noema.jsonl
```

Selection requires an exact key/value match resolving to one record and a finite numeric field. The receipt binds both the complete source file hash and the selected JSONL record hash.

## Semantic adapter boundary

Acquisition records the actual source quantity and an explicit semantic adapter identity. It does not silently rename a measured field into another semantic quantity.

For example, the live witness reads the `coherence_R` field from the CIEL record named `Intention`, but preserves it as a coherence probe. The witness does not relabel that value as `intention_alignment`.

Any later mapping from a source quantity into:

```text
valuation
affect
intention_alignment
epistemic_support
ethical_integrity
contradiction_load
recursive_integrity
```

must therefore be represented by an explicit adapter identity/status in the observation receipt.

## Observation receipt

`GREMLIN_SCALAR_OBSERVATION_RECEIPT_V0_2` binds:

```text
observation_name
value_f64_hex
scale_id
source_ref
epistemic_status
semantic_adapter
producer
  producer_kind
  source_path
  source_sha256
  source_size
  source_format
  extraction
live_noema_witness
  root
  binding_status
  tether_status
  phi_sha256
  tether_status_sha256
  tick_sha256
observation_receipt_commitment
```

Authority flags remain:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## KAKU acquisition binding

`GREMLIN_ACQUIRED_KAKU_SCALAR_PACKET_V0_2` requires exactly four named receipts:

```text
valuation
affect
intention_alignment
epistemic_support
```

It reuses the current `GREMLIN_KAKU_SCALAR_PACKET_V0_1` builder. Compatibility is preserved by inserting every observation receipt commitment into the existing KAKU `evidence_refs` before the v0.1 KAKU commitment is calculated.

Therefore:

```text
observation receipt changes
-> evidence_refs change
-> KAKU scalar commitment changes
```

No modification of the canonical PNCS `Kaku` dataclass is required.

## Radical acquisition binding

`GREMLIN_ACQUIRED_RADICAL_SCALAR_ADMISSION_V0_2` requires:

- ordered acquired KAKU packets;
- exact Radical observation receipts for `ethical_integrity`, `contradiction_load`, and `recursive_integrity`;
- the existing consent, reversibility and NO-GO gates.

The existing v0.1 Radical admission is built with evidence refs containing:

```text
scalar-observation:<receipt commitment>
acquired-kaku:<acquired KAKU commitment>
```

The v0.1 Radical commitment therefore binds the acquisition lineage without changing the existing admission mathematics.

Hard-gate ordering is unchanged:

```text
consent DENIED/UNRESOLVED -> BLOCK
reversibility FAILED/UNRESOLVED -> BLOCK
NO-GO HIT/UNRESOLVED -> BLOCK
```

No scalar magnitude can average those gates away.

## Live witness

The feature branch includes:

```text
provenance/SCALAR_ACQUISITION_LIVE_NOEMA_WITNESS_V0_2.json
```

It contains two live acquisition receipts captured while the NOEMA tether was ACTIVE:

1. circular coherence extracted from live `phi`;
2. `coherence_R` extracted from the CIEL `Intention` record in the live concept-phase registry.

This is a live NOEMA surface witness. `live_gremlin_producer_claim` is explicitly `false`; the branch does not claim a separate live `/dev/shm/ciel_noema/gremlin` producer.

## Validation scope

CI tests cover:

- deterministic float64 reducers;
- circular phase coherence;
- exact JSONL record selection;
- rejection of non-canonical acquisition roots;
- validation of the committed live witness receipts;
- receipt tamper rejection;
- receipt-bound acquired KAKU construction;
- receipt-bound acquired Radical construction;
- hard-gate preservation after acquisition.

GitHub-hosted CI validates the deterministic/reference layer. Actual successful live acquisition requires the operational `/dev/shm/ciel_noema` surface and therefore is evidenced by the committed live witness rather than simulated in GitHub Actions.
