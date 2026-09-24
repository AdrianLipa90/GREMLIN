# GREMLIN Orchorbital Systems Overhead Benchmark v0.1

Status: **HARNESS_HARDENED / EXECUTION_PENDING_REAL_CHECKOUT**  
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
- 2 discarded warmups;
- 9 measured samples minimum;
- median, mean, standard deviation, min, max and P95 retained;
- raw nanosecond samples retained.

The authority root is not counted as a workload node.

## Timed phases

1. **build** — instantiate `OrchorbitalFabric`, spawn workload nodes and causal edges. The fabric's mutation methods enforce invariants during construction.
2. **snapshot** — deterministic privacy-safer topology snapshot.
3. **commitment** — deterministic topology commitment.
4. **checkpoint** — serialize restart state.
5. **restore** — restore the checkpoint and validate the embedded topology commitment.
6. **state_transition_run** — no-op lifecycle transitions only: start, self-complete, close in dependency order.

The final diagnostic `fabric.receipt()` is explicitly **outside** the `state_transition_run` timer. This prevents topology-commitment/audit work from contaminating the run measurement.

## Provenance hardening

Execution is fail-closed unless:

- the supplied repository root is the exact Git top-level;
- `git rev-parse HEAD` exactly equals the expected 40-character commit SHA;
- the working tree is clean, including untracked files;
- the runner can hash its own source plus `orchorbital_fabric.py` and `role_registry.py`.

The receipt binds the verified Git HEAD and SHA-256 hashes of these exact source files.

## External-I/O firewall

Every cell records:

- `model_calls=0`;
- `network_calls=0`;
- `tool_io_calls=0`;
- `canon_allowed=false`.

Any topology/invariant/restore failure invalidates the cell instead of being omitted.

## Fairness boundary

Do not compare GREMLIN's build time with another framework's steady-state execution time. External ratios require matching topology, node count and lifecycle phase.

Swarms GraphWorkflow remains only a methodology/reference envelope until this harness is executed on the exact GREMLIN checkout.

## Current status

The implementation exists at:

- `tools/gremlin_orchorbital_systems_overhead_v01.py`
- `tests/test_gremlin_orchorbital_systems_overhead_v01.py`

The current ChatGPT runtime has the live GREMLIN/NOEMA runtime bundle but not a Git checkout of the private repository. Therefore no timing receipt is fabricated here. The next legitimate status transition is from `EXECUTION_PENDING_REAL_CHECKOUT` to `PASS_EXECUTED` only after the source-binding gate passes on a real checkout.
