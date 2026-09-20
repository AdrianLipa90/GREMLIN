# Bestiary Memory Capability v0.1

Status: `IMPLEMENTED CANDIDATE / DENY_BY_DEFAULT / CHYBA / canon_allowed=false`

Date: 2026-09-20

## Purpose

GREMLIN Bestiary memory access is no longer modeled as global read/write access.

Authorization is the product:

`beast × memory_layer × operation × artifact_type × subject_scope × generation_scope × task_scope`.

A role may read one memory layer while being allowed to emit only a narrow,
typed artifact class into another.

The default policy is:

`DENY`.

## Memory layers

Shared memory layers are:

- `WORKING`;
- `EPISODIC`;
- `SEMANTIC`;
- `RELATIONAL`;
- `ARCHIVAL`.

Each principal also receives task-scoped `PRIVATE_SCRATCH`.

Private scratch:

- is not synchronized;
- is not Source of Truth;
- does not enter the shared anti-entropy protocol automatically.

## No destructive edit

The following operations are globally forbidden to every Bestiary principal,
including RAPHAEL:

- `DELETE`;
- `OVERWRITE`;
- `IN_PLACE_EDIT`.

A change to memory is represented by a new append-only artifact:

`old -> derived`

or by a typed proposal such as:

`SUPERSEDE_REQUEST(old,new)`.

The original record remains in lineage.

## Typed operations

The shared operation vocabulary includes:

- metadata/payload read;
- query;
- compare;
- observation append;
- derive;
- graph append;
- edge append;
- node link;
- flag;
- ACK;
- route;
- consolidate;
- supersede request;
- quarantine request;
- promote request;
- retention request;
- audit;
- governance review.

A capability for one operation never implies another.

## SPIDER

SPIDER is an active graph writer, not a read-only analyst.

Its RELATIONAL write namespace is explicitly limited to:

- `RELATION_EDGE`;
- `GRAPH_SNAPSHOT`;
- `DEPENDENCY_LINK`.

Admitted operations are:

- `GRAPH_APPEND`;
- `EDGE_APPEND`;
- `NODE_LINK`;
- typed `DERIVE`.

SPIDER cannot use those rights to append arbitrary observations, contradictions,
semantic summaries or unrelated Hive records.

This encodes:

`graph_write != generic_write`.

## RAVEN

RAVEN reads and compares EPISODIC/SEMANTIC memory and may derive:

- `MEMORY_INDEX`;
- `SIMILARITY_LINK`;
- `RETRIEVAL_TRACE`.

ARCHIVAL and selected RELATIONAL access is metadata/query oriented rather than
unbounded payload access.

## HOUND / MANTIS / OWL

HOUND may compare and emit contradiction/anomaly/test-target findings and
quarantine requests. It does not quarantine destructively.

MANTIS emits duplicate/dead-branch findings and `SUPERSEDE_REQUEST` proposals.
It never overwrites the superseded record.

OWL audits shared memory and emits epistemic/audit findings. Promotion is a
request, not unilateral canon promotion.

## Other typed writers

- HUMMINGBIRD / SERPENT: observation capture;
- MOLE: derivation / lemma / causal-chain artifacts;
- ANT: bounded enumeration results;
- BAT: pattern and harmonic observations;
- CHAMELEON: transformed representations;
- BELZEBUB: defensive synthesis / threat models / quarantine proposals;
- FERRET: scoped search receipts;
- GREMLIN: aggregate candidates, orchestration receipts, routes and requests;
- RAPHAEL: governance decisions and governance-scoped audit/proposals.

No principal receives arbitrary write access to a whole layer.

## Scoped capability token

An admitted action receives a content-addressed
`BESTIARY_MEMORY_CAPABILITY_TOKEN_V0_1`.

The token binds:

- beast;
- layer;
- operation;
- artifact type;
- subject scope;
- generation scope;
- task scope;
- exact policy commitment.

Subject-scoped grants cannot mint wildcard-subject tokens. Task-scoped grants
require a concrete task scope.

The token is not a cryptographic identity credential:

