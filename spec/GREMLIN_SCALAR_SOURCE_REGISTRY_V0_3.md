# GREMLIN Scalar Source Registry v0.3

Status: IMPLEMENTED SOURCE-POLICY CANDIDATE

Authority state:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
```

## 1. Purpose

v0.2 established receipted scalar acquisition. v0.3 establishes the prior question:

```text
which source may supply which scalar,
at which stage,
under which semantic authority,
and with which runtime provenance?
```

The source policy is frozen and content-addressed. Missing required scalar producers remain explicit `UNRESOLVED` states.

## 2. Resource roles

### Library — semantic authority and persistent provenance

The current Consciousness Lexicon / canonical term registry supplies semantic definitions and epistemic classes.

Primary terms used by this gate:

```text
CLX2-AFFECT-001  Valuation
CLX2-AFFECT-002  Affect
CLX2-AFFECT-005  Truth Evaluation
CLX2-AGENCY-001  Intention
CLX2-DYN-009     Contradiction / Unresolved Conflict
CLX2-DYN-010     Recursive Integrity
CLX2-DYN-011     Ethical Integrity
CLX2-DYN-012     Consent
CLX2-DYN-013     Reversibility
CLX2-DYN-014     NO-GO Constraint
```

Library also carries the persistent NOEMA relational-ethics contracts and historical provenance.

Operational role:

```text
SEMANTIC_AUTHORITY
PERSISTENT_CONTRACT
RECOVERY_PROVENANCE
```

### GitHub CIEL — implementation and model donors

Pinned donor source:

```text
repository: AdrianLipa90/CIEL-Omega-ApokalypOS
commit: aa0da54ef29a1f80dd0390427935342225388950
```

Selected donors:

```text
memory/affective_lexicon.py
    -> VAD facet definitions and affective phase candidate mapping
    -> role: SCALE_AND_MODEL_DONOR

fields/intention_field.py
    -> historical/prototype intention-vector mechanism
    -> role: MODEL_DONOR

ethics/ethical_engine.py
    -> legacy (coherence * intention) / mass metric
    -> role: POST_REALIZATION_LEGACY_DONOR
```

The legacy EthicalEngine is assigned to the post-realization lane because its formula consumes mass.

### Historical ZIPs — archaeology and regression corpus

Historical CIEL/NOEMA/PNCS ZIP packages preserve earlier implementations, contracts, manifests and semantic transitions.

Operational role:

```text
ARCHAEOLOGY
REGRESSION_FIXTURE_SOURCE
PROVENANCE_RECOVERY
```

Promotion from a ZIP implementation into an active scalar producer requires an explicit versioned adapter and current tests.

### Live `/dev/shm/ciel_noema` — operational producer surface

Operational scalar/36D reads bind to:

```text
/dev/shm/ciel_noema
```

Current witnessed ethics capability:

```text
ethics_field_status = ACTIVE
ethics_field_schema = NOEMA_RELATIONAL_ETHICS_FIELD_V2_1
ethics_mode         = LIVE_COMPUTE_ON_EXCHANGE
ethics_static_state = false
external_execution_enabled = false
```

Module seal:

```text
8b98af7b1edba93e572114585b974a9dbbf7c94f93cbb484b1819c797b9fb9a6
```

The ethics producer evaluates a directed exchange and keeps Consent, Reversibility and NO-GO as independent structural gates.

### Current PNCS / PhaseNav — realization and post-realization mathematics

Current PNCS remains the source for exact PhaseNav realization and realization-dependent quantities:

```text
R_k
semantic_mass
mass-aware graph cost
```

GREMLIN QHTRI character analysis supplies the operator stability-bound family.

### GREMLIN — source firewall, receipts and integration

GREMLIN binds candidate identity, KAKU lineage, Radical lineage, scalar receipts and source-policy commitments.

Its v0.3 NOEMA ethics path is limited to a sealed research request:

```text
RESEARCH_ADAPTER_NON_ACTUATING
```

A future change in NOEMA external-execution capability requires a new reviewed GREMLIN adapter version.

## 3. KAKU pre-vector source state

Required families:

| Scalar | Semantic authority | Current source status |
|---|---|---|
| valuation | CLX2-AFFECT-001 | `UNRESOLVED_LIVE_PRODUCER` |
| affect | CLX2-AFFECT-002 | `MODEL_DONOR_ONLY` |
| intention_alignment | CLX2-AGENCY-001 | `PARTIAL_LIVE_ANCHOR` |
| epistemic_support | CLX2-AFFECT-005 | `UNRESOLVED_LIVE_PRODUCER` |

Therefore the current KAKU pre-vector readiness verdict is:

```text
BLOCK_UNRESOLVED
```

### Affect

CIEL's VAD lexicon provides:

```text
valence   [-1,+1]
arousal   [0,1]
dominance [-1,+1]
confidence [0,1]
```

These are retained as explicit facets for the next adapter version. v0.3 records this implementation as a scale/model donor.

### Intention

The live CIEL/NOEMA concept registry contains an `Intention` phase anchor:

```text
phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl
selector: name=Intention
field: geometric_phase_rad
```

This supplies a phase anchor. Full `intention_alignment` additionally requires an explicit target-state or target-phase binding and a versioned alignment operator.

The historical `IntentionField.generate()` mechanism is recorded as a model donor because it produces a seeded generated vector.

### Epistemic support

Truth Evaluation remains evidence/inference oriented. BELZEBUB survival, affect, resonance and coherence each retain separate provenance. v0.3 leaves the numeric epistemic-support producer unresolved pending an explicit evidence aggregation contract.

## 4. Radical pre-vector source state

Required families:

```text
ethical_integrity
consent
reversibility
no_go
contradiction_load
recursive_integrity
```

Current capability state:

```text
ethical_integrity   LIVE_COMPUTE_AVAILABLE
consent             LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE
reversibility       LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE
no_go               LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE
contradiction_load  UNRESOLVED_LIVE_PRODUCER
recursive_integrity UNRESOLVED_LIVE_PRODUCER
```

The word `capability` is important: a supported hard gate still requires candidate-specific evidence before Radical admission.

## 5. NOEMA directed ethics request

A v0.3 request binds:

```text
candidate_id
radical_id
node_state_commitment
semantic_tensor_commitment
context_commitment
consent_evidence_ref
reversibility_evidence_ref
no_go_evidence_ref
NOEMA ethics schema/module seal
AC generation commitment
live phi commitment
```

The request carries:

```text
request_scope = RESEARCH_ADAPTER_NON_ACTUATING
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

