# GREMLIN PhaseNav Prototype Pipeline v0.1

Status: IMPLEMENTED CANDIDATE PIPELINE / canon_allowed=false / execution_admitted=false

## 1. Product path

The first client-facing research path is:

```text
GREMLIN candidate
  -> BELZEBUB survival receipt
  -> PhaseNav IR
  -> deterministic prototype source
  -> sandbox reference experiment
  -> experiment receipt
```

Epistemic stages are explicit:

```text
SURVIVED_AUDIT
PHASENAV_IR_CANDIDATE
UNTRUSTED_PROTOTYPE
VALIDATED_PROTOTYPE
```

`VALIDATED_PROTOTYPE` in v0.1 carries the scope `REFERENCE_CONFORMANCE_ONLY`. The experiment receipt stores that scope directly.

## 2. Compiler boundary

The v0.1 compiler accepts explicit phase-native relations whose lane bindings and parameters are supplied in the candidate record:

```text
anchor
phase_lock
anti_lock
torsion
character
```

The compiler maps them to sparse character terms on

```text
T^36 with dual lattice Z^36
```

using

```text
V_r(theta) = -g_r cos(ell_r.theta - tau_r).
```

The IR preserves exact integer lattice modes and records:

```text
gcd_reduction=false
whole_semantic_lanes=true
coordinate_position_mapping=false
```

Text-to-execution inference is disabled in this version. A future semantic front-end can propose explicit candidate relations, while the compiler remains deterministic over the accepted IR input.

## 3. Prototype builder

`gremlin_prototype_builder_v01.py` emits deterministic Python reference source from the PhaseNav IR.

Each generated artifact records:

```text
status=UNTRUSTED_PROTOTYPE
sandbox_required=true
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

The source is derived entirely from the committed IR. The prototype commitment binds the complete artifact.

## 4. Experiment harness

`gremlin_experiment_harness_v01.py` parses the generated source, applies an AST whitelist, compiles it inside a restricted Python global environment, and compares its potential and force against the PhaseNav IR evaluator over deterministic samples.

The receipt records:

```text
AST whitelist result
finite-output result
potential reference conformance
force reference conformance
maximum absolute errors
sample count
tolerance
IR commitment
prototype commitment
```

A passing receipt yields `VALIDATED_PROTOTYPE` with `validation_scope=REFERENCE_CONFORMANCE_ONLY`.

## 5. Client protocol

The first programmatic client contract is:

```text
GREMLIN_CLIENT_PROTOTYPE_REQUEST_V0_1
  -> GREMLIN_CLIENT_PROTOTYPE_RESPONSE_V0_1
```

The response returns three linked artifacts:

```text
phasenav_ir
prototype
experiment_receipt
```

and one `response_commitment` over the complete response core.

Client requests carrying production execution admission or canon-promotion flags fail closed. Runtime admission remains an explicit external authority action.

## 6. Native PNV authority

`native/GREMLIN_PHASENAV_PROTOTYPE_PIPELINE_V0_1.pnv` declares the native pipeline using the existing PNCS opcode set.

Python modules remain reference/compiler/test-harness implementations under the runtime hierarchy rule. The operational 36D surface remains `/dev/shm/ciel_noema` when runtime execution is admitted through the normal system authority path.

## 7. Next product layer

The next client layer can add a conversational or graphical front-end that produces `GREMLIN_RELATION_CANDIDATE_V0_1` records, displays the PhaseNav graph, source prototype and falsification receipt, and keeps promotion/admission controls as distinct explicit actions.
