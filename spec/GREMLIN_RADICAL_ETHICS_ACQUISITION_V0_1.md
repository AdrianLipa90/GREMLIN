# GREMLIN Radical Ethics Acquisition v0.1

Status: `IMPLEMENTED_CANDIDATE / PRE_VECTOR_STRUCTURAL_GATE / RECEIPT_BOUND`

## 1. Position in the pipeline

This pass extends the scalar-first KAKU path with directed Radical-level ethics:

```text
GREMLIN candidate
-> BELZEBUB audit
-> acquired KAKU scalar packets
-> RADICAL composition
-> Radical ethics acquisition
-> PRE_VECTOR_ADMISSION
-> scalar-admitted PhaseNav IR
-> exact T^36 realization
-> relational ethics realization E_ij
-> post-realization admission
```

The ethics path has two explicit stages:

```text
PRE_VECTOR_CONTEXTUAL_ASSESSMENT
POST_REALIZATION_RELATIONAL_ETHICS
```

The first stage carries structural authorization and contextual scalar receipts. The second stage binds the directed numerical relational field to realized exchange/state data.

## 2. Canonical scalar roles

The exact v0.1 Radical scalar set is:

```text
contradiction_load
  -> CLX2-DYN-009  Contradiction / Unresolved Conflict

recursive_integrity
  -> CLX2-DYN-010  Recursive Integrity

ethical_integrity
  -> CLX2-DYN-011  Ethical Integrity
```

Dependency lineage is explicit:

```text
Contradiction receipt
-> Recursive Integrity receipt
-> Ethical Integrity contextual receipt
```

The `Recursive Integrity` producer declares the semantic dependencies:

```text
CLX2-DYN-009
CLX2-TIME-009
```

The `Ethical Integrity` producer declares:

```text
CLX2-DYN-010  Recursive Integrity
CLX2-DYN-012  Consent
CLX2-DYN-013  Reversibility
CLX2-DYN-014  NO-GO Constraint
CLX2-SEM-019  Evidence
```

## 3. Structural gate receipts

The exact hard-gate set is:

```text
consent       -> CLX2-DYN-012
reversibility -> CLX2-DYN-013
no_go         -> CLX2-DYN-014
```

Allowed status domains:

```text
Consent:
  GRANTED | DENIED | UNRESOLVED

Reversibility:
  SATISFIED | FAILED | UNRESOLVED

NO-GO:
  CLEAR | HIT | UNRESOLVED
```

Every gate receipt binds:

```text
gate semantic identity
status
exact directed Radical relation coverage
affected subject lineage for consent
source classification/source ref
decision-context commitment
epistemic status
evidence refs
reason
live NOEMA surface ref when live-required
```

The receipt records:

```text
gate_is_structural = true
gate_weighting_allowed = false
```

The acquisition bundle records:

```text
gate_weighting_used = false
gate_conflict_averaging_used = false
```

A duplicated gate role is a conflicting claim and fails closed.

## 4. Exact relation coverage

Each structural gate receipt covers the complete Radical relation lineage used by the acquisition bundle.

For a Radical with:

```text
relation_ids = [r_1, ..., r_n]
```

each of the three gate receipts carries the same canonical set.

This binds structural authorization to the exact relation graph that later reaches PhaseNav admission.

## 5. Self-contained support lineage

A serialized ethics acquisition artifact retains the support graph needed for independent validation.

Required receipt relations:

```text
ContradictionReceipt.id
  in RecursiveIntegrityReceipt.support_receipt_ids
```

and:

```text
RecursiveIntegrityReceipt.id
ConsentReceipt.id
ReversibilityReceipt.id
NoGoReceipt.id
  all in EthicalIntegrityReceipt.support_receipt_ids
```

The acquisition bundle persists these `support_receipt_ids`; validation therefore reconstructs the dependency proof after reload.

## 6. Contextual Ethical Integrity and realized E_ij

