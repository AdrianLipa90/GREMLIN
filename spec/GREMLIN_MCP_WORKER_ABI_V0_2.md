# GREMLIN MCP Worker ABI v0.2

Status: CANDIDATE / standalone MCP worker contract / geometry-phase-state scheduling and receiver-owned orbital context cache negotiation active.

## Goal

Allow an arbitrary local or remote backend to participate as a GREMLIN Bestiary animal through Model Context Protocol without receiving GREMLIN native authority and without requiring NOEMA or `/dev/shm/ciel_noema`.

The worker contract is deliberately pull-based:

```text
MCP HOST / BACKEND
  -> register worker
  -> GREMLIN queues routed task
  -> worker claims bounded same-species lease
  -> worker computes locally
  -> worker submits exact lease result set
  -> GREMLIN stores CANDIDATE envelope
```

GREMLIN never calls a worker-supplied URL. This avoids callback trust, SSRF and hidden execution channels in v0.2.

## External worker species

The external Worker ABI accepts the 16 dynamic workload roles from the
canonical 20-role Bestiary registry:

```text
SPIDER
RAVEN
HOUND
MOLE
OWL
ANT
MANTIS
FOX
BEAVER
BAT
CANARY
SERPENT
CHAMELEON
ELEPHANT
BEES
BELZEBUB
```

The four control-plane roles remain outside ordinary workload queues:

```text
HUMMINGBIRD  capture ingress
OCTOPUS      routing/allocation
GREMLIN      authority/aggregate root
FERRET       explicitly authorized actuation boundary
```

Historical compatibility note: at the earlier v0.2.4 boundary, ELEPHANT and
BEES were worker-schedulable before dedicated PhaseNav carriers were promoted,
so explicit T^36 scheduling used an anchor-neutral contribution. That limitation
is superseded by the active v0.2 20-role carrier surface. The current v0.2.6
runtime has software-validated v0.2 carriers for ELEPHANT and BEES; this remains
a computational/runtime claim, not a physical analog-hardware claim.

## Registration

Tool:

```text
gremlin_worker_register
```

Fields:

```text
worker_id      stable caller-selected identifier, 1..128 chars
species        one or more supported animal names
capabilities   optional descriptive capability tags
vector_width   worker vector width hint, default 8
max_batch      hard worker batch ceiling, 1..128
```

Registration is idempotent for a worker ID and refreshes its current capabilities while retaining the original registration timestamp.

## Task admission

Tool:

```text
gremlin_worker_enqueue
```

A task contains:

```text
task_id
species
payload
BLAKE2b task commitment
state
```

Payload must be finite JSON. A repeated `task_id` is idempotent only when the species and payload commitment are identical. Reuse of the same ID for different content fails closed.

## Lease claim

Tool:

```text
gremlin_worker_claim
```

A claim is always a same-species batch. The maximum claim size is:

```text
min(requested_limit, worker.max_batch, orbital_lane_width, queued_count)
```

where `orbital_lane_width` is derived by the existing Bestiary vector-lane planner from the registered worker `vector_width` and the species mass/orbit cadence.

Task selection is no longer FIFO-primary.

When no species is explicitly requested, registered non-empty species queues are scored by the candidate geometry/phase/state scheduler defined in `GREMLIN_GEOMETRY_PHASE_STATE_SCHEDULER_V0_1`. Queue selection uses current T^36 cluster coherence, readiness, noise, urgency, bounded backlog and explicit-phase evidence. Legacy orbital cadence is only a secondary tie-break where a legacy cadence profile exists.

Within a selected species, the lease batch is constructed by phase/state proximity rather than task creation order. FIFO order is retained only as a comparison proxy in the scheduler receipt.

The maximum claim size is additionally geometry-adaptive: coherent queues may use a wider vector lane while noisy queues contract, always under worker `max_batch` and the legacy orbital ceiling when one exists.

Lease duration defaults to 30 seconds and is bounded to 1..300 seconds. Expired leases are returned to `QUEUED` state.

## Geometry / phase / state scheduling metadata

