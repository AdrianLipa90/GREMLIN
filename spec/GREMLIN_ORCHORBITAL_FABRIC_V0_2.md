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

v0.2 separates three execution milestones:

```text
OPEN / not started
OPEN / execution_started
OPEN / self_complete
CLOSED / subtree complete
```

A causal prerequisite may be added only before local execution starts.
`mark_started()` seals the causal prerequisite set. `mark_self_complete()`
records the local worker result but does not close the node while local joins
remain unresolved.

FAILED and QUARANTINED remain reserved terminal-state names for subsequent
failover work.

A non-root node that is the current computational barycenter must be explicitly
recentered before normal CLOSE. A node that is still the orbital center of any
OPEN satellite also cannot close until those satellites are explicitly
recentered. This prevents silent computational-focus migration and orphaned
center references.

Recursive growth is bounded by a fabric-level `max_nodes` resource budget,
not by a species-specific hierarchy or fixed semantic depth. Each node records
`invocation_depth` for audit and benchmark purposes.

The authority root may close only after every other OPEN node is closed.

## Fail-closed recovery and replacement

`FAILED` and `QUARANTINED` are terminal historical states, but they are
**not successful closure**.

A causal or join dependency pointing at one of those states remains unresolved
until an explicit replacement is bound:

```text
FAILED(source)
    |
    +-- replacement --> replacement-node
```

The replacement must cover every obligation carried by the failed/quarantined
source. The old node and all of its original edges remain in the audit history;
nothing is rewritten in place.

A failed/quarantined source is considered successfully resolved only when:

1. its explicit replacement resolves successfully; and
2. every local join child already spawned by the source also resolves
   successfully.

Replacement edges participate in the same blocking-cycle audit as causal and
join edges. The effective blocking graph is:

```text
E_block = E_causal ∪ E_join ∪ E_replacement
```

and it must remain acyclic. This catches mixed deadlocks such as a causal edge
in one direction and a join/replacement edge in the other.

Failure/quarantine also performs explicit failover of live orbital locality:
open satellites are rehomed to the nearest open caller ancestor (or the
authority root), and a failed computational barycenter is moved with an
auditable `BARYCENTER_FAILOVER` event. The authority root itself cannot be
silently failed or replaced by this candidate runtime.

The authority root cannot close while any other node remains unresolved,
including terminal failed/quarantined nodes without a successful recovery
chain.

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

## N-node coordination points

The fabric also supports non-causal multi-node rendezvous points:

```text
CoordinationPoint(
    point_id,
    member_ids,
    weight,
    physical_claim=false
)
```

A coordination point acts as a locality hyperedge. Its members become directly
adjacent for routing/locality purposes without adding causal or join
dependencies.

This is the software meaning of a Lagrange-style shared coordination point in
the current architecture. It is explicitly not a physical claim.

New coordination points require at least two unique OPEN members and a finite
positive weight. Historical points may remain in the audit trail after member
nodes later close, but only OPEN members participate in live locality ranking.

The `weight` field is reserved metadata in v0.2 and is **not yet consumed by
routing distance**. Current locality is unweighted hop distance. This is
reported explicitly in the runtime receipt so a future weighted scheduler
cannot be mistaken for current behavior.

## Dynamic center selection

OCTOPUS may either supply an explicit center for a selected operator or supply
a set of candidate centers.

The fabric ranks candidate centers lexicographically by:

1. shortest open-node locality distance through caller, current-center and
   coordination links;
2. circular T^36 distance when a target phase and candidate phase are both
   available;
3. current computational barycenter preference;
4. stable node identifier order.

Graph locality is therefore primary. Phase is a tie-break rather than a license
to bypass a much closer execution neighborhood.

Explicit and candidate center policies for the same selected operator are
mutually exclusive and fail closed if both are supplied.

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
- local execution start before accepting a result;
- causal-edge sealing after execution starts;
- caller provenance rooted at the immutable authority root;
- recursion budget and invocation-depth accounting;
- orphaned-center prevention on close;
- locality-first/T^36-tiebreak center ranking;
- non-causal n-node coordination-point locality;
- non-authoritative allocation receipts;
- fail-loud rejection of routing metadata for unselected operators;
- self-complete spawn/join sealing;
- mixed causal/join/replacement deadlock rejection;
- failed/quarantined nodes never satisfying closure implicitly;
- explicit obligation-covering replacement recovery;
- failure-driven satellite and barycenter failover;
- root closure blocked by unrecovered terminal work.

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


## WorkerBroker execution bridge

The dynamic fabric now has a dedicated execution bridge:

```text
gremlin_mcp/orchorbital_executor.py
```

The bridge does not move topology semantics into WorkerBroker. WorkerBroker
remains responsible for bounded queueing, same-species leasing, result
commitments and lease expiry. The fabric remains responsible for caller
provenance, causal readiness, joins, centers, barycenter, failure and recovery.

The execution loop is:

```text
fabric.ready_nodes()
  -> deterministic worker task id
  -> WorkerBroker.enqueue()
  -> lease / compute / submit
  -> WorkerBroker result commitment
  -> optional discovery validation
  -> OCTOPUS deterministic recursive allocation
  -> node.self_complete
  -> local join closure
```

### Deterministic task identity

Worker task identity is derived from:

```text
execution_id
authority_root_id
node_id
```

and a domain-separated BLAKE2b commitment.

The current mutable orbital center is deliberately not part of task identity.
A node may be recentered while its worker task remains the same logical work.

The task payload includes an immutable node execution context:

- execution id;
- node id;
- species;
- authority root;
- caller provenance;
- obligations;
- optional phase36;
- invocation depth.

