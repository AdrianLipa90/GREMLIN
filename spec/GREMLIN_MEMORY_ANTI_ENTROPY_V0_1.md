# GREMLIN Hive Memory Anti-Entropy v0.1

Status: `IMPLEMENTED CANDIDATE / EXCHANGE_MEMORY_ONLY / APPEND_ONLY / CHYBA`

Date: 2026-09-20

## Purpose

GREMLIN anti-entropy reconciles only the PhaseNav/GREMLIN exchange-memory subset
stored under `exchange:<envelope-id>`.

It does **not** replicate the whole Orbital Hive.

Local GREMLIN cognition, salience/priority, closure gates, latch state, local
research outputs and unrelated Hive subjects remain local unless another
explicit protocol governs them.

## Replication witness retention

New exchange ingests retain the complete proof required for later replication:

- direct RELATIONAL ingest stores the validated `exchange_packet`;
- cross-layer ingest stores the validated portable `lineage_bundle`.

The upstream WORKING/EPISODIC/SEMANTIC envelopes inside a bundle remain witness
data inside one RELATIONAL record. They are not imported as separate Hive
subjects.

Legacy exchange records created before proof retention remain visible in
inventory but are marked:

`LEGACY_UNEXPORTABLE`.

Anti-entropy refuses to fabricate missing proof for them.

## Inventory

Each Hive advertises only the set of exchange envelope ids, partitioned into
256 two-hex-digit commitment buckets.

Bucket roots depend on envelope ids only. Therefore two Hives holding the same
exchange facts have the same content root even if:

- local Hive record ids differ;
- local priorities differ;
- one peer stores a stronger proof witness than another.

Peer/node labels remain unsigned:

`authentication = UNSIGNED_CONTENT_COMMITMENT`.

## Manifest

Only divergent buckets reveal descriptors.

Descriptors contain:

- `envelope_id`;
- proof kind: `ENVELOPE`, `LINEAGE_BUNDLE` or
  `LEGACY_UNEXPORTABLE`;
- proof commitment;
- exportability flag.

No proof payload is transferred during manifest comparison.

## Delta plan

For direction `A -> B`, the plan records:

- exportable sender-only envelope ids;
- sender-only legacy ids that block export;
- receiver-only envelope ids that must remain untouched.

Claims explicitly forbid:

- receiver deletion;
- overwrite;
- canon promotion;
- full-Hive replication.

## Delta payload

An exportable delta carries only the verified proof needed to reconstruct each
missing RELATIONAL exchange record.

Direct transfer:

`envelope_id + validated exchange packet`.

Cross-layer transfer:

`envelope_id + validated lineage bundle`.

Local Hive priority is not replicated. It remains receiver-local policy.

## Apply

Before append, GREMLIN:

1. validates the delta commitment;
2. validates every exchange packet or lineage bundle;
3. verifies every target remains `RELATIONAL`;
4. verifies direct parent availability, generation continuity and sequence;
5. checks that the receiver exchange inventory is still the inventory used for
   planning;
6. performs normal fail-closed idempotent Hive ingest.

SQLite/WAL-backed Hives retain their existing per-record
`BEGIN IMMEDIATE` authority boundary.

Multi-record all-or-nothing transactionality remains OPEN in v0.1; semantic
preflight occurs before the first append, but each accepted Hive record still
uses the existing authority transaction.

## Retry semantics

If every transfer envelope is already present, replay returns
`ALREADY_APPLIED`.

The peer ACK is deterministic for both first application and exact retry:

- consumer: `GREMLIN-HIVE:<receiver-node-id>`;
- outcome: `ACCEPTED`;
- reason: `HIVE_ANTI_ENTROPY_PRESENT`.

This allows the returned ACKs to enter the PhaseNav ledger without generating a
second conflicting receipt after a lost network response.

The node id remains a committed but unsigned protocol label.

## MCP flow

The Hive MCP surfaces expose:

1. `gremlin_hive_sync_inventory`;
2. `gremlin_hive_sync_manifest`;
3. `gremlin_hive_sync_delta`;
4. `gremlin_hive_sync_apply`.

A normal directional exchange is:

`inventory -> divergent prefixes -> receiver manifest -> sender delta -> receiver apply`.

Bidirectional convergence requires a second exchange in the opposite direction.

## PASS

The implementation establishes:

- exchange-memory-only inventory;
- proof-aware exportability;
- minimal sender-only replication;
- receiver-only preservation;
- local-priority preservation;
- lineage-bundle replication without upstream Hive pollution;
- stale-plan rejection;
- deterministic retry ACK;
- SQLite/WAL restart persistence through existing Hive authority;
- no automatic latch, deletion, overwrite or canon promotion.

## OPEN / NOT CLAIMED

- cryptographic peer identity;
- encrypted network transport;
- Byzantine consensus/quorum;
- multi-record all-or-nothing SQLite transaction;
- tombstones/deletion reconciliation;
- legacy proof reconstruction;
- full Hive-state replication;
- automatic live-NOEMA synchronization;
- physical nonlocal signalling;
- canon promotion.
