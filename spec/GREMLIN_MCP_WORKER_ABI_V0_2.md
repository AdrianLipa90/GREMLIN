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

The external Worker ABI accepts scheduler-backed specialist, sensor, transform and synthesis roles:

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
BELZEBUB
```

`HUMMINGBIRD` remains the capture stage and `OCTOPUS` remains the routing stage inside GREMLIN. `GREMLIN` remains the aggregate root.

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