A task may carry committed scheduler metadata inside its payload under:

```text
_gremlin_scheduler
```

with optional exact `phase36`, readiness, temperature, urgency and noise fields. If no exact phase is supplied, GREMLIN derives a deterministic locality-oriented scheduling fingerprint from canonical payload tokens. This fallback is a scheduling coordinate only and is not promoted as semantic truth.

A `ready=false` task remains queued but is not lease-eligible until its committed task content/state is replaced through a new task identifier/content commitment. The Worker ABI does not mutate an existing task commitment in place.

Every successful lease contains a scheduler receipt with `fifo_primary=false`, selected geometry metrics, transition/noise proxies and lane width.

## Submission

Tool:

```text
gremlin_worker_submit
```

The submitting worker must own the lease. The result set must cover the exact claimed task ID set with no duplicates or omissions.

Every accepted result remains:

```text
status = CANDIDATE
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

A worker cannot promote output to canon through the MCP Worker ABI. A result that attempts a non-`CANDIDATE` envelope status is rejected.

Each result is bound to its original task commitment, worker ID and output by a BLAKE2b result commitment. The batch submission returns a separate receipt commitment.

## Pull model and backend independence

The Worker ABI does not prescribe the worker implementation. A worker may be:

- a language model;
- a deterministic program;
- a symbolic solver;
- a database/search service;
- a GPU kernel;
- a human-in-the-loop research process;
- another MCP-capable system.

Only the MCP contract and candidate/authority boundary are normative here.

## Persistence scope

The reference in-memory broker remains available, while the standalone/product
runtime may use the validated SQLite WAL broker.

Persisted state includes worker registrations, task commitments, task/result
state and active lease lineage. Expired leases are returned to QUEUED during
recovery.

Receiver context-cache hints are intentionally **not persisted** by GREMLIN.
They are supplied by the worker on each claim and therefore remain
receiver-owned capability state.

This separation preserves:

```text
durable canonical task/lease state
!=
ephemeral receiver transport cache
```

A broker restart cannot falsely claim that a worker still holds a context frame.

## MCP tools added in v0.2

```text
gremlin_worker_register
gremlin_worker_heartbeat
gremlin_worker_list
gremlin_worker_enqueue
gremlin_worker_claim
gremlin_worker_submit
gremlin_worker_result
gremlin_worker_queue
```

The original discovery/planning/reference tools remain available.

## Authority boundary

The standalone Worker ABI is not a replacement or emulation of GREMLIN native 36D authority.

```text
MCP Worker ABI -> CANDIDATE / research execution
NOEMA + PhaseNav native path -> separate native admission authority
```

No MCP worker call may grant production runtime write, execution admission or canon promotion.


## ABI v0.2.2 — orbital context cache negotiation

`gremlin_worker_claim` accepts an optional:

```text
known_context_frames: list[BLAKE2b-256 commitment]
```

with a hard bound of 4096 commitments.

The list is a receiver declaration only. It is never inserted into the canonical
task payload, task commitment, result commitment or persisted WorkerBroker
state.

If a queued task contains a verified full orchorbital context packet, GREMLIN
may create a receiver-specific transport view by removing already-known base
frames. The canonical stored task remains byte-for-byte unchanged.

The claim boundary is therefore:

```text
canonical task payload
    |
    | verify full packet
    v
receiver-specific transport projection
    |
    +-- task_commitment remains canonical