It does not include the global topology snapshot as task identity. The global
topology changes during recursive execution and would make retries appear as
payload drift.

### Recoverable two-phase dispatch

A fabric node may be marked execution-started before enqueue succeeds. This is
recoverable rather than silently rolled back.

The executor recomputes the same deterministic task id and may replay enqueue.
WorkerBroker accepts the replay only when content is identical. Different
content under the same deterministic task id fails closed as task-content
drift.

Therefore:

```text
started + task absent  -> retry enqueue
started + task queued  -> no duplicate
started + task leased  -> no duplicate
started + task done    -> reconcile result
```

### Recursive worker discovery

A worker cannot select or directly instantiate another Bestiary species.

A worker may only emit:

```json
{
  "_gremlin_orchorbital_discovery": {
    "schema": "GREMLIN_ORCHORBITAL_DISCOVERY_V0_1",
    "obligations": ["..."]
  }
}
```

The executor validates this envelope. OCTOPUS then runs the exact minimal
capability cover again and allocates the required subnodes.

Malformed discovery is quarantined fail-closed.

### Exactly-once recursive allocation

Recursive discovery uses the completed worker result commitment as an
`allocation_key`.

OCTOPUS derives deterministic node identities from:

```text
caller node
allocation key
selected operator id
```

If reconciliation repeats after a process crash, the same child nodes are
reused. A partial deterministic allocation fails loudly rather than being
silently completed.

This closes the critical crash window:

```text
worker result committed
  -> children allocated
  -> process crash
  -> reconcile again
  -> same children recovered
  -> parent self-complete
```

without duplicate subtrees.

### Local/core execution boundary

The current external WorkerBroker continues to admit only the validated
scheduler species.

Roles outside that set, including GREMLIN core boundaries and roles not yet
promoted onto the external scheduler carrier, appear explicitly in the local
frontier. They are never silently dispatched to an unsupported worker queue.

Local execution uses the same lifecycle contract:

```text
mark_started
-> optional OCTOPUS discovery
-> result commitment
-> mark_self_complete
-> local join closure
```

### Local closure

The executor closes completed non-root subtrees deepest-first.

Before closing a node it explicitly:

- drains open satellites away from the closing center;
- moves the computational barycenter when required;
- preserves the authority root;
- leaves the root open for final aggregation/governance.

There is no implicit global BELZEBUB barrier in this path.

## New validation targets

The execution bridge adds tests for:

- deterministic and idempotent worker dispatch;
- recovery from started-but-not-yet-enqueued state;
- rejection of deterministic task payload drift;
- worker/local frontier separation;
- worker discovery -> OCTOPUS -> recursive subnode;
- crash after child allocation but before parent self-complete;
- malformed discovery quarantine;
- local-role completion without WorkerBroker;
- local-role recursive discovery;
- deepest-first local subtree closure;
- execution-id task namespace separation;
- exactly-once deterministic OCTOPUS allocation.


## Orbital base+delta context lineage

The dynamic execution topology is now paired with an immutable context lineage.

A node context is not defined by its current orbital center. Instead each node
binds once to a committed base frame and a local delta:

```text
materialized(node)
  = materialized(base)
  - explicit deletes
  + explicit sets
```

The frame records:

- node id;
- base node id;
- base frame commitment;
- set-values delta;
- explicit delete keys;
- materialized-context commitment;
- frame commitment;
- lineage depth.

This makes context reproducible even when the execution topology later
`recenter()`s the node.

### Context and topology are deliberately different graphs

```text
execution center: mutable
caller provenance: immutable
context base: immutable after binding
```

A node may move from center A to center B while continuing to use the same
committed context base. Recentring therefore changes scheduling locality, not
the historical meaning of the node input.

### Receiver-owned delta transport

The canonical WorkerBroker task stores a full self-contained context packet.
At claim time the worker may declare verified frame commitments already held in
its local cache.

GREMLIN validates the canonical full packet first, then derives a
receiver-specific shortened packet. The shortened packet may contain only the
frames after the deepest known base.

The task commitment never changes.

The worker SDK verifies the shortened packet against its local committed base
before materialization and only then adds newly verified frames to its bounded
cache.

This makes the intended orbital-context flow executable:

```text
root shared context
  -> child delta
      -> grandchild delta
          -> worker cache reuse
```

rather than repeatedly serializing the complete ancestor context for every
node.

### Claim atomicity

Transport reduction precedes lease mutation.

If packet verification or reduction fails:

```text
task.state = QUEUED
lease_id   = None
```

No malformed transport projection can strand a task inside an active lease.

### Claim boundary

Current receipts report:

- full context packet bytes;
- transported context packet bytes;
- cache-hit task count;
- receiver-known frame count;
- byte saving fraction;
- canonical task commitment unchanged = true;
- token saving claim = false.

The byte metric is a transport fact, not an end-to-end speedup claim.


## Lease-level sibling context deduplication

Per-worker cache removes repeated ancestry across different claims. v0.2 now
also removes repeated ancestry among sibling tasks inside the same claim.

For a multi-task lease, full committed node packets are first verified and then
compiled into one lease context bundle containing each required frame at most
once. Task payload projections contain compact target references instead of
duplicate frame chains.

The worker verifies the bundle once, stages all frame updates, validates every
task reference and transport commitment, materializes independent deep-copy
contexts for handlers, and only then commits the verified cache update.

This keeps three invariants separate:

```text
canonical task commitment  -> immutable queued semantics
bundle commitment          -> shared lease context frame set + task targets
transport commitment       -> exact delivered task projection
```

The optimization is permitted only when lossless reconstruction is verified.