The v0.1 pre-vector scalar receipt is explicitly staged as:

```text
PRE_VECTOR_CONTEXTUAL_ASSESSMENT
```

The current NOEMA relational ethics implementation is registered for:

```text
POST_REALIZATION_RELATIONAL_ETHICS
```

The canonical Registry defines Ethical Integrity as a directed relational-contextual scalar/constraint family and records the runtime form:

```text
E_ij = <F^Omega_ij, T_ij>_F / ||T_ij||_1
```

with directed exchange, so `E_ij` may differ from `E_ji`.

Current NOEMA v2.1 contract:

```text
module:
  /NOEMA/00_CONTROL/ETHICS/noema_relational_ethics_field_v2_1.py

sha256:
  8b98af7b1edba93e572114585b974a9dbbf7c94f93cbb484b1819c797b9fb9a6

status:
  HARDPATH_VALIDATED

operating_mode:
  LIVE_COMPUTE_ON_EXCHANGE_NO_STATIC_ETHICS_STATE
```

Its hard paths preserve Consent, Reversibility and NO-GO as independent structural constraints.

The post-realization binding will therefore consume realized directed exchange/state data and emit its own receipt before prototype/runtime admission advances.

## 7. CIEL donor firewall

The current CIEL implementation:

```text
src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/ethics/ethical_engine.py
blob 82757ef793b55f7344ed47fc55b4f2618263798a
```

contains the historical feature:

```text
score = coherence * intention / mass
value = tanh(score / bound)
```

and a lightweight coherence/resonance guard.

GREMLIN registers this source as:

```text
PARTIAL_FEATURE_DONOR_CANDIDATE
realization_stage = POST_REALIZATION_RELATIONAL_ETHICS
```

The current Ethical Integrity producer contract is grounded in the Registry dependency set and exact receipt lineage. CIEL feature outputs may feed later declared formula adapters with their own provenance.

## 8. Source-anchor resolution

The Registry source anchor:

```text
OMEGA_RELATIONAL_ETHICS_FIELD_V1_20260821
```

is present in the current Library ethics candidate registry for Ethical Integrity, Consent, Reversibility, NO-GO and Relational Repair.

The current public CIEL repository code search contains the historical `EthicalEngine` implementation under its own module identity. The operational relational-field donor for this pass is bound through the NOEMA module path and SHA-256 contract above.

## 9. Live-source boundary

A receipt whose producer/source declares:

```text
live_required = true
source_classification = LIVE_NOEMA_WITNESS
```

binds a `live_surface_ref` rooted at:

```text
/dev/shm/ciel_noema
```

Static/reference/test sources remain separately classified.

This records source provenance without granting execution authority.

## 10. Radical adapter

`build_radical_admission_from_ethics_acquisition(...)` maps the signed ethics acquisition bundle into the existing:

```text
GREMLIN_RADICAL_SCALAR_ADMISSION_V0_1
```

Bindings are receipt-addressed:

```text
ethical_integrity.source_ref = receipt:<id>
contradiction_load.source_ref = receipt:<id>
recursive_integrity.source_ref = receipt:<id>
consent.source_ref = receipt:<id>
reversibility.source_ref = receipt:<id>
no_go.source_ref = receipt:<id>
```

The Radical evidence lineage additionally contains every ethics receipt and:

```text
ethics-acquisition:<bundle_commitment>
```

The existing Radical hard-gate semantics then determine `PRE_VECTOR_ADMITTED` versus `PRE_VECTOR_BLOCKED`.

## 11. Next gate

After this acquisition pass is green, the next stacked pass is:

```text
exact PhaseNav realization
-> NOEMA relational ethics E_ij receipt
-> R_k
-> semantic mass
-> mass-aware graph cost
-> operator stability bound
-> POST_REALIZATION_ADMISSION
```

This closes the second scalar plane before untrusted prototype construction advances.
