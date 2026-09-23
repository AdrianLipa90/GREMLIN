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

## Migration status and next gate

The dynamic execution bridge is now implemented on this branch:

```text
dynamic fabric
  -> executable frontier
  -> WorkerBroker enqueue/claim
  -> node completion receipt
  -> recursive allocation
  -> local join reduction continuation
  -> subtree closure
```

The old flat/global path remains available for compatibility, but it is no
longer architecturally required by the candidate orchorbital path.

The next gate is measurement and runtime hardening rather than another routing
bridge:

```text
frozen workloads
  -> recursive-vs-flat critical-path benchmark
  -> resident worker/shared-memory benchmark
  -> failure/restart benchmark
  -> only then decide production cut-over
```

No 200x claim is admitted before those measurements.


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

The canonical Bestiary split is now explicit:

```text
16 dynamic workload species
4 control-plane species
```

The dynamic worker set is every Bestiary role except:

```text
HUMMINGBIRD
OCTOPUS
GREMLIN
FERRET
```

ELEPHANT and BEES therefore belong to the WorkerBroker frontier. Their lack of
dedicated validated PhaseNav carriers does not demote them to local-core;
instead their carrier-anchor contribution is neutral until separately
validated.

Adaptive operator sets are fail-fast validated and cannot contain control-plane
or unknown species. This prevents OCTOPUS/GREMLIN/FERRET/HUMMINGBIRD from being
accidentally allocated as ordinary workload nodes.

The local frontier is reserved for explicit control-plane nodes. Local
execution uses the same lifecycle contract:

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


## Lease-level context bundle

Per-worker cache reuse removes repeated ancestor frames across consecutive
claims, but without another layer a multi-task lease could still carry the same
shared ancestor once per task.

v0.2 therefore supports a lease-level context bundle.

When a lease contains at least two tasks with committed orchorbital context
packets, WorkerBroker:

1. verifies every canonical full packet before changing task state;
2. deduplicates identical frame commitments across the selected tasks;
3. emits every required unique frame at most once in a deterministic
   topological order;
4. emits one compact task-local reference per context-bearing task;
5. binds the projected task payload to its canonical task with a separate
   domain-separated transport commitment;
6. only then mutates tasks to LEASED.

The canonical task payload and canonical task commitment remain unchanged in
broker storage.

Single-task leases retain the existing packet path for compatibility.

The bundle is itself commitment-bound and the worker SDK verifies it
transactionally before exposing any materialized context to the handler.
If any task reference, frame, bundle commitment or projected payload is
invalid, the handler is not called and the verified context cache is not
partially updated.

## Context-aware batch routing

The geometry/phase scheduler now accepts an optional privacy-safe context
affinity map.

For each queued task WorkerBroker may derive only the ordered set of committed
context-frame hashes. No raw context text is passed into the affinity layer.

The original seed selection remains unchanged. During subsequent same-species
batch construction, context ancestry adds a bounded locality bonus:

```text
geometry / state score
+ bounded context-ancestry affinity
```

The current context-affinity weight is deliberately small relative to the
existing phase/state score. It is intended to break or gently steer comparable
routing choices, not to bypass readiness, phase geometry, noise or urgency.

This creates the intended execution behavior:

```text
A1 selected as seed
A2 shares A-parent context
B1 has comparable phase but different branch

=> prefer A2 when the phase/state costs are comparable
```

The scheduler receipt exposes:

- whether context affinity was active;
- the configured affinity weight;
- mean selected context affinity.

This is now a routing property, not merely a post-selection compression trick.

## Transport commitment boundary

Receiver-specific transport projection is intentionally distinct from the
canonical task commitment.

Every delivered task view may carry:

```text
transport_commitment
```

which binds:

- task id;
- worker species;
- canonical task commitment;
- delivered payload projection;
- lease context-bundle commitment when present.

