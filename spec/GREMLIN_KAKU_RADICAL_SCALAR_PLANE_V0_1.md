# GREMLIN KAKU/RADICAL Scalar Plane v0.1

Status: ARCHITECTURE CANDIDATE / no production execution authority / no canon promotion

## 1. Starting point

The integration starts at PNCS L0/L1:

```text
L0 KAKU    atomic typed relational operation
L1 RADICAL reusable ordered/graph composition of KAKU atoms
```

The mature PNCS construction order is preserved:

```text
semantic / mathematical relation
-> KAKU
-> RADICAL
-> DEFINITION
-> exact PhaseNav T^36 realization
-> execution route
```

The scalar integration therefore happens before exact T^36 realization whenever the scalar is semantically defined without requiring the realized phase vector.

## 2. Two scalar planes

A single undifferentiated scalar bundle would mix quantities with incompatible provenance. v0.1 separates them.

### Plane A — PRE_VECTOR_SCALAR_ENVELOPE

Evaluated before `Vector36` / exact `T^36` binding.

It may contain declared or measured scalar realizations for:

```text
valuation
affect modulation
intention alignment
epistemic support / confidence
ethical integrity
consent
reversibility
risk / protected-condition exposure
NO-GO
```

The envelope also records provenance and epistemic status for each scalar. Missing required structural gates fail closed.

### Plane B — POST_REALIZATION_SCALARS

Evaluated only after the exact PhaseNav realization exists.

```text
R_k phase coherence / order parameter
semantic_mass m_k
mass-aware graph cost C_M
character / operator stability bounds
realization-dependent diagnostics
```

`semantic_mass` is deliberately not fabricated in Plane A because the current PNCS mass binding depends on the realized phase order parameter `R_k`.

## 3. KAKU-local scalar semantics

A pre-vector KAKU packet is a typed semantic atom plus scalar observations and constraints. It is not yet a `Vector36`.

Candidate record:

```text
KAKU_SCALAR_PACKET_V0_1
  kaku_id
  operator_kind
  direction
  polarity
  role
  source_binding
  target_binding
  valuation
  affect
  intention_alignment
  epistemic_support
  evidence_refs
  scalar_status
```

Rules:

- `polarity` remains an explicit local scalar.
- affect and valuation may modulate priority/weighting but do not establish truth or execution authority.
- intention is represented as a future-directed constraint; a scalar alignment is a realization of that constraint, not its semantic definition.
- unknown required values remain explicit unknowns; they are not silently replaced by neutral zeros.

## 4. RADICAL-level scalar semantics

Ethical and authorization state is evaluated primarily at the directed relation / Radical level because it depends on context among KAKU nodes and edges.

Candidate record:

```text
RADICAL_SCALAR_ADMISSION_V0_1
  radical_id
  ordered_kaku_ids
  relation_ids
  kaku_scalar_commitments
  ethical_integrity
  consent_gate
  reversibility_gate
  no_go_gate
  contradiction_load
  recursive_integrity
  aggregate_epistemic_support
  aggregate_affect_modulation
  pre_vector_admission
```

Hard-gate semantics:

```text
NO_GO hit           -> BLOCKED
consent failure     -> BLOCKED for affected directed relation
reversibility fail -> BLOCKED for protected intervention class
missing required structural evidence -> BLOCKED / UNRESOLVED
```

These gates are not averaged away by resonance, coherence, agreement, affect, confidence or aggregate score.

## 5. Admission ordering

```text
GREMLIN candidate relation
-> BELZEBUB audit
-> KAKU semantic atoms
-> KAKU scalar packets
-> RADICAL composition
-> directed ethics / consent / reversibility / NO-GO
-> PRE_VECTOR_ADMISSION receipt
-> exact PhaseNav T^36 realization
-> POST_REALIZATION_SCALARS
-> mass / graph-cost / stability checks
-> PhaseNav IR
-> UNTRUSTED_PROTOTYPE
-> reference / falsification harness
```

The scalar plane therefore determines whether vector synthesis may be attempted. It does not by itself authorize runtime execution.

