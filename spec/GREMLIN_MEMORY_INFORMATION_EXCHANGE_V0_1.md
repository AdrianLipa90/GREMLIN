# GREMLIN Memory and Information Exchange v0.1

Status: `IMPLEMENTED CANDIDATE / APPEND_ONLY HIVE INGEST / SHARED_COGNITION_ONLY / CHYBA`

Date: 2026-09-20

## Purpose

This layer connects the PhaseNav memory-exchange protocol to GREMLIN Orbital Hive
Memory without duplicating PhaseNav memory semantics.

Accepted upstream schemas:

- `PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1`;
- `PHASENAV_MEMORY_INFORMATION_EXCHANGE_ACK_V0_1`;
- `PHASENAV_MEMORY_INFORMATION_EXCHANGE_BUNDLE_V0_1`.

GREMLIN independently recomputes payload commitments, envelope identities,
route-phase transport, ACK commitments and bundle commitments. No upstream hash
is trusted merely because it is present.

## Memory-role firewall

GREMLIN Hive is the `RELATIONAL` consumer.

A direct envelope ingest therefore requires:

`target_layer = RELATIONAL`.

ARCHIVAL/LOCKED state is not created automatically. Hive closure gates and
`latch()` remain separate operations.

## Content versus route

Payload commitment answers: **what information is this?**

Route metadata answers: **through what declared computational relational phase
did this hop travel?**

GREMLIN verifies:

`W_route = exp(i * sum_e A_e)`

and

`|W_route| = 1`.

This remains computational relation metadata. No physical communication field
or nonlocal signalling is claimed.

## Direct RELATIONAL ingest

The direct path stores each envelope under:

`exchange:<envelope-id>`.

If a direct RELATIONAL child declares another RELATIONAL parent, that parent
must already exist in the same authoritative Hive. Generation continuity and
monotonic sequence are checked before append.

This path remains useful for chains that are already inside the RELATIONAL
memory role.

## Cross-layer lineage bundle

A SEMANTIC -> RELATIONAL handoff must not require GREMLIN Hive to persist the
upstream WORKING, EPISODIC or SEMANTIC memories as if they were native Hive
records.

For cross-layer transfer GREMLIN accepts a portable lineage bundle containing:

- the RELATIONAL target envelope;
- every causal ancestor envelope in parent-first order;
- ACK packets recorded for upstream envelopes;
- one SHA-256 commitment over the complete portable proof.

GREMLIN then independently verifies:

1. every envelope commitment;
2. every parent edge;
3. generation continuity;
4. monotonic child sequence;
5. that the bundle contains exactly the ancestry of the target, with no
   unrelated envelopes;
6. every ACK commitment and payload binding;
7. at least one `ACCEPTED` ACK for every upstream ancestor;
8. the complete bundle commitment;
9. that the target is actually addressed to `RELATIONAL`.

Only the target envelope is persisted as Hive shared cognition. Upstream
envelopes are **lineage witnesses only**.

This resolves the ownership boundary:

`upstream memory proof != downstream native memory record`.

## Idempotency

`HiveAuthorityRuntime.place_idempotent` remains the only persistence path.

Exact replay of the same envelope or same lineage bundle returns the existing
Hive record instead of creating a second semantic version.

The protocol ACK remains stable across an exact retry. The result separately
reports:

- `created=true` for first ingest;
- `created=false` for exact replay.

A different lineage proof for an already stored envelope fails closed through
the existing idempotent Hive content/lineage comparison instead of silently
rewriting provenance.

## ACK return path

GREMLIN emits
`PHASENAV_MEMORY_INFORMATION_EXCHANGE_ACK_V0_1` bound to:

- exact envelope id;
- exact payload SHA-256;
- consumer id;
- outcome;
- reason code;
- CHYBA/shared-cognition authority state.

Direct ingest returns `HIVE_INGESTED`.

Bundle ingest returns `HIVE_LINEAGE_BUNDLE_INGESTED`.

The ACK can be recorded directly by the PhaseNav `MemoryExchangeLedger`.

## No automatic promotion

Ingest does not:

- set `evidence_ready`;
- set `dependencies_closed`;
- set `contradiction_audited`;
- set `provenance_complete`;
- set `phase_coherent`;
- call `latch()`;
- grant mutation authority;
- promote canon.

The target begins as ordinary OPEN shared cognition.

## Surfaces

Direct and bundle ingest are exposed through:

- integrated `gremlin-mcp` / `server_with_hive`;
- authoritative `gremlin-hive-mcp`;
- legacy Hive compatibility server.

All three surfaces use `HiveAuthorityRuntime`.

## PASS

The implementation establishes:

- independent envelope commitment verification;
- independent U(1) route verification;
- target-layer firewall;
- direct parent-first RELATIONAL ingest;
- portable cross-layer ancestry verification;
- upstream ACCEPTED-ACK gating;
- target-only Hive persistence;
- idempotent Hive persistence;
- stable ACK across retries;
- SQLite/WAL restart survival through existing Hive authority;
- no automatic latch or closure-gate promotion.

## OPEN / NOT CLAIMED

- live NOEMA memory synchronization;
- automatic `PhaseMemoryHypercrystal` promotion;
- physical nonlocal signalling;
- physical communication-field identification;
- proof of consciousness;
- canon promotion;
- physical substrate identification.
