# GREMLIN Semantic Graph Transformer / Compiler v0.1

Status: **candidate**. No canon promotion. No external mutation authority.

## Purpose

Convert unstructured text into a compact typed graph of semantic relation tokens so that downstream GREMLIN execution can operate on the minimal active relation subgraph instead of repeatedly expanding all source text.

The v0.1 implementation is deliberately a deterministic reference kernel, not a trained neural transformer. It fixes the executable contract that a learned relation scorer can later replace without changing the graph or bytecode format.

## Core map

`documents -> bounded relation candidates -> typed relation tokens -> compressed graph -> query causal cone`

The compiler does **not** perform full all-pairs attention. For each sentence it considers at most `max_neighbors` forward neighbors per term. This bounds candidate generation at approximately `O(n k)` for fixed `k` instead of `O(n^2)` pair enumeration.

## Relation bytecode

A relation token stores:

`(source_node_id, relation_code, target_node_id, confidence_q8, multiplicity)`

Stable relation codes in v0.1: ASSOCIATED_WITH, IS_A, PART_OF, CAUSES, SUPPORTS, CONTRADICTS, TRANSFORMS, DEPENDS_ON, PRECEDES, SAME_AS.

Repeated identical relations are represented once with multiplicity. Untouched source text remains provenance, not duplicated graph state.

## Query execution

`causal_cone(graph, seeds, depth)` returns only the bounded connected subgraph needed around query seeds. This is the intended handoff to GREMLIN routing/Bestiary computation.

## Claim boundary

This prototype demonstrates the storage/execution architecture and deterministic compression. It does **not** establish semantic completeness, universal compression, neural-model superiority, or a new complexity class. Arbitrary incompressible information remains expensive.


## Bestiary/Hive integration

The candidate handoff is capability-scoped and ordered:

SPIDER -> ELEPHANT -> BEES

SPIDER receives typed graph/edge/dependency-link requests. ELEPHANT receives bounded consolidation/memory-orbit/replay-plan requests. BEES receives coherence, anti-entropy, and reconciliation requests. The handoff itself never mutates Hive.

A content-addressed PHASENAV_MEMORY_INFORMATION_EXCHANGE_V0_1 candidate can be emitted with target_layer=RELATIONAL. Existing GREMLIN memory_exchange validation and Hive ingestion remain the authority boundary.

## Local validation, 2026-09-23

- deterministic local unit tests: 11/11 PASS;
- live NOEMA/GREMLIN A/B: causal-cone routing cut median dispatch fan-out from 4 to 2 in all three tested corpus sizes;
- at 550 sentences, median live GREMLIN route latency fell from 21.44 ms to 18.28 ms and context bytes fell 31.7%;
- at 1100 sentences, context bytes fell 65.9%;
- reference 5000-sentence repeated-structure fixture: 2,068,027 input bytes -> 15,778 relation-bytecode bytes, with 2,944 unique relation tokens representing 1,125,000 relation occurrences.

These are architecture/runtime measurements, not a semantic-quality or trained-model benchmark. GitHub Actions was not executed because the repository account has no available GHA billing minutes.