The worker SDK verifies this commitment before context materialization or
handler invocation. Mutation of either a bundle reference or any other
projected payload field after claim is therefore detected fail-closed.

## Additional validation targets

The v0.2 suite additionally checks:

- multi-task leases deduplicate common context frames;
- single-task leases preserve packet compatibility;
- bundle reconstruction equals canonical materialized context exactly;
- bundle validation is transactional in the worker SDK;
- handler mutation cannot alias back into verified cache state;
- projected-payload tampering is rejected before handler invocation;
- per-task packet cache updates are claim-transactional;
- optional scheduler context affinity leaves the legacy path inactive when no
  affinity is supplied;
- equal-geometry routing prefers the sibling sharing more committed orbital
  ancestry;
- WorkerBroker uses that affinity in the real claim path;
- bundle and cache optimization do not alter canonical task commitments.

No 200x, token, billing or end-to-end latency claim follows from these
structural and byte-transport results alone.


## Parent-species reduction continuation

A local join is no longer allowed to collapse into closure without semantic
integration.

For any node with join children:

```text
self_complete(parent)
children resolved
    !=
subtree closed
```

The fabric requires an explicit `reduction_complete` commitment before the
joined parent may close.

For WorkerBroker-dispatchable species the executor now returns the completed
join to the **same parent species** as a deterministic continuation task.

Example:

```text
SPIDER
  -> invokes OWL
OWL
  -> returns audit candidate
SPIDER
  <- receives reduction packet:
       own SPIDER result
       + exact OWL effective result
       + commitment of the joined input set
SPIDER
  -> emits integrated reduction candidate
subtree may close
```

This does not require BELZEBUB as a global barrier. BELZEBUB may still be
selected as an ordinary capability module when the route requires synthesis,
but local join semantics do not hard-code it.

The reduction worker task ID is deterministically derived from:

```text
execution_id
parent node id
reduction_input_commitment
```

so enqueue/reconcile is replay-safe.

Reduction tasks may not recursively discover new children after the original
join set has been sealed by parent self-completion. Such an output is
quarantined fail-closed rather than mutating the completed join contract.

## Automatic recursive obligation dispatch

Dynamically allocated child nodes no longer require an external caller to
invent a new ad-hoc payload before they can execute.

The executor can generate a canonical obligation envelope containing:

- execution id;
- node id;
- species;
- obligations;
- caller provenance;
- current center reference;
- invocation depth;
- authority root.

Domain context remains in the committed orbital context packet.

Explicit per-node payload overrides remain supported. Automatic dispatch does
not overwrite or re-enqueue an already-existing custom task: an execution-
started node is retried automatically only when its deterministic task is
actually absent.

## Non-blocking orchestration step

`orchestration_step()` advances exactly one deterministic runtime iteration.
It does not wait for workers and performs no background work.

One step:

1. reconciles completed ordinary worker tasks;
2. closes every locally resolvable subtree;
3. reconciles completed parent reduction continuations;
4. closes newly reduced subtrees;
5. dispatches newly eligible reduction continuations;
6. dispatches newly ready ordinary worker nodes with automatic obligation
   envelopes or explicit overrides;
7. returns the new frontier and topology commitments.

Repeated calls therefore advance the recursive fabric without a central
global synchronization barrier.

The integration test covers the complete sequence:

```text
parent worker result + discovery
 -> automatic child allocation
 -> automatic child dispatch
 -> child worker result
 -> child close
 -> automatic parent reduction dispatch
 -> parent reduction result
 -> parent close
```

with the authority root remaining open.

## Routing locality layers now implemented

The current v0.2 routing path now composes four distinct locality mechanisms:

```text
1. fabric graph locality
   caller / center / coordination points

2. T^36 phase-state locality
   geometry scheduler

3. committed context ancestry affinity
   sibling/subtree batch preference

4. receiver-cache locality
   species + task preference for already-held verified frames
```

