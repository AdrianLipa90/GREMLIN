# GREMLIN Memory and Information Exchange v0.1

Status: `IMPLEMENTED CANDIDATE / APPEND_ONLY HIVE INGEST / SHARED_COGNITION_ONLY / CHYBA`

Date: 2026-09-19

## Purpose

This layer connects the PhaseNav memory-exchange protocol to GREMLIN Orbital Hive
Memory without duplicating PhaseNav memory semantics.

The accepted upstream packet is:

`PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1`.

GREMLIN independently recomputes:

- canonical payload SHA-256;
- exact envelope commitment;
- memory-layer labels;
- generation/sequence fields;
- parent references;
- route-edge U(1) phase;
- transport unit modulus;
- epistemic and authority boundaries.

No upstream commitment is trusted merely because it is present in the packet.

## Memory-role mapping

GREMLIN Hive is the `RELATIONAL` consumer.

[
	ext{PhaseNav WORKING/EPISODIC/SEMANTIC}
	o
	ext{exchange envelope}
	o
oxed{	ext{GREMLIN RELATIONAL Hive}}.
]

The ingest endpoint rejects envelopes whose declared target layer is not
`RELATIONAL`.

ARCHIVAL/LOCKED state is not created automatically. Hive closure gates and latch
remain separate operations.

## Content versus route

The payload commitment answers:

[
	ext{what information is this?}
]

The route transporter answers:

[
	ext{through what declared relational phase did this hop travel?}
]

GREMLIN verifies

[
W_{m route}=expleft(isum_e A_eight),qquad |W_{m route}|=1.
]

This remains computational relation metadata. No physical communication field or
nonlocal signalling is claimed.

## Causal ingest

Each envelope is stored under its own Hive subject:

[
	exttt{exchange:<envelope-id>}.
]

This avoids implicit last-writer-wins versioning when several hops carry the same
logical subject.

For every declared parent:

1. the parent envelope must already exist in the same authoritative Hive;
2. parent and child generation ids must match;
3. child sequence must exceed the parent sequence.

The child Hive dependency list contains explicit parent exchange references.

Thus a causal child cannot enter shared relational memory before its declared
history.

## Idempotency

`HiveAuthorityRuntime.place_idempotent` is the only write path.

Replaying the exact same envelope returns the already stored Hive record and does
not append a second semantic version.

The protocol ACK remains exactly:

[
	exttt{ACCEPTED / HIVE_INGESTED}
]

for both first delivery and exact retry, so network replay does not create a
conflicting second ACK for the same consumer.

The result separately reports:

- `created=true` for first ingest;
- `created=false` for exact idempotent replay.

## ACK

GREMLIN emits:

`PHASENAV_MEMORY_INFORMATION_EXCHANGE_ACK_V0_1`

bound to:

- exact envelope id;
- exact payload SHA-256;
- consumer id;
- outcome;
- reason code;
- CHYBA/shared-cognition authority state.

The ACK therefore returns to the same protocol ledger that emitted the
information packet.

## No automatic promotion

Ingest does **not**:

- set `evidence_ready`;
- set `dependencies_closed`;
- set `contradiction_audited`;
- set `provenance_complete`;
- set `phase_coherent`;
- call `latch()`;
- grant mutation authority;
- promote canon.

The new record begins as ordinary OPEN shared cognition.

## Surfaces

The same exchange ingest is exposed through:

- integrated `gremlin-mcp` / `server_with_hive`;
- authoritative `gremlin-hive-mcp`;
- legacy Hive server surface for compatibility.

All surfaces use `HiveAuthorityRuntime`.

## PASS

The implementation establishes:

- independent packet commitment verification;
- independent U(1) route verification;
- target-layer firewall;
- parent-first causal ingest;
- generation and sequence checks;
- idempotent Hive persistence;
- stable ACK across retries;
- SQLite/WAL restart survival through existing Hive authority;
- no automatic latch or closure-gate promotion.

## OPEN / NOT CLAIMED

- live NOEMA memory synchronization;
- automatic PhaseMemoryHypercrystal promotion;
- physical nonlocal signalling;
- physical communication-field identification;
- proof of consciousness;
- canon promotion;
- physical substrate identification.
