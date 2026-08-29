# GREMLIN

GREMLIN is the root system. OCTOPUS and BELZEBUB are writable subordinate tools with independent local `CURRENT` heads, while GREMLIN binds verified tool heads into one aggregate `SUPER_CURRENT`.

## Native authority

Authoritative runtime declarations live in `native/*.pnv` and use the existing PhaseNav Natural Coding operator vocabulary. Python is retained only as a reference/test harness.

```text
GREMLIN
├── SUPER_CURRENT
├── Triple Pulse Boot: IDENTITY -> DOMAIN -> AUTHORITY
├── REQUEST -> COUPLING -> ADMISSION
├── Natural Queue + scalar tau modulation
├── OCTOPUS
│   └── CURRENT + own content-addressed write namespace
└── BELZEBUB
    └── CURRENT + own content-addressed defensive write namespace
```

Operational runtime surface: `/dev/shm/ciel_noema`.

Persistent-memory protocol:

- GREMLIN: `OBJECT -> RECEIPT -> SUPER_CURRENT`
- OCTOPUS: `OBJECT -> RECEIPT -> CURRENT`
- BELZEBUB: `OBJECT -> RECEIPT -> CURRENT`
- event-driven; no tick requirement
- no last-writer-wins
- missing/corrupt lineage fails closed

Boot protocol:

1. `IDENTITY` pulse — verify current identity.
2. `DOMAIN` pulse — verify current live runtime generation.
3. `AUTHORITY` pulse — verify admission authority.
4. `REQUEST`.
5. `COUPLING` to the current live generation.
6. `ADMISSION` only after 3/3 pulse receipts bind the same generation.

Native witness: `native/GREMLIN_TRIPLE_PULSE_BOOT_V0_5.pnv`.

## PhaseNav prototype pipeline

An audited relation candidate can be compiled into PhaseNav character IR, converted into a deterministic reference prototype and checked by the experiment harness:

```text
SURVIVED_AUDIT
  -> PHASENAV_IR_CANDIDATE
  -> UNTRUSTED_PROTOTYPE
  -> VALIDATED_PROTOTYPE
```

`VALIDATED_PROTOTYPE` currently carries `validation_scope=REFERENCE_CONFORMANCE_ONLY`.

## Standalone MCP adapter v0.5

GREMLIN can run as a standalone Model Context Protocol server for research integration. This path does not require NOEMA or `/dev/shm/ciel_noema` for discovery, Bestiary inspection, OCTOPUS reference routing, scheduler planning, external animal-worker coordination, durable local queue state, or the existing Python reference prototype pipeline.

Install from the repository root:

```text
python -m pip install -e .
```

Run over stdio:

```text
gremlin-mcp
```

Or expose a local Streamable HTTP endpoint:

```text
gremlin-mcp --transport streamable-http --host 127.0.0.1 --port 8766
```

Default HTTP MCP endpoint: `http://127.0.0.1:8766/mcp`.

Core MCP tools:

- `gremlin_status`
- `gremlin_bestiary`
- `gremlin_species`
- `gremlin_plan`
- `gremlin_route`
- `gremlin_auto_fanout`
- `gremlin_fanout`
- `gremlin_collect`
- `gremlin_synthesize`
- `gremlin_prototype`

### OCTOPUS semantic routing v0.5

The standalone reference path now implements an auditable OCTOPUS route decision:

```text
payload
  -> gremlin_route / OCTOPUS
  -> ranked semantic + structural evidence
  -> bounded route mask
  -> gremlin_auto_fanout
  -> specialist queues
```

The v0.5 reference router is deterministic and dependency-free. It uses explicit semantic cue weights plus structural JSON evidence for `SPIDER`, `RAVEN`, `HOUND`, `MOLE`, `OWL`, `ANT`, and `MANTIS`. Every score contribution is returned to the caller; routing is therefore inspectable rather than an opaque model decision.

Each decision receives a BLAKE2b-256 `route_commitment`. Automatic fanout binds that commitment into every downstream worker task. If no positive evidence clears the configured threshold, `gremlin_auto_fanout` queues nothing and returns `NO_CONFIDENT_ROUTE_NOT_QUEUED`.

Example:

```text
gremlin_route({
  "problem": "Audit evidence for contradictions in this dependency graph",
  "dependencies": ["A->B"],
  "sources": ["paper-a"]
})
```

The explicit `gremlin_fanout` tool remains available when the MCP host already knows the desired route mask.

### High-level Bestiary pipeline

A host can now use either OCTOPUS auto-routing or an explicit route and then hand completed candidates to BELZEBUB:

