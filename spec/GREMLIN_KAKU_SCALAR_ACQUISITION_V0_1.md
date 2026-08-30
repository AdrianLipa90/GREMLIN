# GREMLIN KAKU Scalar Acquisition v0.1

Status: `IMPLEMENTED_CANDIDATE / PRE_VECTOR / RECEIPT_BOUND`

## Goal

Replace unbound numeric entry at the KAKU scalar boundary with an explicit producer and receipt chain:

```text
semantic registry term
-> producer contract
-> scalar observation receipt
-> exact acquisition bundle
-> KAKU scalar packet
```

The acquisition layer stays before exact `T^36` realization.

## Canonical semantic bindings

The v0.1 KAKU acquisition set is exactly:

```text
valuation            -> CLX2-AFFECT-001  Valuation
affect               -> CLX2-AFFECT-002  Affect
intention_alignment  -> CLX2-AGENCY-001  Intention
epistemic_support    -> CLX2-SEM-023     Confidence
```

Dependency bindings are explicit:

```text
affect
  -> CLX2-AFFECT-001 Valuation

epistemic_support
  -> CLX2-SEM-019 Evidence
  -> CLX2-AFFECT-005 Truth Evaluation
```

`epistemic_support` is therefore a graded confidence observation whose provenance includes evidence/truth-evaluation contracts.

## Producer contract

Schema:

```text
GREMLIN_KAKU_SCALAR_PRODUCER_CONTRACT_V0_1
```

A producer declares:

```text
producer identity/version
semantic role
canonical term ID
semantic class
support term IDs
scale ID
formula contract reference
implementation reference
source classification
live requirement
authority boundaries
```

Supported source classifications:

```text
LIVE_NOEMA_WITNESS
EXTERNAL_OBSERVATION
CIEL_IMPLEMENTATION_DONOR
STATIC_REFERENCE
TEST_FIXTURE
```

A producer marked `live_required=true` binds `LIVE_NOEMA_WITNESS` and its observation receipt binds the canonical live root:

```text
/dev/shm/ciel_noema
```

## Observation receipt

Schema:

```text
GREMLIN_KAKU_SCALAR_OBSERVATION_RECEIPT_V0_1
```

The receipt binds:

```text
producer contract commitment
canonical semantic identity
exact f64 value
scale ID
source classification/reference
input commitment
formula contract
implementation reference
epistemic status
evidence refs
live surface ref when required
```

The receipt ID is deterministic BLAKE2b-256 over canonical content.

Scale conversion requires a separately declared adapter/contract. v0.1 records:

```text
silent_scale_conversion_allowed = false
```

Conflicting observations remain separate claims until an explicit resolution contract exists. v0.1 records:

```text
conflict_averaging_allowed = false
```

## Exact acquisition bundle

Schema:

```text
GREMLIN_KAKU_SCALAR_ACQUISITION_BUNDLE_V0_1
```

The bundle requires exactly one valid receipt for each of the four semantic roles. Inputs may arrive in any order; the signed bundle uses deterministic canonical role ordering.

Admission conditions:

```text
exact four roles
finite values
valid canonical term bindings
valid receipt commitments
explicit scale per role
explicit source provenance
zero duplicate semantic roles
zero silent conversion
zero conflict averaging
```

The bundle remains pre-vector:

```text
vector_bound = false
t36_realization_present = false
execution_admitted = false
canon_allowed = false
```

## KAKU binding

`build_kaku_scalar_packet_from_acquisition(...)` converts the signed acquisition bundle into the existing `GREMLIN_KAKU_SCALAR_PACKET_V0_1` representation.

The KAKU packet receives each observation through its receipt ID:

```text
source_ref = receipt:<receipt_id>
```

and its signed evidence lineage contains:

```text
receipt:<receipt_id>       for all four observations
acquisition:<bundle_commitment>
```

The existing KAKU commitment therefore covers the acquisition lineage without post-signature mutation.

## CIEL donor audit

Two current CIEL/OMEGA implementations are registered as implementation-donor candidates:

### IntentionField

```text
src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/fields/intention_field.py
blob 68f93f42a14911ca7ba5a69b3eb7ec37a34eba7a
candidate role: intention_alignment
```

Its current implementation generates a normalized seeded vector and exposes projection/phase operations. A semantic producer binding requires a formula contract connecting those operations to the maintained future-directed target constraint represented by `CLX2-AGENCY-001`.

### AffectiveOrchestrator

```text
src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/emotion/affective_orchestrator.py
blob 1d0a1dadedaf147fa7628d176352b4c956a06d4a
candidate role: affect
```

Its current implementation maps EEG bands through the affect/emotion stack and exposes `mood_scalar`. The acquisition adapter will bind a selected output only through a declared affect scale/formula contract.

The donor also contains a broad exception fallback in its optional color path. GREMLIN scalar acquisition uses explicit validation/receipt failures and does not inherit that exception-handling path.

## Next gate

After v0.1 passes CI:

```text
1. add explicit CIEL producer adapters for validated valuation/affect/intention/confidence formulas;
2. bind live-required producers to NOEMA witness receipts;
3. feed acquired KAKU packets into RADICAL scalar admission;
4. implement RADICAL ethics acquisition for Ethical Integrity, Consent, Reversibility, NO-GO, contradiction load and recursive integrity.
```

The next gate keeps ethics at the directed Radical relation level while KAKU retains local valuation/affect/intention/epistemic observations.