Context affinity and receiver-cache affinity are bounded scheduler biases, not
authority signals and not semantic truth claims.

Dynamic center migration remains separate from immutable context lineage.
Already committed worker tasks are not silently rewritten when a center moves.


## Durable runtime checkpoint / restore

The orchorbital runtime is now restartable without collapsing its dynamic
topology into the older flat WorkerBroker model.

Three runtime layers expose commitment-bound full checkpoints:

```text
OrchorbitalFabric
OrbitalContextStore
OrchorbitalExecutor
```

These are combined into one runtime envelope:

```text
GREMLIN_ORCHORBITAL_RUNTIME_CHECKPOINT_V0_1
```

and may be persisted in a dedicated SQLite WAL store.

### Separation from WorkerBroker durability

The runtime checkpoint deliberately does **not** duplicate WorkerBroker state.

```text
orchorbital runtime WAL
    fabric topology
    immutable context lineage
    local/core results
    semantic reduction results

worker WAL
    worker registrations
    canonical tasks
    leases
    candidate results
```

The executor checkpoint records that WorkerBroker persistence is externally
required. During restore, completed worker nodes are verified against the
restored broker task/result commitments before the executor is admitted.

Queued or in-flight deterministic tasks may still be retried by the normal
executor recovery path when missing. Completed worker results may not be
silently reconstructed or invented.

### Fabric checkpoint

The full fabric restart state contains:

- every node including caller and mutable center relations;
- raw obligations;
- causal and local-join graphs;
- coordination edges and n-node coordination points;
- replacement/failover mappings;
- computational barycenter;
- event sequence and complete event log;
- node-id counter;
- lifecycle and reduction commitments;
- the privacy-safe topology commitment.

Restore verifies the envelope commitment, reconstructs all internal relations,
runs the normal fabric invariants, and requires the restored topology
commitment to equal the recorded one.

### Context checkpoint

Context persistence stores immutable base+delta frames only.

Materialized contexts are not duplicated. Restore rebuilds them through the
normal frame binding validators and requires each reconstructed:

- base commitment;
- frame commitment;
- materialized commitment;
- depth

to match the checkpoint.

This preserves the separation between mutable execution centers and immutable
context lineage across process restarts.

### Executor checkpoint

Executor-only state stores:

- execution id;
- operator tiers/capabilities/costs;
- resource budget;
- local-core result payloads;
- semantic reduction result payloads;
- reduction-input commitments;
- exact fabric/context commitments.

Worker task/lease/result state is excluded.

### Atomic runtime store

`SQLiteOrchorbitalRuntimeStore` uses:

```text
journal_mode = WAL
synchronous = FULL
BEGIN IMMEDIATE
read-back verification before COMMIT
```

with one committed runtime row per execution id.

The outer runtime commitment binds the exact inner fabric, context and executor
checkpoints. Tampering with stored JSON while leaving the commitment column
unchanged therefore fails closed before restore.

### Mid-orbit restart target

The dedicated restart test checkpoints the runtime in this state:

```text
parent local work complete
child returned and CLOSED
parent reduction continuation QUEUED
process restart
```

After reopening both the worker WAL and runtime WAL, the test requires:

```text
same topology commitment
same parent/child materialized contexts
same deterministic parent reduction task id
same queued reduction task
parent reduction completes
parent subtree closes
authority root remains OPEN
global synthesis barrier remains false
```

No performance multiplier follows from restart durability itself.


## Restart and checkpoint contract

The orchorbital runtime now defines three independent committed restart layers:

```text
fabric checkpoint
context-lineage checkpoint
executor checkpoint
```

The WorkerBroker state is deliberately external to the executor checkpoint.

### Fabric checkpoint

The fabric checkpoint binds:

- every node instance and lifecycle flag;
- caller/center/authority relationships;
- causal edges;
- local join edges;
- coordination edges and n-node coordination points;
- replacements;
- barycenter;
- event sequence and append-only event history;
- topology commitment.

