# GREMLIN Memory Consolidation Routing v0.1

Status: `IMPLEMENTED CANDIDATE / READ_ONLY ROUTER / CHYBA`

Date: 2026-09-20

## Purpose

GREMLIN validates PhaseNav memory-consolidation plans and receipts, then returns
the only admitted route from a derived SEMANTIC memory toward RELATIONAL Hive
memory.

GREMLIN does not perform the semantic consolidation itself and does not bypass
the PhaseNav memory-layer contract.

## Accepted PhaseNav artifacts

- `PHASENAV_MEMORY_CONSOLIDATION_PLAN_V0_1`;
- `PHASENAV_MEMORY_CONSOLIDATION_RECEIPT_V0_1`;
- `PHASENAV_MEMORY_RETENTION_MANIFEST_V0_1`;
- derived `PHASENAV_MEMORY_CONSOLIDATED_SEMANTIC_V0_1` envelope.

Every commitment is independently recomputed.

## Validation boundary

GREMLIN verifies that:

- at least two source descriptors exist;
- all sources target `EPISODIC`;
- all sources share one subject and one generation;
- one exact ACCEPTED-ACK id is bound for every source;
- the derived envelope is `EPISODIC -> SEMANTIC`;
- every source is a causal parent of the derived envelope;
- source payload commitments match the derived payload;
- `semantic_equivalence_proven=false`;
- retention entries never grant delete/overwrite authority;
- every retained memory remains retrievable;
- plan and receipt commitments are exact.

Reducer and producer labels remain unsigned content commitments.

## Memory-layer firewall

A consolidated derived envelope still targets `SEMANTIC`.

GREMLIN Hive accepts only `RELATIONAL`.

Therefore:

`derived SEMANTIC -> direct Hive ingest`

is forbidden.

The admitted route is:

1. PhaseNav applies consolidation;
2. a SEMANTIC store returns an ACCEPTED ACK;
3. PhaseNav promotes the derived SEMANTIC envelope to RELATIONAL;
4. PhaseNav creates a causal lineage bundle;
5. GREMLIN Hive ingests that RELATIONAL lineage bundle.

The router reports the first incomplete step and does not mutate memory.

## Receipt semantics

Without a PhaseNav receipt the route state is:

`AWAITING_PHASENAV_APPLY`.

With a valid `APPLIED` or `ALREADY_APPLIED` receipt the route state becomes:

`READY_FOR_SEMANTIC_STORE_ACK`.

An exact replay receipt is valid because the consolidation itself is
idempotent.

## Retention boundary

GREMLIN treats HOT/WARM/COLD/PINNED as storage/retrieval hints only.

It does not interpret `COLD` as deletion eligibility.

The router accepts retention only when every entry states:

- `deletion_allowed=false`;
- `overwrite_allowed=false`;
- `retrievable=true`.

## Authority boundary

The route planner is read-only.

It grants no:

- Hive mutation authority;
- direct SEMANTIC ingest;
- deletion authority;
- overwrite authority;
- canon promotion;
- reducer identity authentication;
- semantic-equivalence claim.

## PASS

The implementation establishes:

- independent PhaseNav consolidation-plan validation;
- independent retention-manifest validation;
- independent consolidation-receipt validation;
- explicit SEMANTIC/Hive firewall;
- deterministic five-step route to RELATIONAL Hive ingestion;
- no mutation from the route tool itself.

## OPEN / NOT CLAIMED

- automatic semantic-reducer quality;
- automatic SEMANTIC store selection;
- cryptographic reducer identity;
- cross-subject/cross-generation consolidation;
- deletion/garbage collection;
- automatic live-NOEMA consolidation;
- canon promotion.