```text
payload
  -> OCTOPUS route / explicit route mask
  -> SPIDER / RAVEN / HOUND / MOLE / OWL / ANT / MANTIS
  -> gremlin_collect
  -> gremlin_synthesize
  -> BELZEBUB
  -> CANDIDATE synthesis
```

`gremlin_synthesize` fails closed until every supplied specialist task is complete.

### External animal workers

Any backend that can call MCP tools can register as a scheduler-backed GREMLIN animal worker. The Worker ABI is pull-based and does not require GREMLIN to call arbitrary worker URLs:

```text
backend
  -> gremlin_worker_register
  -> gremlin_worker_claim
  -> local model / solver / search / GPU work
  -> gremlin_worker_submit
  -> CANDIDATE result
```

Worker tools:

- `gremlin_worker_register`
- `gremlin_worker_heartbeat`
- `gremlin_worker_list`
- `gremlin_worker_enqueue`
- `gremlin_worker_claim`
- `gremlin_worker_submit`
- `gremlin_worker_result`
- `gremlin_worker_queue`

External worker roles are `SPIDER`, `RAVEN`, `HOUND`, `MOLE`, `OWL`, `ANT`, `MANTIS`, and `BELZEBUB`. Capture remains owned by HUMMINGBIRD and semantic routing remains owned by OCTOPUS.

Claims are same-species batches bounded by both the worker-declared maximum and the existing mass-orbit/vector-lane scheduler. Results are bound to task lineage by BLAKE2b commitments and remain candidate-only.

For a worker running as a separate process, use one shared Streamable HTTP GREMLIN server. A stdio server belongs to the process launched by its MCP host, so launching a second stdio GREMLIN process creates a different broker unless both are intentionally pointed at the same durable state file.

The package also includes `GremlinWorkerClient`, a batch-aware helper for plugging in a model, solver, graph engine, search backend, or accelerator without reimplementing MCP plumbing:

```python
from gremlin_mcp.worker_client import GremlinWorkerClient

async def spider(batch):
    return [
        {"task_id": task["task_id"], "output": my_backend(task["payload"])}
        for task in batch["tasks"]
    ]

worker = GremlinWorkerClient(
    "http://127.0.0.1:8766/mcp",
    worker_id="my-spider",
    species=["SPIDER"],
    handler=spider,
    vector_width=8,
    max_batch=32,
)
await worker.serve()
```

A runnable skeleton is in `examples/mcp_worker_spider.py`. Its handler is intentionally only an echo demonstration; replace it with the actual backend for the selected animal role.

### Durable worker state

Without a state path, worker coordination remains process-resident. For restart-safe standalone coordination, enable the SQLite WAL backend explicitly:

```text
gremlin-mcp --transport streamable-http \
  --state-path ./gremlin-worker.sqlite3
```

or set `GREMLIN_MCP_STATE_PATH`.

Durable mode persists worker registrations, queued tasks, active leases, task commitments and candidate results. Hydration validates task commitments and lease/task lineage and fails closed on corruption. Expired leases are returned to `QUEUED` after restart.

The MCP adapter is fail-closed with respect to native authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Specifications:

- `spec/GREMLIN_MCP_SERVER_V0_1.md`
- `spec/GREMLIN_MCP_WORKER_ABI_V0_2.md`
- `spec/GREMLIN_MCP_PERSISTENCE_V0_3.md`
- `spec/GREMLIN_MCP_PIPELINE_V0_4.md`
- `spec/GREMLIN_MCP_OCTOPUS_ROUTER_V0_5.md`

## Visual research client v0.1

The local visual client exposes the prototype pipeline as a three-pane workspace:

```text
Problem & candidate | PhaseNav operator graph | Prototype / BELZEBUB / Tests / Receipt
```

Run from the repository root:

```text
python client/gremlin_web_server_v01.py
```

Open `http://127.0.0.1:8765` and use **Load example** followed by **Compile & test**.

The browser surface has zero external frontend dependencies. The local API delegates to the same `run_client_request()` implementation used by the CLI and test harness.

Visual-client authority state:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Full specification: `spec/GREMLIN_VISUAL_CLIENT_V0_1.md`.

Motto: `Verbis utor, informationem in existentiam converto.`

BELZEBUB quarantines untrusted code as data, performs semantic defensive analysis, and emits repair/immunity candidates. Quarantined content has no execution authority.

## License

GREMLIN is distributed under the **CIEL Research Non-Commercial License v2.0** (`LicenseRef-CIEL-Research-NonCommercial-2.0`). The license permits non-commercial research execution, reproducibility, benchmarking, profiling, vectorization, security review, and project-native agent/orchestration experiments while reserving commercial use, production deployment, hosted services, AI/ML development use, and model extraction for separate written authorization.

See [`LICENSE`](LICENSE) for the canonical terms.
