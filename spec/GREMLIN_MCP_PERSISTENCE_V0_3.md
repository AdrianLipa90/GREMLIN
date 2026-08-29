# GREMLIN MCP Persistence v0.3

Status: IMPLEMENTED / standalone research persistence layer.

## Goal

Make the standalone GREMLIN MCP Worker ABI survive server restarts without depending on NOEMA or `/dev/shm/ciel_noema`.

The persistence layer is local and explicit. Native 36D execution authority remains outside the MCP adapter.

## Storage model

The durable backend is SQLite with:

```text
journal_mode = WAL
synchronous = FULL
foreign_keys = ON
```

Default Worker ABI v0.2 process-memory behavior remains available. Durable mode is selected with:

```text
gremlin-mcp --state-path /path/to/gremlin-worker.sqlite3
```

or:

```text
GREMLIN_MCP_STATE_PATH=/path/to/gremlin-worker.sqlite3 gremlin-mcp
```

## Persisted records

The store persists three record classes:

```text
WORKER
TASK
LEASE
```

Workers retain declared species, capabilities, vector width, maximum batch size and heartbeat timestamps.

Tasks retain payload, task commitment, state, lease lineage and candidate result commitment.

Leases retain worker, species, exact task set, issue time and expiry.

## Restart semantics

On startup the persistent broker hydrates workers, tasks and active leases. It validates:

- store keys match embedded record identifiers;
- task payloads reproduce the recorded BLAKE2b task commitments;
- task states are valid;
- every persisted lease references an existing registered worker;
- the worker is registered for the leased species;
- every leased task points back to the same lease, worker and species.

Any hydration inconsistency fails closed.

Expired leases are reaped during hydration and their tasks return to `QUEUED`.

A non-expired lease may be completed after a server restart by the same registered worker.

## Authority boundary

Persistence changes durability only. Every MCP worker result remains:

```text
status = CANDIDATE
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

SQLite state is therefore coordination/provenance state for the standalone MCP path, not a substitute for native GREMLIN/NOEMA authority.

## Validation

`tests/test_gremlin_mcp_persistence_v03.py` covers:

1. WAL mode is active;
2. worker/task/lease state survives restart;
3. an active lease can be completed after restart;
4. the completed candidate result survives a second restart;
5. task-payload corruption that breaks the recorded commitment fails closed;
6. the MCP server can switch explicitly from process memory to a durable state path.