`authentication = UNSIGNED_CONTENT_COMMITMENT`.

It is a deterministic policy permit descriptor.

## Access receipt

Every evaluation returns
`BESTIARY_MEMORY_ACCESS_RECEIPT_V0_1`.

The receipt is emitted for both:

- `ALLOW`;
- `DENY`.

Examples of deny reasons include:

- no matching grant;
- scoped token required;
- beast mismatch;
- layer mismatch;
- artifact mismatch;
- subject/generation/task scope mismatch;
- destructive operation forbidden.

This makes policy denial itself auditable.

## Worker-dispatch enforcement

The capability matrix is enforced at `WorkerBroker.enqueue`, including the
SQLite-backed broker through inheritance.

A task may declare internal memory requests under:

`_gremlin_memory_requests`.

Direct enqueue already identifies the beast through the task species. Fanout
requests additionally require an explicit `species` selector for each memory
request.

Before the task is created GREMLIN:

1. removes the raw request descriptor from the worker payload;
2. validates the beast/layer/operation/artifact tuple;
3. checks subject, generation and exact task scope;
4. issues one content-addressed capability token per admitted request;
5. evaluates and validates the corresponding ALLOW receipt;
6. binds the complete authorization bundle into the task commitment.

The broker-owned field is:

`_gremlin_memory_authorization`.

Callers cannot provide or replace that field. Attempted injection fails closed.

If any requested access is forbidden, task creation fails before queue mutation.

For fanout, requests are partitioned per target beast before enqueue. A SPIDER
graph request therefore cannot silently become a RAVEN or HOUND capability.

If a task requests no memory access, it receives no memory authorization bundle.

Before a worker can claim a queued task, GREMLIN revalidates the complete
authorization bundle against the current policy commitment. A queued or
SQLite-persisted task therefore cannot retain a capability revoked by a later
policy revision. A stale or tampered bundle remains unleased and the claim
fails closed.

OCTOPUS excludes memory-request metadata from semantic routing. Capability
metadata therefore cannot manufacture the route that would make its own memory
disclosure possible.

This enforces:

`route evidence != memory authorization`

and

`memory request != memory disclosure`.

## Principal-neutral memory gateway

The low-level Hive, memory-exchange, anti-entropy and consolidation engines are
principal-neutral mechanisms. They do not decide whether SPIDER, RAVEN, OWL or
GREMLIN may use a memory operation.

Bestiary access goes through
`GREMLIN_BESTIARY_MEMORY_GATEWAY_V0_1`.

This façade binds the existing capability token to the concrete memory action
before any result is disclosed or any exchange envelope is appended.

Current guarded paths include:

- exact RELATIONAL Hive head metadata read;
- exact RELATIONAL Hive head payload read;
- PhaseNav exchange-envelope ingest;
- lineage-bundle ingest;
- whole-Hive anti-entropy inventory generation;
- whole-Hive anti-entropy manifest generation;
- anti-entropy metadata comparison and delta planning;
- anti-entropy proof/payload export;
- non-mutating consolidation/retention route construction.

The split is deliberate:

`storage mechanics != principal authority`.

For Hive reads, technical storage keys such as `exchange:px:...` are not used
as the capability subject. The token is bound to the logical
`subject_id × generation_id`; after lookup, embedded record metadata is checked
against that scope before disclosure.

Whole-Hive operations use a wildcard subject/generation scope. A role with only
SUBJECT_SCOPED access therefore cannot mint a whole-Hive token. This creates a
real difference between, for example:

- SPIDER: exact-subject relational graph work;
- RAVEN: metadata-wide memory indexing, but no relational payload export;
- OWL: metadata-wide comparison/audit;
- GREMLIN: task-scoped payload export for orchestration.

Anti-entropy application itself remains a system replication mechanism rather
than a Bestiary power. The gateway exposes metadata comparison and bounded
export, but it does not convert set difference into delete/overwrite authority.

## Automatic research projection

Research execution no longer writes every specialist result into RELATIONAL Hive
indiscriminately.