```

All transport projection is completed **before** task state is changed to
LEASED. A malformed context packet therefore fails closed while the task
remains QUEUED and no lease is created.

Unknown but well-formed cache commitments are harmless: they produce no cache
hit and the full required frame chain is delivered.

The worker SDK validates every received packet before using it, keeps a bounded
local verified context cache, and advertises only commitments actually present
in that cache on the next claim.

No model-token reduction claim is made by this ABI. Receipts expose byte counts
only; token/runtime gains require separate benchmarks.


## ABI v0.2.3 — lease context bundles and transport commitments

When two or more tasks in the same lease carry full orchorbital context
packets, GREMLIN may replace repeated per-task frame chains with one
lease-scoped bundle:

```text
_gremlin_orchorbital_context_bundle
```

The bundle is a domain-separated BLAKE2b commitment over:

- one deterministic topological sequence of unique context frames;
- the exact task -> target-frame mapping.

Each affected task receives only a compact committed target reference:

```text
_gremlin_orchorbital_context_ref
```

A frame shared by several sibling tasks therefore appears at most once in the
lease bundle.

A one-task lease keeps the v0.2.2 packet path for backwards compatibility.

### Canonical task vs transport projection

Context bundling changes the payload delivered to the worker but does not
rewrite the canonical queued task.

Therefore each delivered task view now carries a separate:

```text
transport_commitment
```

bound to:

```text
task_id
species
canonical task_commitment
delivered payload projection
lease bundle commitment (or null)
```

The canonical task commitment continues to bind the stored task. The transport
commitment binds exactly what the worker receives.

The worker SDK verifies the transport commitment before interpreting any
context reference or invoking the handler.

### Transactionality

Lease bundle validation and task-reference validation are staged before the SDK
commits new context frames to its local cache.

If any bundle, reference or transport commitment fails verification:

```text
handler_not_called = true
receiver_cache_unchanged = true
```

At the broker boundary, the bundle and every projected task view are built
before task states are mutated to LEASED.

### Performance claim boundary

Bundle receipts expose byte counts and unique-frame counts. They do not imply a
token, latency, throughput or end-to-end speedup claim.


## Receiver-cache-aware routing

The worker cache declaration is now used before transport projection as a
bounded scheduling-locality hint.

WorkerBroker derives privacy-safe context ancestry from frame commitments only.
Raw context values are not exposed to the geometry scheduler.

The hint may influence:

1. selection among otherwise comparable species queues;
2. seed selection inside the chosen queue;
3. subsequent same-species batch construction.

The locality weights are deliberately bounded below the existing phase/state
terms. Readiness and the canonical T^36/state scheduler remain active.

The intended behavior is:

```text
same/comparable geometry
+ worker already owns branch-A context
=> prefer branch-A work over an equivalent cold branch
```

The claim receipt reports whether receiver-cache affinity was active and its
bounded weight.

This is a routing optimization only. It grants no authority and makes no
end-to-end latency or speedup claim.


## ABI v0.2.4 — canonical Bestiary workload partition

The public worker-species enum now derives from the canonical 20-role Bestiary
registry rather than the older 18-role PhaseNav carrier list.

The partition is:

```text
20 Bestiary roles
= 16 dynamic workload species
+ 4 control-plane species
```

Control-plane:

```text
HUMMINGBIRD
OCTOPUS
GREMLIN
FERRET
```

Dynamic workload:

```text
SPIDER RAVEN HOUND MOLE OWL ANT MANTIS
FOX BEAVER BAT CANARY SERPENT CHAMELEON
ELEPHANT BEES BELZEBUB
```

The worker scheduler therefore admits ELEPHANT and BEES.

At the v0.2.4 revision this did **not** claim dedicated PhaseNav carriers for
those two roles: the carrier surface at that revision remained the 18 legacy
roles and ELEPHANT/BEES used an anchor-neutral species term. This historical
v0.2.4 limitation is superseded by the active 20-role PhaseNav v0.2 carrier
promotion; v0.2.6 retains the old statement only as versioned provenance.

The runtime must fail loudly if:

- the Bestiary registry is not exactly partitioned by dynamic/control-plane
  role sets;
- a control-plane role is supplied as an adaptive workload operator;
- a dynamic role disappears from WorkerBroker admission because of carrier
  registry drift.


## ABI v0.2.5 — exact routing indexes and cached immutable scheduler state

v0.2.5 removes repeated routing work without changing task semantics.

The broker now keeps derived, rebuildable runtime indexes:

```text
queued_by_species
lease_expiry_min_heap
task_context_affinity
task_phase_state
unfinished_task_count
```

These are **not** new canonical state. Canonical task, lease and result records
remain the source of truth. SQLite restore rebuilds the indexes and verifies the
persisted task/context/memory contracts before routing resumes.

### Species queue index

Claim no longer scans every task to find one species queue.

```text
old structural candidate search:
all broker tasks -> filter requested species

