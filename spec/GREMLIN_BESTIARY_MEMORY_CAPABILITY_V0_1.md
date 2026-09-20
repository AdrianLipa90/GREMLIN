# GREMLIN Bestiary Memory Capability v0.1

Status: `IMPLEMENTED CANDIDATE / DENY-BY-DEFAULT / CHYBA`

Date: 2026-09-20

## Purpose

GREMLIN memory access is not a binary read/write permission.

The admitted relation is:

`principal x memory layer x operation x artifact type x scope -> ALLOW / DENY`.

Every decision emits a deterministic access receipt.

The policy covers all 18 Bestiary species plus RAPHAEL as a separate governance
principal.

## Memory layers

Shared memory layers:

- `WORKING`;
- `EPISODIC`;
- `SEMANTIC`;
- `RELATIONAL`;
- `ARCHIVAL`.

Every principal also has `PRIVATE_SCRATCH`.

Private scratch is local working space only:

- it is not a Source of Truth;
- it is not synchronized;
- it does not enter the shared memory ledger directly;
- only an explicitly exported typed artifact crosses into shared append-only
  memory.

## Global destructive-memory prohibition

The following shared-memory operations are globally denied for every Bestiary
species and RAPHAEL:

- `DELETE`;
- `OVERWRITE`;
- `EDIT_IN_PLACE`;
- `TRUNCATE`;
- `PURGE`.

This prohibition concerns GREMLIN memory semantics. It does not alter the
separate RAPHAEL repository/file mutation protocol, whose operations are
governed by decree, external authorization, exact-state reservation and
post-audit receipts.

Shared memory correction therefore means one of:

- append a derived artifact;
- append a flag;
- request supersession;
- request quarantine;
- request promotion.

The source record remains in lineage.

## Typed write authority

No species receives a generic `WRITE` capability.

Write-like operations require typed artifact namespaces.

Examples:

### SPIDER

SPIDER may read scoped EPISODIC, SEMANTIC and RELATIONAL state.

Its RELATIONAL write capability is:

`GRAPH_APPEND`

for:

- `RELATION_EDGE`;
- `GRAPH_SNAPSHOT`;
- `DEPENDENCY_LINK`;
- `ISOMORPHISM_LINK`.

SPIDER therefore writes graphs and relations, not arbitrary RELATIONAL payloads.

### RAVEN

RAVEN may create:

- `MEMORY_INDEX`;
- `SIMILARITY_LINK`;
- `RETRIEVAL_TRACE`.

It does not receive SPIDER graph-write authority.

### HOUND

HOUND may append:

- `CONTRADICTION`;
- `ANOMALY`;
- `TEST_TARGET`.

It may issue `QUARANTINE_REQUEST`, but does not directly quarantine or delete
memory.

### MOLE

MOLE may append typed derivation artifacts:

- `DERIVATION`;
- `LEMMA_CANDIDATE`;
- `CAUSAL_CHAIN`.

### OWL

OWL receives scoped epistemic audit capabilities and may append:

- `AUDIT_RECEIPT`;
- `EPISTEMIC_FINDING`.

### MANTIS

MANTIS may append duplicate/dead-branch findings and
`SUPERSEDE_REQUEST`.

A supersede request never deletes the source.

### BELZEBUB

BELZEBUB may append bounded defensive synthesis and threat artifacts:

- `SYNTHESIS_CANDIDATE`;
- `DEFENSIVE_THREAT_MODEL`;
- `THREAT_FLAG`;
- `QUARANTINE_REQUEST`.

### GREMLIN

The aggregate principal may append:

- `AGGREGATE_CANDIDATE`;
- `ORCHESTRATION_RECEIPT`;
- exchange ACKs;
- promotion/retention requests.

GREMLIN is not a memory superuser.

### RAPHAEL

RAPHAEL has governance metadata/audit visibility and may append governance
receipts/decrees.

Its ordinary memory-read visibility is metadata-bounded. Memory deletion and
overwrite remain globally denied.

## Read visibility

