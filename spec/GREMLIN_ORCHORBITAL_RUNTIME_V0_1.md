# GREMLIN Orchorbital Runtime v0.1

Status: `IMPLEMENTED CANDIDATE / RECURSIVE EXECUTION TOPOLOGY / NON-ACTUATING / CHYBA`

Date: 2026-09-23

## Purpose

This layer removes the architectural assumption that one GREMLIN request must
be executed as a flat

```text
OCTOPUS -> specialist fanout -> one global synthesis barrier -> GREMLIN
```

topology.

The orchorbital candidate represents orchestration as a recursively composable
orbit tree with optional cross-orbit coordination edges:

```text
A
+- B
|  +- BA
|  +- BB
+- C
   +- CA
```

Every internal orbit is both a local execution centre and a local reduction
boundary. A child subtree may close as soon as its own causal obligations are
closed; it does not wait for unrelated sibling subtrees.

This is a software execution topology. "Orbit", "Lagrange" and related language
are scheduler/graph terms here and do not assert physical orbital dynamics.

## Current role boundary

Current `main` exposes 20 Bestiary roles after the ELEPHANT/BEES relational-memory
merge. The orchorbital compiler accepts all 20 roles.

The existing validated PhaseNav carrier surface remains 18 roles. Therefore
`phase36` is optional: ELEPHANT and BEES can participate in the execution tree
without silently receiving an unvalidated PhaseNav carrier.

## Core state

One orbit is

```text
OrbitSpec(
    orbit_id,
    species,
    parent_id,
    depends_on,
    phase36
)
```

`phase36` is a scheduling coordinate only.

## Recursive execution semantics

Each orbit has two events:

```text
OPEN:<orbit>
CLOSE:<orbit>
```

For a non-root orbit:

```text
OPEN(child) <- OPEN(parent)
```

An explicit causal dependency adds:

```text
OPEN(X) <- CLOSE(dependency)
```

An internal orbit closes locally:

```text
CLOSE(X)
  <- OPEN(X)
  <- CLOSE(immediate child 1)
  <- ...
  <- CLOSE(immediate child n)
```

Therefore a subtree has a local join. The root waits only for the immediate
root children, not for a flat list of every specialist task in the system.

## Tau

The compiler assigns exact discrete causal depth:

```text
tau(e) = 0                    when e has no prerequisite
tau(e) = 1 + max(tau(parent)) otherwise
```

Independent events occupy the same `tau` layer.

A cycle in either containment or causal dependencies fails closed.

## Coordination / Lagrange edges

`coordination_edges` add non-causal locality edges between orbits. They do not
silently add execution prerequisites and therefore cannot manufacture a hidden
global barrier.

The same graph is used by locality-first work stealing:

1. shortest hierarchy/coordination graph distance;
2. optional T^36 circular distance;
3. stable orbit identifier order.

This is the first explicit implementation of cross-plane coordination without
routing every exchange through the root.

## Hard invariants

The v0.1 compiler requires:

- exactly one root;
- every non-root orbit has an existing parent;
- all orbits are connected to the root;
- no parent cycle;
- all causal dependencies resolve to declared orbits;
- no causal cycle;
- coordination edges have valid distinct endpoints;
- optional phase state is exactly 36 finite values in `[0,2pi)`;
- unknown GREMLIN species fail closed.

The runtime receipt always preserves:

```text
canon_allowed            = false
execution_admitted       = false
memory_mutation_allowed  = false
physical_orbital_claim   = false
speedup_claim            = false
```

## Architectural difference from the current flat pipeline

The current production-compatible MCP pipeline remains unchanged in v0.1.
This candidate does not yet replace `gremlin_mcp/pipeline.py` or OCTOPUS.

The branch now contains both the executable topology primitive and the first
adaptive minimal-cover bridge:

```text
OCTOPUS obligations
 -> adaptive minimal cover
 -> ORCHORBITAL tree compiler
 -> WorkerBroker event frontier
 -> local subtree synthesis
 -> recursive reduction
 -> GREMLIN root close
```

The bridge is implemented in `gremlin_mcp/orchorbital_bridge.py`. It maps the
exact minimal capability cover onto obligation orbits while preserving explicit
parent/dependency structure. The global BELZEBUB barrier remains a migration
target in the existing production-compatible pipeline; it is not silently
removed by this candidate.

## Performance claim boundary

No 200x claim is made by v0.1.

The current evidence establishes topology and scheduler invariants only. Real
speedup must be measured after WorkerBroker and specialist kernels consume the
recursive event frontier on the same frozen workloads used by the existing
GREMLIN benchmarks.

For a 200x end-to-end result, the effective serial fraction would need to be
below roughly 0.5 percent in the relevant workload. The purpose of local joins,
recursive fanout, locality-first stealing and vector-resident kernels is to make
that regime testable, not to assume it.

## Validation

Targeted tests cover:

- recursive local joins;
- sibling parallelism in tau;
- readiness without unrelated-subtree blocking;
- causal-cycle rejection;
- multiple-root rejection;
- 36D boundary validation;
- coordination-edge work locality;
- authority/speedup claim firewall;
- ELEPHANT/BEES admission without fake PhaseNav carrier promotion;
- fail-loud equality with `core.py::BESTIARY_ROLES` so future role drift is caught;
- adaptive minimal-cover to orchorbital-tree compilation and authority firewall.

Local pre-commit validation on 2026-09-23: `9 passed`.

CI workflow: `.github/workflows/gremlin-orchorbital-runtime-v01.yml`.
