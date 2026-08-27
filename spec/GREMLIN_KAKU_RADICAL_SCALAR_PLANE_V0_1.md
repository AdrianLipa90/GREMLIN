# GREMLIN KAKU/RADICAL Scalar Plane v0.1

Status: IMPLEMENTED ARCHITECTURE CANDIDATE / no production execution authority / no canon promotion

## 1. Starting point

The integration starts at PNCS L0/L1:

```text
L0 KAKU    atomic typed relational operation
L1 RADICAL reusable ordered/graph composition of KAKU atoms
```

The PNCS construction order is preserved:

```text
semantic / mathematical relation
-> KAKU
-> RADICAL
-> DEFINITION / graph
-> exact PhaseNav T^36 realization
-> execution route
```

The scalar integration therefore begins before exact T^36 realization whenever the scalar is semantically defined without requiring the realized phase state.

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

Evaluated only after an exact PhaseNav realization exists.

```text
R_k phase coherence / order parameter
semantic_mass m_k
mass-aware graph cost C_M
character / operator stability bounds
realization-dependent diagnostics
```

`semantic_mass` is deliberately not fabricated in Plane A because the current PNCS mass binding depends on the realized phase order parameter `R_k`.

The two planes therefore create two distinct admission boundaries:

```text
PRE_VECTOR_ADMISSION
POST_REALIZATION_ADMISSION
```

A successful pre-vector receipt permits PhaseNav realization work to begin. It does not imply that realization-dependent mass, cost or stability checks have passed.

## 3. KAKU-local scalar semantics

A pre-vector KAKU packet is a typed semantic atom plus scalar observations and constraints. It is not yet a `Vector36`.

Candidate record:

```text
KAKU_SCALAR_PACKET_V0_1
  kaku_id
  operator_kind
  operator_classification
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

Current operator classifications are kept explicit instead of flattening all recovered names into one primitive class:

```text
SOURCE       OBSERVED_REUSED_PNCS_LEAF
ORDER        OBSERVED_REUSED_PNCS_LEAF
TRANSFORM    OBSERVED_REUSED_PNCS_LEAF
COMPOSITION  OBSERVED_REUSED_PNCS_LEAF
DIFFERENCE   OBSERVED_REUSED_PNCS_LEAF
IDENTITY     OBSERVED_REUSED_PNCS_LEAF
CONDITION    CONTROL_PLANE_KAKU_CANDIDATE
NEGATION     RECOVERED_PNV_OPERATOR
```

This follows the current PNCS separation between its minimal observed/reused leaf alphabet, control-plane candidates and the broader recovered PNV vocabulary.

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

The scalar-first route is:

```text
GREMLIN candidate relation
-> BELZEBUB audit
-> KAKU semantic atoms
-> KAKU scalar packets
-> RADICAL composition
-> directed ethics / consent / reversibility / NO-GO
-> PRE_VECTOR_ADMISSION receipt
-> scalar-admitted PhaseNav IR / realization request
-> exact PhaseNav T^36 realization
-> POST_REALIZATION_SCALARS
-> mass / graph-cost / stability checks
-> POST_REALIZATION_ADMISSION receipt
-> UNTRUSTED_PROTOTYPE
-> reference / falsification harness
```

`tools/gremlin_scalar_admitted_phasenav_v02.py` implements the first hard bridge: no scalar-admitted PhaseNav IR is emitted unless the Radical is `PRE_VECTOR_ADMITTED`, the candidate identity matches, and the exact candidate relation lineage equals the scalar-admitted Radical relation lineage.

The next bridge must bind the exact realization to Plane B and block prototype construction until the post-realization receipt passes.

Neither admission receipt independently authorizes production runtime execution.

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
- current KAKU classifications;
- exact realization and mass binding;
- native execution and inverse lineage contracts.

The scalar-plane adapter does not rewrite canonical PNCS mathematics or the existing `Kaku` dataclass.

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

- harvest algorithms, thresholds, state handling and tests;
- compare candidate realizations against the current semantic registry;
- adapt useful mechanisms through narrow adapters.

Existing code alone does not promote a legacy formula to current semantic authority.

### NOEMA — runtime/provenance substrate

Library NOEMA artifacts provide boot, recovery, schemas, manifests, receipts and archive selectors.

Operational 36D authority remains the live surface:

```text
/dev/shm/ciel_noema
```

The scalar plane may be computed/audited before vector admission. Once a 36D operation is admitted, the operational path traverses the live NOEMA surface.

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
build untrusted prototype after all required admission stages
run falsification/reference tests
```

Production execution and canon promotion remain separate authority decisions.

## 7. Non-invasive adapter boundary

The implementation adds a scalar-plane adapter rather than modifying the canonical PNCS `Kaku` dataclass in place.

Reason:

- the current class requires `Vector36`;
- historical and current receipts depend on existing identities;
- scalar-first semantics need an unbound pre-realization representation;
- PhaseNav realization remains a later explicit binding.

Implemented adapter chain so far:

```text
KAKU_SEMANTIC_ID
-> KAKU_SCALAR_PACKET_V0_1
-> RADICAL_SCALAR_ADMISSION_V0_1
-> PRE_VECTOR_ADMITTED
-> GREMLIN_SCALAR_ADMITTED_PHASENAV_IR_V0_2
```

Planned continuation:

```text
-> exact T^36 realization binding
-> POST_REALIZATION_SCALARS
-> POST_REALIZATION_ADMISSION
-> prototype gate
```

## 8. v0.1/v0.2 gate status

Implemented and tested:

1. typed KAKU scalar packets;
2. exact KAKU operator classification provenance;
3. order-sensitive Radical aggregation;
4. hard consent/reversibility/NO-GO semantics;
5. separate affect/valuation/intention/epistemic modulators;
6. deterministic content commitments;
7. pre-vector admission receipt semantics;
8. candidate/Radical identity binding;
9. exact scalar-admitted relation-lineage binding;
10. PhaseNav IR emission only after `PRE_VECTOR_ADMITTED`.

The implementation remains a feature-branch candidate. Production runtime effects and canon promotion remain closed.