Any mutation of checkpoint content without recomputing the domain-separated
checkpoint commitment fails closed.

### Context checkpoint

The context checkpoint stores immutable base+delta frames only. Materialized
contexts are not duplicated in the checkpoint.

The context checkpoint is bound to the exact fabric topology commitment. It
therefore cannot be restored against another fabric, even if its frame content
would otherwise parse.

### Executor checkpoint

The executor checkpoint binds:

- execution id;
- exact operator tiers and capability sets;
- resource budget;
- maximum exact-cover state budget;
- local result payloads;
- local reduction payloads;
- reduction-input commitments;
- the fabric topology commitment;
- the context checkpoint commitment when a context store is present.

Worker payload/result state is not copied into this checkpoint.

### Durable WorkerBroker boundary

Worker task commitments, result commitments and lease lineage remain owned by
the WorkerBroker persistence layer.

On restore, every self-complete worker node is checked against the external
broker. Missing or different worker result state fails closed.

The restart invariant is therefore:

```text
restored fabric commitment
+
restored context commitment
+
restored executor commitment
+
externally durable worker result commitments
=
same logical execution
```

A fresh empty WorkerBroker is not accepted as a substitute for the persisted
broker state of an execution that already contains completed worker nodes.

### End-to-end restart gate

The dedicated checkpoint test now exercises:

```text
worker parent
 -> recursive worker child
 -> child close
 -> local parent reduction
 -> parent close
 -> local/core result
 -> fabric checkpoint
 -> context checkpoint
 -> executor checkpoint
 -> close SQLite broker
 -> reopen durable broker
 -> restore all three orchorbital layers
 -> verify identical checkpoint commitments
 -> run another non-blocking orchestration step
```

No completed worker task may be re-enqueued after the restore.

Tampering with any of the three checkpoint layers must fail closed.


## Role partition and local execution adapters

The Bestiary role registry is now partitioned into three architectural classes.

### Control-plane / authority boundaries

```text
HUMMINGBIRD
OCTOPUS
GREMLIN
FERRET
```

These are not ordinary adaptive exact-cover workload operators.

- HUMMINGBIRD is the capture boundary.
- OCTOPUS is the allocator/router.
- GREMLIN is the aggregate authority root.
- FERRET is the explicit actuation boundary.

Supplying one of these roles as an adaptive workload operator fails closed.

### Routable execution modules

All remaining Bestiary roles may participate in exact-cover planning.

Roles with validated external scheduler carriers continue through WorkerBroker.

### Local execution modules

```text
ELEPHANT
BEES
```

These roles are routable but do not yet receive a synthetic PhaseNav carrier
merely to make external dispatch convenient.

They may execute through an explicit `LocalAdapterRegistry`.

A local adapter must declare:

- species;
- stable adapter id;
- version;
- 64-hex implementation commitment;
- synchronous handler;
- optional synchronous local reducer;
- `replay_safe=true`;
- `side_effects=false`.

The registry rejects control-plane roles and any adapter that requests
side-effectful or non-replay-safe semantics.

No default local adapter is silently installed.

If a BEES/ELEPHANT node becomes ready without a registered adapter, the
orchestration receipt reports `adapter_required` and leaves the node OPEN and
unstarted.

### Automatic local frontier

When a valid adapter exists, one non-blocking orchestration iteration may:

```text
local-ready BEES/ELEPHANT
 -> seal execution start
 -> invoke replay-safe adapter
 -> validate finite JSON output
 -> apply optional OCTOPUS discovery
 -> bind result commitment
 -> local join closure
```

If the adapter raises, the node fails explicitly.

If adapter output cannot satisfy the runtime contract, the node is quarantined.

There is no fallback to an unrelated worker species.

### Local join reduction

A local adapter may also register a reducer.

Once a local node is self-complete and all join children resolve, its reducer
receives the same committed local reduction packet used by worker-backed
reductions.

