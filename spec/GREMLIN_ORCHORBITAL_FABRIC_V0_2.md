# GREMLIN Orchorbital Fabric v0.2

Status: `IMPLEMENTED CANDIDATE / DYNAMIC MODULAR TOPOLOGY / NON-ACTUATING / CHYBA`

Date: 2026-09-23

## Architectural correction

A Bestiary species does not own a fixed place in the execution hierarchy.

`SPIDER`, `MOLE`, `OWL`, `BEES`, and the other species are capability
modules. Runtime node instances acquire their position only when OCTOPUS
allocates them for an obligation discovered by an already-running node.

Therefore all of the following are legal in different invocations:

```text
MOLE
└── SPIDER
    └── OWL
```

```text
SPIDER
└── MOLE
    └── BEES
```

and in one runtime lineage:

```text
MOLE-1
└── SPIDER-1
    └── MOLE-2
```

The repeated species is a new node instance, not a recursion error.

## Four distinct relations

The v0.2 fabric explicitly separates four relations that must never be
collapsed into one parent/child edge.

### 1. Invocation provenance

```text
caller_id
```

This records which node asked OCTOPUS to allocate another node.

It is immutable for that node instance.

Invocation does not itself create a causal dependency and does not force the
child to orbit around the caller.

### 2. Orbital locality

```text
center_id
```

This describes the current non-causal computational locality of a node.

It may be changed at runtime by `recenter()`.

Center cycles are legal:

```text
A.center = B
B.center = A
```

because an orbital relation does not mean "wait for".

### 3. Causal prerequisite

```text
A depends_on B
```

This means A is not execution-ready until B is CLOSED.

The causal graph must remain a DAG. Any mutation that would create a causal
cycle fails closed.

### 4. Local reduction / join

```text
consumer waits_for child
```

This means the consumer cannot close its local result until the child result is
closed.

The join graph is also acyclic and local. It is not a single global BELZEBUB
barrier.

## Stable authority, movable computation

The fabric maintains two separate identities:

```text
authority_root_id
computational_barycenter_id
```

`authority_root_id` is fixed for the lifetime of the fabric and is copied
into every node instance.

`computational_barycenter_id` may move as activity migrates into a deeper or
more strongly connected subtree.

Moving the barycenter does not transfer authority.

This permits:

```text
authority root = GREMLIN/root request

initial computational barycenter = root
later computational barycenter   = SPIDER-7
later computational barycenter   = MOLE-12
```

without changing ownership of the request.

## OCTOPUS semantics

OCTOPUS is no longer modeled as a one-shot flat dispatcher.

Any OPEN Bestiary node may discover new obligations and invoke:

```text
allocate_invocation(
    fabric,
    caller_id,
    obligations,
    operators,
    budget,
    ...
)
```

OCTOPUS then:

1. runs exact `minimal_capability_cover`;
2. selects only the operator tiers required for the new obligation set;
3. creates new node instances atomically;
4. records the invoking node as immutable `caller_id`;
5. assigns each new node an independent `center_id`;
6. optionally attaches the new nodes to the caller's local join;
7. returns an auditable allocation receipt.

The newly created nodes may themselves invoke OCTOPUS later. This is how
subnodes and sub-subnodes arise.

## Dynamic example

```text
GREMLIN/root
  |
  | request requires derivation
  v
OCTOPUS allocates MOLE-1

MOLE-1 discovers graph obligation
  |
  v
OCTOPUS allocates SPIDER-1

SPIDER-1 discovers another derivation obligation
  |
  v
OCTOPUS allocates MOLE-2
```

There is no species ordering rule such as "MOLE must always orbit SPIDER" or
"SPIDER must always orbit MOLE".

The placement is a property of node instances in the current execution state.

## Caller and center may differ

A node can be invoked by one node and orbit another:

```text
caller(SPIDER-9) = MOLE-2
center(SPIDER-9) = BEES-4
```

This enables local reuse and cross-subtree coordination without falsifying
provenance.

`recenter()` may later change:

```text
center(SPIDER-9) = OWL-3
```

while:

```text
caller(SPIDER-9) = MOLE-2
authority_root(SPIDER-9) = AUTH:ROOT
```

remain unchanged.

## Atomic node allocation

`spawn_batch()` is transactional at the fabric layer.

If validation or an invariant check fails, the complete batch is rolled back,
including:

- node registry;
- causal edges;
- join edges;
- coordination edges;
- event log;
- generated-node counter;
- event sequence;
- computational barycenter.

This prevents partial fanout from becoming visible as valid runtime topology.

## Event log

Every successful topology mutation appends an event.

The event history is append-only from the public API and is returned by copy.
External callers cannot mutate the fabric by editing a previously returned
event structure.

Important events include:

```text
FABRIC_INIT
NODE_SPAWN
SPAWN_BATCH_COMMIT
CAUSAL_EDGE_ADD
JOIN_EDGE_ADD
COORDINATION_EDGE_ADD
NODE_RECENTER
BARYCENTER_MOVE
NODE_CLOSE
```

## Current lifecycle boundary

v0.2 models OPEN and CLOSED execution nodes and reserves FAILED and QUARANTINED
as terminal-state names for subsequent failover work.

A non-root node that is the current computational barycenter must be explicitly
recentered before normal CLOSE. This prevents silent computational-focus
migration.

The authority root may close only after every other OPEN node is closed.

## Phase boundary

`phase36` is optional.

If supplied, it must contain exactly 36 finite phase values in `[0,2pi)`.

This preserves the current distinction between the 20-role Bestiary registry
and the currently validated 18-role PhaseNav carrier surface. A role is not
silently promoted to a PhaseNav carrier merely because it can participate in
the orchorbital fabric.

## Safety and authority

The v0.2 receipt remains:

```text
canon_allowed           = false
execution_admitted      = false
memory_mutation_allowed = false
speedup_claim           = false
```

This branch changes architecture, not external authority.

## Performance significance

The v0.2 fabric removes several structural requirements that previously forced
work through a central route:

- fixed species position;
- caller == orbital center;
- root-mediated recursive allocation;
- one global synthesis dependency;
- fixed computational center.

The architecture can now represent local recursive expansion, local reduction,
cross-subtree locality, and barycenter migration.

No end-to-end multiplier is claimed until the WorkerBroker consumes this
dynamic topology on frozen workloads.

## Validation targets

The v0.2 contract suite checks:

- repeated species at different runtime depths;
- arbitrary species inversion;
- recursive OCTOPUS invocation from non-root nodes;
- caller/center independence;
- reciprocal orbital centers;
- causal-cycle rejection;
- join-cycle rejection;
- local join behavior;
- stable authority under barycenter movement;
- caller and authority immutability under recentering;
- explicit barycenter movement before normal close;
- atomic batch rollback;
- event-log copy isolation;
- exact 36D phase boundary;
- non-authoritative allocation receipts;
- fail-loud rejection of routing metadata for unselected operators.

## Migration path

v0.2 intentionally does not yet replace the current WorkerBroker or production
compatible flat pipeline.

The next integration gate is:

```text
dynamic fabric
  -> executable frontier
  -> WorkerBroker enqueue/claim
  -> node completion receipt
  -> local join closure
  -> recursive continuation
```

Only after that bridge is validated should the global flat synthesis path be
removed from the critical path.
