# GREMLIN MCP Bestiary Pipeline v0.4

Status: IMPLEMENTED / explicit-route research pipeline.

## Goal

Expose the existing Bestiary topology through a small high-level MCP workflow so an MCP host does not have to manipulate the worker queue one task at a time.

## Pipeline

```text
caller-provided route mask
  -> SPECIALIST TASKS
  -> external animal workers
  -> CANDIDATE outputs
  -> COLLECT
  -> BELZEBUB synthesis task
  -> CANDIDATE synthesis
```

The v0.4 pipeline deliberately requires an explicit specialist route mask. It does not silently claim that the standalone adapter already contains a semantic OCTOPUS router.

Allowed fanout specialists:

```text
SPIDER
RAVEN
HOUND
MOLE
OWL
ANT
MANTIS
```

BELZEBUB is not accepted in the initial fanout. It is queued only after every supplied specialist task reaches `DONE`.

## MCP tools

### `gremlin_fanout`

Input:

- JSON payload;
- explicit specialist list;
- optional request id.

Output binds each specialist to a deterministic task id and recorded task commitment.

### `gremlin_collect`

Reads the exact task ids supplied by the caller and reports current task states and candidate outputs.

### `gremlin_synthesize`

Requires every supplied specialist task to be complete. It creates one BELZEBUB task containing:

- specialist species;
- task id;
- task commitment;
- result commitment;
- candidate output.

Incomplete specialist sets fail closed.

## Authority

All pipeline outputs retain:

```text
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

The high-level MCP pipeline therefore coordinates research candidates only. It does not promote BELZEBUB or GREMLIN output to canon.

## Persistence

When the server is started with SQLite WAL state, the queued specialist and BELZEBUB tasks use the same durable WorkerBroker as direct Worker ABI calls. The pipeline itself does not require an additional hidden orchestration database.

## Validation

`tests/test_gremlin_mcp_pipeline_v04.py` covers:

1. explicit multi-specialist fanout;
2. incomplete collection state;
3. synthesis rejection before specialist completion;
4. specialist worker completion;
5. complete collection;
6. BELZEBUB queueing after completion;
7. rejection of BELZEBUB as an initial specialist route;
8. MCP discovery of the three pipeline tools.