Read-like permissions additionally bound payload visibility:

- `COMMITMENT`;
- `FEATURE_VIEW`;
- `METADATA`;
- `FULL`.

A compare capability does not automatically imply full payload access.

Example: ANT comparison is limited to `FEATURE_VIEW`, while OCTOPUS global
routing visibility is metadata-only.

## Scope tokens

Shared memory requires a content-addressed
`GREMLIN_MEMORY_SCOPE_TOKEN_V0_1`.

A token binds:

- principal;
- task id;
- subject ids;
- generation ids;
- operations;
- artifact types;
- optional dependency ids;
- governance flag.

The token is explicitly:

`UNSIGNED_CONTENT_COMMITMENT`.

It is therefore a deterministic scope declaration, not cryptographic identity
authentication and not an authority grant by itself.

The policy engine intersects the token with the static Bestiary policy.

A token cannot widen static policy.

## Payload scope

Task-scoped full-payload reads require explicit subject and generation scope.

Wildcard subject/generation is rejected for payload-bearing task-scoped reads.

Global wildcard scope is admitted only where the static policy explicitly says
`GLOBAL_METADATA` or governance metadata.

This enforces:

`candidate retrieval -> capability filter -> payload retrieval`

rather than:

`retrieve everything -> filter afterward`.

## Dependency scope

A request may carry a dependency id.

When the token contains an explicit dependency allowlist, a dependency outside
that set is denied.

This supports graph/dependency-closure retrieval without exposing the whole
layer.

## Deterministic receipts

Every access check emits
`GREMLIN_MEMORY_ACCESS_RECEIPT_V0_1`.

Receipts bind:

- exact request commitment;
- principal;
- layer;
- operation;
- artifact type;
- subject/generation;
- dependency;
- scope-token commitment;
- matching rule id;
- effective visibility;
- ALLOW or DENY;
- reason code.

DENY is therefore auditable rather than silent.

## Principal summary

- HUMMINGBIRD: fast WORKING/EPISODIC typed capture.
- OCTOPUS: metadata routing and route receipts.
- SPIDER: scoped source read + RELATIONAL graph write.
- RAVEN: memory retrieval, similarity and indexing.
- HOUND: contradiction/anomaly/test-target findings and quarantine requests.
- MOLE: deep typed derivations.
- OWL: epistemic audit and audit findings.
- ANT: bounded feature-view comparison/enumeration.
- MANTIS: duplicate/dead-branch findings and supersede requests.
- FOX: planning/decomposition artifacts.
- BEAVER: prototype/construction candidates.
- BAT: phase/weak-signal pattern artifacts.
- CANARY: runtime/drift alerts and quarantine requests.
- SERPENT: novelty/latent-field observations.
- CHAMELEON: append-only representation transforms.
- BELZEBUB: defensive synthesis/threat findings.
- FERRET: explicit-grant metadata and actuation receipts only.
- GREMLIN: aggregation/orchestration receipts and bounded memory control requests.
- RAPHAEL: governance audit/receipts, not memory superuser.

The executable policy matrix in
`gremlin_mcp/bestiary_memory_capability.py` is authoritative for the review
branch.

## PASS

The implementation establishes:

- deny-by-default shared-memory policy;
- all 18 species plus RAPHAEL covered;
- typed write artifact namespaces;
- SPIDER graph-write semantics;
- subject/generation/dependency scope checks;
- metadata/feature/full visibility bounds;
- deterministic scope-token commitments;
- deterministic ALLOW/DENY receipts;
- global no-delete/no-overwrite/no-edit-in-place memory invariant;
- Bestiary/species manifests expose memory policy;
- reference MCP tool registry remains unchanged.

## OPEN / NOT CLAIMED

- cryptographic identity authentication of species workers;
- distributed signed scope-token issuance;
- retrieval/salience engine enforcement beyond callers using this gate;
- automatic migration of legacy memory accesses through the gate;
- garbage collection or physical deletion;
- canon promotion;
- physical/nonlocal memory claims.
