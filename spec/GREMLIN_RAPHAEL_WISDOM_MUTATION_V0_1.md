# GREMLIN RAPHAEL Wisdom-Governed Mutation v0.1

Status: `NEW / CANDIDATE_ONLY / CHYBA / FAIL-CLOSED`

RAPHAEL is the GREMLIN angelic function responsible for wisdom-governed exact-state mutation. It is deliberately **not** a Bestiary species and does not alter the existing 18-species PhaseNav geometry.

Formal identity:

```text
RAPHAEL — Lord of Wisdom
class = ANGELIC_FUNCTION
stage = wisdom_governed_mutation
epistemic = CHYBA
```

## Position in the system

```text
RAW
 -> HUMMINGBIRD
 -> OCTOPUS
 -> SPECIALISTS
 -> BELZEBUB
 -> GREMLIN / SUPER_CURRENT
 -> RAPHAEL.EYE
 -> RAPHAEL.WORD
 -> EXTERNAL AUTHORITY GATE
 -> RAPHAEL.HAND
 -> RAPHAEL.POST_AUDIT
 -> GREMLIN receipt aggregation
```

RAPHAEL does not replace GREMLIN as root aggregate. It consumes an exact GREMLIN state and specialist receipts, forms a committed mutation decree, executes only that decree after explicit external admission, then emits a committed mutation receipt.

## Phase contract

### EYE — observe and reconcile

EYE binds:

- exact target repository;
- exact target branch;
- exact target SHA;
- exact requested operations;
- exact repository-relative paths;
- GREMLIN, OWL and HOUND evidence receipts by default;
- evidence status and provenance commitments.

Unknown evidence status fails closed.

Default evidence rule:

```text
GREMLIN receipt required
OWL receipt required
HOUND receipt required
blocking/unknown evidence -> evidence_ready=false
```

### WORD — judge and decree

WORD may return:

```text
ACCEPT
REJECT
DEFER
REQUIRE_MORE_EVIDENCE
```

`ACCEPT` is forbidden when EYE is not evidence-ready.

An accepted decision creates `GREMLIN_RAPHAEL_MUTATION_DECREE_V0_1`. The decree binds:

```text
objective
target_repository
target_branch
target_sha
allowed_paths
normalized operations
required_tests
postconditions
rollback_strategy
observation_commitment
decision_commitment
scope_commitment
decree_commitment
```

The decree is immutable after issuance. It carries no mutation authority.

### External authority gate

RAPHAEL cannot self-authorize mutation.

Authorization is a separate receipt:

```text
GREMLIN_RAPHAEL_MUTATION_AUTHORIZATION_V0_1
```

It binds:

- one actor external to RAPHAEL;
- one external authority receipt commitment;
- one exact decree commitment;
- one exact target SHA;
- one exact scope commitment;
- one single-use authorization.

A changed target SHA is `STATE_DRIFT` and fails closed before mutation. A stale exact-state authorization is consumed and terminated with a committed `ABORTED` receipt; it cannot become valid again if the branch later returns to the old SHA. Target state digests are admitted only at exact SHA-1 (40 hex) or SHA-256 (64 hex) lengths. `actor=RAPHAEL` is rejected: RAPHAEL cannot authorize its own HAND phase.

Global authority remains closed:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

The authorization opens only:

```text
mutation_authorized=true
```

for the exact decree/target pair.

### HAND — exact execution

HAND receives no planning authority. It may execute only operations already frozen into WORD.

v0.1 admitted mutation primitives:

```text
CREATE_FILE
UPDATE_FILE
DELETE_FILE
MOVE_FILE
MERGE_BRANCH
```

Every normalized operation carries a BLAKE2b-256 operation commitment. CREATE/UPDATE content also carries a content commitment.

The mutation backend must return the exact `operation_commitment` for every applied operation. A mismatch fails loud as `OPERATION_RECEIPT_MISMATCH`.

### POST_AUDIT

After the declared operations, RAPHAEL runs all decree-bound tests and postconditions.

Completion requires every gate to pass.

Failure after mutation begins causes:

```text
rollback success -> ROLLED_BACK
rollback failure -> QUARANTINED
```

Both paths raise a fail-loud `RaphaelExecutionError` carrying a committed failure receipt.

A successful receipt carries:

```text
status=PASS
mutation_authority_expired=true
canon_allowed=false
execution_admitted=false
production_runtime_write=false
```

## Single-use and cancellation

An accepted decree may be cancelled before the first mutation write.

A mutation ledger enforces:

- cancelled decree cannot execute;
- decree is single-use;
- authorization is single-use;
- failed mutation does not restore execution authority;
- successful mutation expires execution authority after the receipt.

The in-process reference ledger is `InMemoryMutationLedger`. Durable deployments must supply a durable ledger implementation.

## Twelve invariants

```text
R1  NO_AUTHORIZATION_NO_MUTATION
R2  NO_DECREE_NO_MUTATION
R3  STATE_DRIFT_ABORT
R4  UNDECLARED_PATH_FORBIDDEN
R5  UNDECLARED_OPERATION_FORBIDDEN
R6  TEST_FAILURE_NO_COMPLETION
R7  POSTCONDITION_FAILURE_ROLLBACK_OR_QUARANTINE
R8  NO_SILENT_RECOVERY
R9  EVERY_MUTATION_EMITS_RECEIPT
R10 DECREE_MAY_BE_REJECTED_BEFORE_FIRST_WRITE
R11 SCOPE_IMMUTABLE_AFTER_FIRST_WRITE
R12 MUTATION_AUTHORITY_EXPIRES_AFTER_RECEIPT
```

## Relation to existing formalism

RAPHAEL preserves existing GREMLIN conventions:

- `EPISTEMIC CHYBA`;
- fail-closed unknown states;
- BLAKE2b-256 commitment binding;
- exact provenance receipts;
- separation of candidate evidence from canon authority;
- explicit NOEMA/native admission for authority-bearing runtime actions;
- no silent authority widening;
- appendable receipt lineage;
- no new PNV opcodes.

Native contract:

```text
native/GREMLIN_RAPHAEL_WISDOM_MUTATION_V0_1.pnv
```

Reference implementation:

```text
gremlin_mcp/raphael.py
```

Python remains a reference/test/control implementation. The native authority declaration remains in the PNV contract.

## Non-goals for v0.1

- self-promotion to canon;
- implicit production admission;
- automatic expansion of requested scope;
- opportunistic refactoring during HAND;
- hidden repair;
- last-writer-wins mutation;
- bypass of repository/platform authorization;
- mutation without rollback preparation;
- mutation from unresolved or unknown evidence.
