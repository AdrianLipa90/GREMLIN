# GREMLIN Full System Benchmark & Ablation Suite v0.1

Status: IMPLEMENTED_CANDIDATE / OBSERVATIONAL_BENCHMARK / EXACT_INVARIANT_GATES

Date: 2026-09-20

Base runtime theorem merge head: `c2b7f44cd160bcdaf5e9ce13b8f7417afb598012`.

## Purpose

This suite provides one reproducible internal evaluation surface for GREMLIN.

It separates four result classes that cannot compensate one another:

1. constitutional invariants;
2. declared runtime constitutional coverage;
3. memory/governance invariants;
4. semantic/performance regression.

A routing speedup cannot compensate a constitutional gap.
A constitutional PASS cannot compensate memory loss.
Low latency cannot promote an inadmissible action.

## Exact constitutional ablation

The evaluated admission algebra is

\[
\sigma_G=
\min\{
\sigma_E,
\sigma_C,
\sigma_A,
\sigma_X,
\sigma_\Theta
\}.
\]

The five channels are ethics, capability, authority, evidence and parameter provenance.

The frozen matrix contains one all-PASS case and, for every channel, one BLOCK and one UNRESOLVED case.

Exact invariants:

\[
\boxed{\text{all-PASS}\Rightarrow ALLOW}
\]

and

\[
\boxed{\text{any non-PASS channel}\Rightarrow\text{decision}\neq ALLOW}.
\]

Each single-channel ablation must expose at least one false ALLOW relative to the complete conjunction. No fitted threshold is used.

## Fault injection

The frozen fail-closed matrix includes:

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

## Runtime constitutional coverage

The benchmark imports the same structural theorem implementation used by runtime non-bypass CI:

tools/gremlin_runtime_constitutional_proof_v01.py

The current explicit registry contains 26 declared mutation surfaces.

For every registered surface the theorem requires:

- the function exists;
- a constitutional_packet argument exists;
- exactly one unconditional top-level require_constitutional_admission call exists;
- the guard precedes the first declared mutation call;
- endpoint literal matches the registry;
- consequence class literal matches the registry;
- the guard consumes the function constitutional_packet;
- all declared mutation calls are present.

The internal runtime coverage lane passes only if

\[
\boxed{
C_{\rm declared}=
\frac{N_{\rm covered}}{N_{\rm declared}}=1.
}
\]

This is not yet a proof that the explicit registry is exhaustive over every arbitrary Python import/call path.

## Control-plane latency

The suite measures same-process Python latency for constitutional admission, typed capability validation, full request-bound runtime constitutional guard validation and transition certification.

Reported: median, p95, p99, mean, min and max.

These are measure-only in v0.1. No production SLO is inferred from this machine.

## Ledger scaling

Frozen batch sizes:

\[
1,\ 10,\ 100,\ 1000,\ 5000.
\]

Every content-addressed event must survive the append-only join. Latency and ns/event are descriptive.

## Memory anti-entropy convergence

For workload size N, the receiver begins with exactly floor(N/2) of the sender independent envelopes.

The exact missing-set invariant is

\[
\boxed{
N_{\rm transferred}
=
N_{\rm sender}-N_{\rm receiver,initial}.
}
\]

After application:

\[
\boxed{
\operatorname{divergentBuckets}(A,B)=\varnothing.
}
\]

The suite records inventory/manifest/plan/export latency, apply latency and serialized delta/full-packet byte ratio. No compression threshold is introduced.

## Durable Hive

Frozen record counts:

\[
10,\ 100,\ 500.
\]

The benchmark writes records to the SQLite WAL authority runtime, closes the handle, reopens the database and verifies

\[
\boxed{
N_{\rm recovered}=N_{\rm written}.
}
\]

Write, read and reopen/repair times are measure-only.

## RAPHAEL governance

Two repeated lanes are evaluated.

Valid lane: exact decree, external authorization, constitutional packet, live admission, reservation, mutation, post-audit and authority expiry.

Fault lane injects an invalid operation receipt after mutation begins.

Exact requirement:

\[
\boxed{
N_{\rm rollback}
=
N_{\rm injected\ bad\ operation\ receipts}.
}
\]

Every valid mutation must also expire mutation authority.

## FERRET actuation

