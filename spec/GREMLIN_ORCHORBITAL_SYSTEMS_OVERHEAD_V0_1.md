# GREMLIN Orchorbital Systems Overhead Benchmark v0.1 — preregistration

Status: **DESIGNED_NOT_EXECUTED**  
`canon_allowed=false`

## Goal

Measure GREMLIN's own orchestration overhead with no model inference, using a lifecycle taxonomy compatible with published graph-runtime systems benchmarks.

## Frozen matrix

Topologies:
- chain
- wide fan-out
- diamond
- layered

Sizes:
- 10 nodes
- 50 nodes
- 200 nodes

Each cell:
- 2 discarded warmups
- 9 measured samples minimum
- median, mean, standard deviation and P95 retained
- raw samples retained

## Phases

1. **build** — construct the Orchorbital topology and validate invariants;
2. **prepare/snapshot** — generate the deterministic topology commitment / executable control state;
3. **state-transition run** — perform no-op lifecycle transitions only; no LLM, network or tool I/O;
4. **checkpoint** — serialize and verify restart state;
5. **restore** — restore and validate commitment equality.

## Fairness boundary

Do not compare a GREMLIN build time to another framework's steady-run time. Any external ratio requires the same topology, node count and lifecycle phase.

Swarms GraphWorkflow is used only as a methodology reference: its published benchmark uses no-op nodes specifically to isolate framework overhead. GREMLIN's result remains unknown until this preregistration is run on an actual repository checkout.

## Required receipt

The receipt must bind:
- GREMLIN commit SHA;
- Python/runtime and host information;
- topology/size/sample count;
- raw timing samples;
- median/P95;
- topology commitment;
- whether invariant checks were enabled;
- `model_calls=0`;
- `network_calls=0`;
- `canon_allowed=false`.

A failed topology or invariant check invalidates the cell rather than being omitted.
