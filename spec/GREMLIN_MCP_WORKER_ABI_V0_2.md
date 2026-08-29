# GREMLIN MCP Worker ABI v0.2

Status: CANDIDATE / standalone MCP worker contract.

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

The external Worker ABI accepts scheduler-backed specialist and synthesis roles:

```text
MANTIS
ANT
RAVEN
HOUND
OWL
SPIDER
MOLE
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

When no species is explicitly requested, registered species are considered in descending scheduler cadence.

Lease duration defaults to 30 seconds and is bounded to 1..300 seconds. Expired leases are returned to `QUEUED` state.

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

v0.2 worker registry, leases, queued tasks and results are process-resident:

```text
state_persistence = PROCESS_MEMORY_V0_2
```

Restarting the standalone MCP server therefore resets Worker ABI state. Durable append-only/WAL-backed worker state is a later gate and must preserve the same task commitments, exact lease lineage and fail-closed authority rules.

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