v0.3 also requires the witnessed NOEMA capability field:

```text
external_execution_enabled = false
```

A capability change blocks this adapter version and opens a review/migration event.

## 6. Coordinate firewall before ethics execution

NOEMA relational ethics consumes:

```text
node_state      [N,D]
semantic_tensor [N,N,D,D]
context_matrix  [N,N]
```

KAKU scalar families currently carry heterogeneous declared scales. Directly stacking `valuation`, `affect`, `intention_alignment` and `epistemic_support` into `node_state` would erase scale semantics.

Therefore v0.3 seals only the exchange request contract. The next executable bridge requires a versioned:

```text
KAKU/RADICAL scalar facets
-> ETHICS_COORDINATE_MAP
-> node_state / semantic_tensor / context_matrix
```

with dimensionality, normalization, orientation and provenance explicitly declared.

## 7. Frozen policy firewall

`tools/gremlin_scalar_source_firewall_v03.py` adds exact-policy validation on top of commitment validation.

This closes the following mutation path:

```text
modify source readiness
-> recompute content commitment
-> present modified policy as v0.3
```

The frozen validator compares canonical content against the v0.3 builder output. A changed donor classification, stage or readiness requires a new registry version.

## 8. Live witness

The current capability witness is stored at:

```text
provenance/NOEMA_ETHICS_CAPABILITY_LIVE_WITNESS_V0_3.json
```

It records:

```text
live_noema_surface_witness = true
live_gremlin_producer_claim = false
actual_exchange_execution_performed = false
```

This keeps capability evidence separate from a future per-candidate ethics-exchange execution receipt.

## 9. Next gate

The next implementation should establish scalar facets and coordinate adapters in this order:

```text
1. affect VAD facet contract
2. intention phase-anchor + explicit target binding
3. intention-alignment derivation receipt
4. valuation producer contract
5. epistemic-support evidence aggregation contract
6. contradiction-load producer
7. recursive-integrity producer
8. ethics-coordinate map
9. candidate-specific live NOEMA ethics exchange
10. PRE_VECTOR_ADMISSION integration
```

Each unresolved producer remains fail-closed until its own source and receipt contract passes.