## 6. Resource authority map

### Historical PNCS ZIPs — archaeology / regression source

Use the Library packages:

```text
PHASENAV_NATURAL_CODE_SYSTEM_V0_1.zip
PHASENAV_NATURAL_CODE_SYSTEM_V0_2_TIR_SOH.zip
PHASENAV_NATURAL_CODE_SYSTEM_V0_3_GRAMMAR_MINING.zip
PHASENAV_NATURAL_CODE_SYSTEM_V0_4_PRIMITIVE_CLOSURE.zip
```

Purpose:

- recover original KAKU/RADICAL contracts;
- verify why a radical is a compression handle for an ordered KAKU path;
- preserve primitive-mining provenance;
- build regression tests against historical semantics.

They are not live execution authority.

### Current PNCS GitHub — current KAKU/RADICAL contract

`AdrianLipa90/PhaseNav-Natural-Coding-System`

Purpose:

- current hierarchy and fail-closed rules;
- current irreducible KAKU status;
- exact realization and mass binding;
- native execution and inverse lineage contracts.

The scalar-plane adapter must not silently rewrite canonical PNCS mathematics.

### Consciousness Dictionary / CIEL registry in Library — semantic source

Use the current term/dependency/ethics registries for semantic definitions of:

```text
Valuation
Affect
Intention
Ethical Integrity
Consent
Reversibility
NO-GO Constraint
Recursive Integrity
Truth Evaluation
```

Purpose:

- define what each scalar/constraint means;
- preserve dependency and epistemic status;
- prevent old runtime formulas from becoming definition authority by accident.

### CIEL/OMEGA code and historical ZIPs — implementation donor

Use legacy/current CIEL engines as candidate implementations only after semantic mapping:

```text
EthicalEngine
EthicalCoreLite
EthicsGuard
IntentionField
ResonanceOperator
Affect / coherence machinery
```

Purpose:

- harvest tested algorithms, thresholds, state handling and receipts;
- compare candidate realizations against the current semantic registry;
- adapt useful mechanisms through narrow adapters.

No legacy formula is promoted merely because code exists.

### NOEMA — runtime/provenance substrate

Library NOEMA artifacts provide boot, recovery, schemas, manifests, receipts and archive selectors.

Operational 36D authority remains the live surface:

```text
/dev/shm/ciel_noema
```

The scalar plane may be computed/audited before vector admission. Once a vector operation is admitted, every operational 36D path must traverse the live NOEMA surface.

### GREMLIN — integration and research client

GREMLIN owns the candidate/audit presentation and the bounded compilation workflow.

It may:

```text
propose relation
show KAKU decomposition
show Radical composition
show scalar envelopes
show failed hard gates
request PhaseNav realization after scalar admission
build untrusted prototype
run falsification/reference tests
```

It does not independently grant production execution or canon promotion.

## 7. Non-invasive adapter boundary

The first implementation should add a scalar-plane adapter rather than modify the canonical PNCS `Kaku` dataclass in place.

Reason:

- the current class requires `Vector36`;
- historical and current receipts depend on existing byte/content identities;
- scalar-first semantics need an unbound pre-realization representation;
- PhaseNav realization remains a later explicit binding.

Proposed adapter chain:

```text
KAKU_SEMANTIC_ID
-> KAKU_SCALAR_PACKET
-> RADICAL_SCALAR_ADMISSION
-> PRE_VECTOR_RECEIPT
-> canonical PNCS realization adapter
-> Vector36 / T^36 binding
```

## 8. First implementation gate

v0.1 should implement only:

1. typed KAKU scalar packets;
2. Radical aggregation;
3. hard consent/reversibility/NO-GO semantics;
4. separate affect/valuation/intention/epistemic modulators;
5. deterministic content commitments;
6. pre-vector admission receipt;
7. adapter output accepted by the existing GREMLIN -> PhaseNav compiler only after `PRE_VECTOR_ADMITTED`.

No vector synthesis change, runtime mutation or production effect is required for this first gate.
