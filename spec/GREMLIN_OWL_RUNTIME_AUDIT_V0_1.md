# GREMLIN OWL Runtime Audit v0.1

Status: CANDIDATE_ONLY

## Purpose

OWL already performs GREMLIN's epistemic evidence audit. Runtime Audit extends the same evidence boundary to claims about GREMLIN itself: performance, reliability, errors, retries and observable execution cost.

The invariant is:

```
OWL = OBSERVE -> AUDIT -> PROPOSE
OWL != MUTATE
```

No runtime finding grants execution, repository-write, publication or canon authority.

## Per-use receipt

Every instrumented runtime call emits a `GREMLIN_OWL_USE_RECEIPT_V0_1` record containing:

- trace id and tool/component name;
- start/end timestamps and observed duration;
- commitment to call arguments, never the raw arguments;
- commitment to successful output, never the raw output;
- PASS/ERROR state and typed error code where available;
- explicitly exposed numeric runtime metrics when present;
- optional build/config/hypercrystal identifiers supplied by environment;
- append-only sequence, previous-record hash and current record hash.

The ledger is a BLAKE2b-256 hash chain. A broken sequence, broken previous hash or modified record marks the auditor `DEGRADED` on replay.

## Privacy and provenance boundary

Raw prompts, payloads, outputs, credentials, cookies and source documents are not persisted by this layer. Commitments bind an execution to separately retained evidence without turning telemetry into a second content store.

OWL does not invent hidden model telemetry. A metric that the runtime does not expose remains unobserved.

## Online statistics

For each instrumented tool OWL maintains:

- call/success/error counts and error rate;
- observed latency distribution using Welford online mean/variance;
- latency EWMA;
- online summaries for exposed retry, tool-call, memory-I/O, token or explicit latency metrics.

The update cost is constant with respect to history length after startup.

## Improvement candidates

v0.1 may emit deterministic `GREMLIN_OWL_IMPROVEMENT_CANDIDATE_V0_1` records for:

- elevated error rate after a minimum evidence count;
- recent EWMA latency regression against the tool's accumulated distribution;
- persistent retry burden when retry metrics are exposed.

A candidate contains the measured evidence and a proposed next experiment. It always carries:

```
status = CANDIDATE_ONLY
auto_apply = false
mutation_allowed = false
canon_allowed = false
```

The intended continuation is OWL -> HOUND for clustering/falsification and then an explicitly governed GREMLIN/RAPHAEL experiment when authorized.

## Persistence

The default ledger resolves through the canonical GREMLIN installation paths to:

```
<logs_dir>/owl-runtime-audit-v01.jsonl
```

`GREMLIN_OWL_AUDIT_PATH` may override the location. `:memory:` is reserved for tests or explicitly ephemeral runs. `GREMLIN_OWL_AUDIT_FSYNC=1` requests fsync after each receipt.

On process start the existing ledger is replayed, its sequence/hash chain is verified, and online statistics are reconstructed. Tampering therefore degrades the audit state instead of silently creating a new baseline.

## Runtime coverage

The normal reference and licensed-product MCP surfaces are instrumented through the existing central MCP error boundary. Hive, Hive Authority, PhaseNav VCS, evidence-kind, evidence-origin, quorum and dual-use MCP surfaces use the semantics-preserving OWL boundary directly.

The wrapper preserves the wrapped function's return value and exception type. Audit failures are surfaced as a degraded OWL status and runtime warning rather than being silently ignored or replacing the primary operation's error.

## Claim boundary

OWL Runtime Audit can establish properties of observed software runs under identified configurations. It cannot by itself establish scientific truth, physical realization, consciousness, safety in untested environments or model-quality claims that have not been operationalized by a benchmark.
