# GREMLIN Full System Benchmark & Ablation Suite v0.1

Status: \`IMPLEMENTED_CANDIDATE / OBSERVATIONAL_BENCHMARK / EXACT_INVARIANT_GATES\`

Date: 2026-09-20

## Purpose

This suite replaces isolated benchmark claims with one reproducible internal evaluation surface.

It has three independent verdict classes:

1. constitutional invariants;
2. semantic/performance regression;
3. runtime constitutional coverage.

No class can compensate another.

A routing speedup cannot compensate a constitutional gap.
A constitutional PASS cannot compensate a routing regression.
A low latency cannot promote an inadmissible action.

## Scope

The suite executes:

- constitutional five-channel non-bypass ablations;
- fail-closed fault injection;
- declared production/public mutation-surface constitutional coverage;
- constitutional admission latency;
- typed memory-capability validation latency;
- exact transition-certificate latency;
- append-only ledger scaling;
- research orchestration v0.2;
- OOD routing v0.6;
- Bestiary deterministic virtual topology;
- geometry phase scheduler vs FIFO proxy;
- PhaseNav scalar/vector equivalence and performance.

## Exact five-channel admissibility model

The evaluated global scalar is

\[
\sigma_G
=
\min\{
\sigma_E,
\sigma_C,
\sigma_A,
\sigma_X,
\sigma_\Theta
\}.
\]

The five channels are:

- ethics;
- capability;
- authority;
- evidence;
- parameter provenance.

Frozen ablation cases contain:

- one all-PASS case;
- for each channel, one BLOCK case;
- for each channel, one UNRESOLVED case.

For every case, the full system is compared with five ablated systems, each omitting exactly one channel.

The preregistered exact requirements are:

\[
\boxed{\text{full false ALLOW count}=0}
\]

and

\[
\boxed{\text{full false DENY count on all-PASS}=0}.
\]

Every single-channel ablation must expose at least one false ALLOW relative to the complete conjunction.

This is not a fitted performance threshold. It is an exact logical consequence of the declared admissibility algebra.

## Fault injection matrix

The frozen matrix includes at least:

1. all required inputs valid -> ALLOW;
2. missing required ethics gate -> DEFER;
3. NO-GO hit -> DENY;
4. capability deny -> DENY;
5. authority unresolved -> DEFER;
6. canonical but unbound kappa used by mutation -> DEFER;
7. forged memory-capability receipt -> REJECT;
8. forged ethics-gate receipt -> REJECT;
9. silent state mutation -> REJECT;
10. replay of an ALLOW receipt against a different ActionContract -> REJECT.

All outcomes are exact.

The benchmark preserves negative results. A failure is not converted into a weaker threshold.

## Runtime constitutional coverage audit

The runtime audit does not rely on a hand-maintained list of public Hive entrypoints.

It parses the Python source tree and constructs an AST call graph. Candidate roots are discovered from:

- all `@mcp.tool()` functions;
- explicit actuator roots whose purpose is mutation or external actuation.

The graph is traversed transitively toward typed mutation sinks such as Hive append/state mutation, memory-exchange ingest, anti-entropy apply and backend mutation.

Coverage is path-sensitive. For every discovered root-to-sink path, the audit tracks whether a Constitutional guard was encountered before the sink.

A root is covered iff

\[
\boxed{
\forall p\in Paths(root,sink):
\exists g\in p\quad g\in ConstitutionalGuards.
}
\]

The coverage metric is

\[
\boxed{
C_{\rm runtime}
=
\frac{N_{\rm covered\ discovered\ roots}}
{N_{\rm auto-discovered\ high-consequence\ roots}}.
}
\]

\[
C_{\rm runtime}=1
\]

is required for the runtime-coverage verdict to be complete.

This removes the earlier arbitrary public-entrypoint registry. The remaining scope limitations are explicit: dynamic dispatch that cannot be resolved statically, native/non-Python actuators and semantic correctness of the evidence behind a gate remain separate proof obligations.

## Existing benchmark replay

The suite reuses existing benchmark implementations rather than rewriting historical results:

### Research orchestrator v0.2

Measures:

- routing precision;
- recall;
- exact-route rate;
- stage-exact rate;
- fan-out reduction;
- useful-task efficiency;
- plan latency.

Baseline:

- seven-specialist broadcast.

Existing preregistered thresholds are reused unchanged.

### OOD routing v0.6

Measures English paraphrases, Polish intents and ambiguity traps.

Existing thresholds are reused unchanged.

### Bestiary virtual topology v0.1

Compares deterministic Bestiary service topology with serial generalist service units.

This remains a synthetic topology benchmark, not a live hardware speedup claim.

### Geometry phase scheduler v0.1

Compares selected geometry-aware scheduling with FIFO proxy for:

- transition cost;
- noise;
- lexical overlap;
- topic purity;
- packed context bytes.

Existing synthetic verdict semantics are preserved.

### PhaseNav NumPy v0.1

Measures:

- scalar/vector equivalence;
- torus error;
- phase-kernel continuity candidates;
- measured scalar/vector speedup.

The equivalence threshold is inherited from the existing benchmark.

No new performance-promotion threshold is added.

## Latency lane

The suite measures same-process Python control-plane latency for:

- full constitutional admission;
- full typed capability validation;
- transition certification.

Reported metrics:

- median;
- p95;
- p99;
- mean;
- min;
- max.

These are measure-only in v0.1.

No arbitrary production SLO is inferred.

## Ledger scaling lane

Frozen batch sizes:

\[
1,\ 10,\ 100,\ 1000,\ 5000.
\]

For each size the suite builds content-addressed events and performs append-only join.

It records:

- total join time;
- nanoseconds per event;
- whether every event survives.

No throughput threshold is introduced in v0.1.

The benchmark is intended to expose scaling behavior before choosing an implementation-specific SLO.

## Aggregate verdict

The aggregate internal-readiness verdict is determined structurally:

### PASS_FULL_INTERNAL_SYSTEM_GATE

Requires simultaneously:

- constitutional invariants PASS;
- declared runtime constitutional coverage complete;
- existing semantic regression PASS.

### FAIL_RUNTIME_CONSTITUTIONAL_COVERAGE_GAP

Constitutional invariants and legacy semantics pass, but at least one declared high-consequence runtime surface still bypasses constitutional admission.

### FAIL_CONSTITUTIONAL_INVARIANT

Any exact non-bypass/fault-injection invariant fails.

### FAIL_EXISTING_BENCHMARK_REGRESSION

Constitutional invariants pass but existing semantic benchmark requirements regress.

Performance timings do not alter this logical verdict in v0.1.

## Reproducibility

Frozen seed:

\[
616.
\]

The suite writes a machine-readable JSON receipt:

\`provenance/GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1.json\`

with a SHA-256 content commitment.

The GitHub Actions artifact preserves the exact receipt generated by the exact reviewed head.

## Scope firewall

This suite does not claim:

- external model answer-quality superiority;
- external web-index superiority;
- enterprise production SLO certification;
- physical validation of GREMLIN dynamics;
- consciousness;
- biological equivalence;
- exhaustive proof that no undeclared runtime mutation path exists.

External answer-quality benchmarking remains a separate lane requiring a frozen public corpus, identical source/tool access where feasible, blinded scoring and explicit cost accounting.

## Implementation

Full suite:

\`benchmarks/gremlin_full_system_v01.py\`

Runtime coverage scanner:

\`tools/gremlin_runtime_coverage_audit_v01.py\`

Tests:

\`tests/test_gremlin_full_system_benchmark_v01.py\`


## Memory convergence and durable Hive lane

The suite measures exchange-memory anti-entropy using frozen content-addressed envelopes.

For each workload size the sender contains (N) envelopes and the receiver starts with exactly (lfloor N/2floor).

The exact invariants are:

[
oxed{
N_{m transferred}
=
N_{m sender}
-
N_{m receiver,initial}
}
]

and after delta application

[
oxed{
operatorname{divergentBuckets}(A,B)=arnothing.
}
]

The benchmark records inventory/manifest/plan/export cost, delta-apply cost and serialized delta/full-packet byte ratio. The byte ratio is descriptive only; no compression threshold is introduced.

A separate durable Hive lane writes frozen record counts to the SQLite WAL authority runtime, closes the process-resident handle, reopens the database and requires exact record recovery.

The exact durable-state requirement is

[
oxed{
N_{m recovered}=N_{m written}.
}
]

Write latency, full-table read latency and reopen/repair latency are measure-only.

## RAPHAEL governance lane

Two frozen lanes are executed repeatedly:

1. exact authorized mutation with passing post-audit;
2. deliberately malformed operation receipt after mutation begins.

Success requires:

- mutation status PASS;
- mutation authority expired after execution;
- no rollback on the valid lane.

Fault injection requires:

- OPERATION_RECEIPT_MISMATCH;
- status ROLLED_BACK;
- mutation authority expired;
- backend state restored exactly to the pre-mutation state.

Thus

[
oxed{
N_{m exact rollback}=N_{m injected bad receipts}
}
]

is an exact invariant, not a performance threshold.

Latency for both success and rollback is reported separately.

Implementation:

`benchmarks/gremlin_memory_governance_v01.py`
