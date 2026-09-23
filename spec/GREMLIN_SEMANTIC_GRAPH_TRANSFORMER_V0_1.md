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