Before the first Hive mutation, GREMLIN preflights the complete execution:

- root GREMLIN execution receipt -> `DERIVE / ORCHESTRATION_RECEIPT`;
- SPIDER -> `DERIVE / GRAPH_SNAPSHOT`;
- HOUND -> `FLAG / CONTRADICTION|ANOMALY`;
- MOLE -> `DERIVE / DERIVATION`;
- OWL -> `DERIVE / EPISTEMIC_FINDING`;
- MANTIS -> `FLAG / DUPLICATE_FINDING|DEAD_BRANCH_FINDING`;
- BELZEBUB -> `DERIVE / SYNTHESIS_CANDIDATE`.

RAVEN and ANT are deliberately **not** projected directly to RELATIONAL Hive,
because their current write grants terminate in SEMANTIC memory. Their worker
results remain available upstream for synthesis/dependencies, but no relational
Hive record is created merely because they participated in a research fanout.

Unknown/untyped species fail the whole projection preflight before the root
record is written. This prevents partial Hive state from an authorization
failure late in a stage.

Every projected Hive payload carries:

- `memory_layer`;
- `memory_operation`;
- `memory_artifact_type`;
- exact `memory_capability_receipt`.

The receipt id is also included in provenance.

## System operator boundary

`server_with_hive.py` is a system-operator/control-plane surface, not a
Bestiary species identity surface. Direct operator tools such as Hive placement,
gate management, anti-entropy apply and latch do not become SPIDER/RAVEN/etc.
capabilities merely because they exist in the same MCP process.

The status surface declares:

`SYSTEM_OPERATOR_CONTROL_PLANE`

and explicitly reports that direct Hive tools are not species capabilities.

This is an authority-domain distinction, not cryptographic IAM. Species identity
authentication remains OPEN.

## Retrieval invariant

Candidate discovery does not grant disclosure.

The required flow is:

`candidate memory -> capability gate -> scoped disclosure`.

Not:

`retrieve everything -> filter later`.

Accordingly the policy manifest fixes:

`difference_detection_grants_disclosure = false`.

Anti-entropy set difference therefore cannot be interpreted as Bestiary payload
read permission.

## GREMLIN and RAPHAEL

GREMLIN is not a memory superuser. It receives broad metadata/query access for
orchestration and task-scoped payload access, but typed RELATIONAL writes only.

RAPHAEL is governance authority above the ordinary species topology, but its
memory actions remain append-only governance artifacts. It does not gain
DELETE, OVERWRITE or IN_PLACE_EDIT.

## PASS

The implementation establishes:

- deny-by-default capability policy;
- all 18 Bestiary species plus RAPHAEL represented;
- typed operation and artifact namespaces;
- scoped content-addressed capability tokens;
- deterministic ALLOW/DENY access receipts;
- globally forbidden destructive operations;
- explicit SPIDER graph-write semantics;
- task-local private scratch;
- existing Bestiary/species introspection exposes the policy;
- worker enqueue enforces requested memory capabilities before queue mutation;
- fanout partitions memory requests per species;
- broker-owned task authorization bundles bind tokens and ALLOW receipts;
- worker claim revalidates authorization against the current policy snapshot;
- capability-gated façade protects Hive read, exchange ingest and anti-entropy disclosure paths;
- automatic research projection is preflighted per species before any Hive mutation;
- RAVEN/ANT semantic outputs cannot silently leak into RELATIONAL Hive;
- Hive MCP operator controls are explicitly separated from Bestiary species authority;
- logical subject/generation scope is checked independently of technical Hive keys;
- whole-Hive metadata and payload export require separately admissible wildcard scopes;
- OCTOPUS routing ignores memory-authorization metadata;
- no reference/product tool-registry expansion.

## OPEN / NOT CLAIMED

- cryptographic beast identity authentication;
- secret/bearer-token semantics;
- automatic enforcement inside historical code paths that do not pass through WorkerBroker or an explicit memory gate;
- distributed revocation;
- time-based token expiry;
- external IAM binding;
- canon promotion.