v0.2.5:
requested species -> queued task ids directly
```

A synthetic skew fixture with 4 target tasks and 1024 unrelated tasks yields:

```text
naive candidate inspections proxy = 1028
indexed candidate inspections      = 4
structural scan reduction ratio    = 257x
```

This is a candidate-inspection count only. It is **not** a 257x wall-clock,
latency, throughput or end-to-end GREMLIN speedup claim.

### Indexed lease expiry

Active lease expiry is maintained in a min-heap.

Claim/reap no longer scans every active lease. Completed leases may leave stale
heap entries, which are ignored by lease-id/expiry verification and periodically
compacted. SQLite hydration rebuilds the heap from canonical active leases before
expiry processing.

### Immutable task phase-state cache

Scheduler parsing of immutable task payloads now occurs at admission/hydration.
The resulting `TaskPhaseState` is reused by:

- species queue scoring;
- geometry lane metrics;
- batch selection.

Lineage checks bind cached state to task id, species, task commitment and
creation timestamp. Any mismatch fails closed.

The selected species metrics and 36D centroid computed during species selection
are reused by batch selection instead of being recomputed.

These changes are exact-path optimizations: no approximate nearest-neighbor or
heuristic candidate truncation is enabled by v0.2.5.


## ABI v0.2.6 — same-species orbital ancestry index

The queue index now has an additional privacy-safe ancestry layer for warm
receiver claims.

Canonical tasks remain indexed by species. When a canonical task contains a
verified full orchorbital context packet, GREMLIN also indexes the deepest
bounded context-frame commitments:

```text
species
  -> context frame commitment
      -> queued task ids
```

Only BLAKE2b frame commitments are used as index keys. Raw context values never
enter the routing index.

### Activation boundary

The ancestry index is intentionally conservative.

It is used only when:

1. the worker requests an explicit species; and
2. the worker supplies one or more verified-format `known_context_frames`.

Cold claims and multi-species claims retain the complete species-queue
candidate semantics.

### Smallest warm bucket

If several receiver-known frame commitments are present in the selected
species queue, GREMLIN chooses the smallest non-empty matching bucket.

This matters for nested orbital context:

```text
root commitment       -> potentially thousands of tasks
branch commitment     -> tens of tasks
local parent frame    -> a few tasks
```

A warm worker therefore begins routing from the narrowest known local branch
rather than scanning every queued task of the species.

### Fairness window

Warm locality is not an exclusive filter.

The candidate set also receives a bounded oldest-task fairness window from the
same species queue:

```text
warm ancestry bucket
+
up to min(32, max(4, requested_limit)) oldest non-local queued tasks
```

This keeps unrelated work visible to the normal phase/state/urgency scoring
instead of silently starving it.

The ancestry index reduces candidate materialization; it does not bypass the
existing geometry/phase/state scheduler.

### Queue lifecycle

An ancestry membership exists only while a task is QUEUED.

```text
enqueue  -> species index + ancestry index
claim    -> remove from both indexes before LEASED
expiry   -> return to both indexes
submit   -> remain absent because DONE
restart  -> rebuild both indexes from durable canonical task payloads
```

The index itself is ephemeral and is not persisted as authority-bearing state.

### Measurement boundary

The v0.2.6 routing benchmark uses one species only:

```text
SPIDER warm orbit tasks
SPIDER unrelated orbit tasks
```

The worker advertises a warm parent-frame commitment and the benchmark counts
how many task scheduler views must be materialized before selecting its batch.

A structural ratio above 200x therefore means:

```text
full same-species queue candidate inspections
------------------------------------------------
ancestry-index candidate inspections
```

for that synthetic fixture.

It is explicitly **not** a 200x wall-clock, model, token, or end-to-end runtime
claim.