FERRET is benchmarked with a deterministic injected executor and no external network access.

The lane requires exact preview, exact explicit authorization, request-bound constitutional packet, one successful execution and rejection of authorization replay.

Exact invariant:

\[
\boxed{
N_{\rm blocked\ replays}
=
N_{\rm executed\ authorizations}.
}
\]

Timing is measure-only.

## Existing benchmark replay

The suite reuses, rather than rewrites, existing benchmark implementations.

### Research orchestrator v0.2

Measures routing precision, recall, exact-route rate, stage-exact rate, fan-out reduction, useful-task efficiency and planning latency.

Baseline: seven-specialist broadcast. The deterministic fixture existing semantic correctness is treated as a regression invariant.

### OOD routing v0.6

The historical threshold gates remain in the raw receipt for provenance, but they do not control the new aggregate verdict.

The aggregate uses exact frozen-fixture facts: false positives = 0, false negatives = 0, exact route rate = 1 and ambiguity false additions = 0. Fan-out is compared only to the natural zero-reduction baseline.

### Bestiary virtual topology v0.1

Replays the deterministic Bestiary topology vs serial-generalist service model. The legacy 10x candidate threshold is report-only. Aggregate readiness uses only the natural baseline ratio: virtual speedup >= 1 means no worse than the serial reference model.

This remains synthetic and is not a live hardware claim.

### Geometry phase scheduler v0.1

The historical 20%/5%/20% verdict is retained only as legacy evidence. Aggregate readiness checks only the signs of the measured differences against FIFO: transition cost, noise cost, lexical overlap, topic purity and context packing must not be worse than baseline.

### PhaseNav NumPy v0.1

The historical 1e-12 scalar/vector tolerance is report-only. The measured maximum torus error is preserved, but it does not control readiness until an implementation-specific floating-point roundoff bound is derived. Measured speedup remains descriptive.

## Aggregate verdict

PASS_FULL_INTERNAL_SYSTEM_GATE requires simultaneously:

- constitutional exact invariants PASS;
- declared runtime constitutional coverage complete;
- memory/governance exact invariants PASS;
- existing semantic regression PASS.

Possible negative verdicts include FAIL_CONSTITUTIONAL_INVARIANT, FAIL_RUNTIME_CONSTITUTIONAL_COVERAGE_GAP, FAIL_MEMORY_OR_GOVERNANCE_INVARIANT and FAIL_EXISTING_BENCHMARK_REGRESSION.

Performance timing cannot alter these logical verdicts in v0.1.

## Reproducibility

Frozen seed:

\[
616.
\]

The receipt records Python version, implementation, OS/platform, machine architecture, processor string where available, CPU count, workload sizes, exact benchmark version and SHA-256 commitment of the complete receipt.

Machine-readable output:

provenance/GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1.json

## Scope firewall

This suite does not claim external LLM answer-quality superiority, external web-index superiority, enterprise production SLO certification, physical validation of GREMLIN dynamics, consciousness, biological equivalence or whole-repository mutation reachability exhaustiveness.

A future external comparative benchmark should use a frozen public corpus, equal tool/source access where feasible, blinded scoring, explicit token/time/cost accounting, preregistered metrics and preserved negative results.

## Implementation

Full suite: benchmarks/gremlin_full_system_v01.py

Memory/governance lanes: benchmarks/gremlin_memory_governance_v01.py

Tests: tests/test_gremlin_full_system_benchmark_v01.py

Runtime theorem reused unchanged: tools/gremlin_runtime_constitutional_proof_v01.py


## Benchmark gate provenance

Every aggregate readiness gate must declare one of the following provenances:

- EXACT_FROZEN_FIXTURE;
- EXACT_LABELED_FIXTURE;
- EXACT_NEGATIVE_FIXTURE;
- NATURAL_BASELINE_ZERO;
- NATURAL_BASELINE_RATIO_ONE.

Legacy empirical constants may remain visible in historical receipts but are tagged report-only and cannot change the aggregate verdict.

A floating-point tolerance is not promoted merely because it is conventional. It must be derived from the implementation and its numerical error model. Until that proof exists, the associated metric is measure-only.

This is the benchmark analogue of the Constitutional parameter rule: theorem, measurement or explicit policy; no silent magic number.
