# GREMLIN Research Orchestrator Benchmark v0.2 Receipt

Status: `PASS`

This receipt preserves the v0.1 negative result and the v0.2 corrective result.

## v0.1 — FAIL

Workflow run: `33277938762`

Observed control-plane result:

- precision: `1.0`
- recall: `0.625`
- exact-route rate: `0.5`
- stage-exact rate: `1.0`
- average dispatched specialists: `1.6666666667`
- broadcast average: `7.0`
- fan-out reduction: `76.190476%`
- useful-task efficiency: `1.0` vs broadcast `0.38095238`

The preregistered quality gate failed because the benchmark compared the one-shot acquisition route against the specialist set required by the whole staged research plan. The failure also exposed a real planner gap: ANT/MANTIS did not have dedicated enumeration/pruning stages.

The v0.1 receipt is retained and is not rewritten as PASS.

## v0.2 — corrective architecture

Changes:

1. orchestration is evaluated as the union of species selected across the full staged plan;
2. every stage receives a typed specialist task plus a cryptographic query commitment rather than the full cross-contaminating query text;
3. added `MEMORY_CONTEXT -> RAVEN`;
4. added `ENUMERATE_VARIANTS -> ANT`;
5. added `PRUNE_REDUNDANCY -> MANTIS`;
6. quality thresholds were not relaxed.

Workflow run: `33278053935`

Exact head: `287a0f92a88817ff5944a348ff5cd4b4c250e796`

Observed v0.2 result across 12 frozen routing cases:

- precision: `1.0`
- recall: `1.0`
- F1: `1.0`
- exact-route rate: `1.0`
- stage-exact rate: `1.0`
- total dispatched specialists: `32`
- average dispatched specialists/query: `2.6666666667`
- seven-specialist broadcast total: `84`
- broadcast average/query: `7.0`
- fan-out reduction: `61.9047619%`
- useful-task efficiency: `1.0`
- broadcast useful-task efficiency: `0.38095238095`
- useful-task efficiency ratio: `2.625x`
- median GREMLIN full-plan control-plane latency: `471060 ns` (`0.47106 ms`)
- p95 plan latency: `1338292 ns` (`1.338292 ms`)
- p99 plan latency: `1362589 ns` (`1.362589 ms`)
- constant broadcast construction median: `141 ns`

Benchmark commitment:

`902626d0ea73ca3baba5c412e5f96b2a80fa9644ae8990a53b23da9fc883913b`

GitHub Actions artifact digest:

`sha256:535b0b81cfdc1313e09e1f7ba228ccecc6f1b2ac566fd9defdd9fff83a849bc3`

## Preregistered gates

All passed in v0.2:

- recall >= 0.95
- stage exact rate == 1.0
- fan-out reduction >= 0.35
- useful-task efficiency > broadcast
- exact-route rate >= 0.70

## Scope boundary

This benchmark is a deterministic GREMLIN control-plane benchmark against a seven-specialist broadcast baseline.

It is explicitly:

- not an actual Perplexity service benchmark;
- not a model answer-quality benchmark;
- not a web-index quality benchmark.

The next gate is external research-quality evaluation with frozen public questions, common source access where feasible, citation scoring, answer correctness, source diversity, tool/model-call counts, latency and cost.