This removes the remaining need to route BEES/ELEPHANT reductions through a
global BELZEBUB barrier.

### Adapter restart identity

Executor checkpoints store the adapter manifest but never callable code.

Restore requires an exactly matching manifest, including the
`implementation_commitment`.

This detects declared implementation drift across restart. The commitment must
therefore be the hash of the adapter artifact/version actually being loaded;
the runtime does not pretend that a caller-supplied false hash proves code
identity.

The resulting role model is:

```text
control plane != workload execution

workload execution
  -> external worker carrier
  -> or explicit replay-safe local adapter
```

with no silent third path.


## Shared discovery context frames

Recursive discovery now carries information as well as topology.

A worker/local node may emit bounded discovery `handoff` data. OCTOPUS remains
the only allocator: the caller cannot select child species directly.

For one discovery fanout GREMLIN creates one immutable shared context frame:

```text
parent node context
    |
    v
CTX:DISC:<commitment>
    parent_result_commitment
    bounded handoff
    |
    +---- child A empty/local delta
    +---- child B empty/local delta
    +---- child C empty/local delta
```

Caller provenance stays on the execution nodes. The shared context frame is not
an execution node and cannot become an orbital center or authority root.

The handoff is bounded to 128 keys and 65536 canonical JSON bytes. Malformed or
oversized handoff fails closed before child allocation.

This avoids copying the same parent result/handoff into every child frame.

## Delta-only context storage

`OrbitalContextStore` no longer retains one full materialized context per frame.

Persistent in-process representation is:

```text
immutable base+delta frames
+ bounded LRU materialization cache
```

Materialization is reconstructed through frame lineage and every reconstructed
step is checked against its materialized commitment.

The cache size is a performance parameter and does not alter frame or packet
commitments. Evicted frames must reconstruct identically.

Benchmark receipts report serialized-storage proxies only:

- eager full-materialization bytes proxy;
- delta frame bytes proxy;
- bounded cache bytes proxy;
- delta+cache reduction fraction.

These are not Python heap measurements.

## Exact routing hot-path indexes

The WorkerBroker routing path now uses:

```text
species queue index
receiver/context affinity cache
precomputed immutable TaskPhaseState
lease expiry min-heap
reused species metrics + centroid
```

All indexes are derived from canonical broker state and rebuilt after durable
SQLite hydration.

The synthetic routing-index benchmark may exceed 200x in **candidate inspection
reduction** under heavily skewed multi-species queues. This does not establish a
200x end-to-end speedup.


## Execution-role partition

GREMLIN v0.2 uses one canonical role partition.

```text
control plane / authority boundaries:
HUMMINGBIRD, OCTOPUS, GREMLIN, FERRET

routable workload roles:
all Bestiary roles except the control-plane set

local execution modules without external carrier:
ELEPHANT, BEES
```

Control-plane roles cannot be admitted as adaptive exact-cover execution
operators.

`ELEPHANT` and `BEES` are valid workload operators, but they require an
explicit local adapter until validated external worker carriers exist.

### Local adapter contract

A local adapter must declare:

- species;
- adapter id;
- adapter version;
- a 64-hex implementation commitment;
- replay-safe = true;
- side-effects = false;
- optional local reducer.

The implementation commitment is included in the executor checkpoint manifest.
A durable runtime restore therefore rejects a missing or different local
adapter manifest.

No callable code is serialized into the checkpoint.

Local adapter execution is integrated into the same non-blocking orchestration
step as WorkerBroker execution. A local module may recursively discover worker
children, and an optional local reducer may close its subtree once those
children resolve.

Missing adapters never silently fall back to another species. The node remains
open and is reported in `adapter_required`.

### Durable façade restore

`DurableOrchorbitalRuntime.restore(..., local_adapters=...)` forwards the
registry through the SQLite runtime store into executor restore. This keeps
store-level restore and façade-level restore semantically identical.
