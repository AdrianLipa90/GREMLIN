# GREMLIN Continuous Prompt Benchmark v0.1

Status: IMPLEMENTED_CANDIDATE / OBSERVATIONAL_ONLY / NO_AUTHORITY

## Purpose

GREMLIN already contains reproducible offline benchmark and ablation suites.
This layer adds an append-only runtime ledger for prompts that actually cross
OCTOPUS/GREMLIN.

The target is continuous measurement rather than a one-time before-vs-after
benchmark.

## Scope

The v0.1 ledger records:

- prompt commitment, never raw prompt text;
- runtime generation where supplied;
- OCTOPUS route status, route mask, route commitment and bounded numeric scores;
- specialist or stage result commitments;
- validation status, corrections, retries and regressions;
- final outcome commitment and measured duration;
- explicitly executed ablation measurements.

Raw model outputs and raw specialist payloads are not persisted by this layer.

## Prompt visibility boundary

The runtime cannot benchmark a host prompt it never receives.

Therefore:

all GREMLIN-routed prompts can be observed
is not equivalent to
all ChatGPT host prompts being automatically visible.

Every direct call to OCTOPUS.route receives at least an implicit route-only span.

A host or NOEMA adapter can open prompt_benchmark_scope to bind multiple routes,
specialist stages, validation events and the final result to one prompt
lifecycle.

A future platform-level interceptor may use the same schema without changing
the ledger format.

## Non-interference rule

OCTOPUS computes its semantic route decision and route commitment before the
benchmark hook executes.

The benchmark therefore cannot alter score contributions, route threshold,
route mask, route commitment, worker authority, constitutional admission or
canon status.

Telemetry failure is observational. It may mark the benchmark DEGRADED and emit
a visible runtime warning, but it cannot silently rewrite routing output.

## Ledger integrity

The persistent JSONL ledger is a BLAKE2b-256 hash chain.

Every record binds a monotonically increasing sequence, previous record hash,
canonical event body and current record hash.

Replay verifies the complete chain.

If continuity or a record hash fails, the ledger becomes DEGRADED and refuses
further append until repaired. Historical corruption is never silently skipped.

## Runtime event model

The initial event vocabulary is:

PROMPT_OPEN
OCTOPUS_ROUTE
STAGE
VALIDATION
ABLATION
PROMPT_CLOSE

A complete trace is therefore one PROMPT_OPEN, followed by zero or more route,
stage, validation and ablation events, and finally PROMPT_CLOSE.

## Online metrics

The aggregate status reports only measured values:

- opened and closed prompt counts;
- known-success count and success rate;
- prompt duration;
- number of OCTOPUS routes;
- no-confident-route count;
- route fanout;
- validation pass rate;
- correction count;
- retry count;
- regression count;
- number of ablation observations;
- event counts by runtime generation.

Unknown quantities remain unknown. They are not imputed.

## Ablation semantics

An ablation receipt is valid evidence only for metrics explicitly supplied from
an executed comparison.

For each shared metric m the ledger stores:

delta(m) = m_ablated - m_baseline.

It does not simulate or infer the ablated result.

Examples of valid labels include WITHOUT_GREMLIN, WITHOUT_MEMORY,
WITHOUT_OCTOPUS, WITHOUT_PHASE_SCHEDULER and WITHOUT_SPECIES_HOUND.

The receipt also records whether the comparison used the exact same frozen task.

## Privacy

Policy in v0.1:

raw_prompt_persisted = false
raw_output_persisted = false
append_only = true
hash_chained = true
observational_only = true

This ledger is evidence about runtime behavior, not a second memory store for
conversation contents.

## Relationship to OWL runtime audit

OWL_RUNTIME_AUDIT_V0_1 remains the generic per-tool runtime evidence layer.

Continuous Prompt Benchmark v0.1 is complementary and records the per-prompt
orchestration lifecycle.

The two remain separately hash-chained so failure or migration of one does not
rewrite the other.

## Relationship to the existing full-system benchmark

GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1 remains the reproducible frozen internal
suite.

The continuous ledger does not replace it.

Frozen benchmark evidence is controlled regression evidence.
Continuous benchmark evidence is longitudinal real-work telemetry.

A strong performance claim should use both.

## Current limitation

v0.1 instruments OCTOPUS natively.

Complete host-wide automatic prompt lifecycle capture still requires a host or
NOEMA adapter to open and close prompt spans around every user turn. The current
NOEMA shared-memory surface exposes runtime state and routing contracts but not
a platform event containing every raw chat message.

This limitation must remain explicit.

## Implementation

gremlin_mcp/continuous_benchmark.py
gremlin_mcp/router.py
tests/test_continuous_prompt_benchmark_v01.py

No main-branch promotion is implied by this candidate implementation.
