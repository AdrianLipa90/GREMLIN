# GREMLIN External Evidence Registry v0.2

Status: **CANDIDATE / EXTERNAL RESEARCH**  
`canon_allowed=false`

This registry strengthens the external reference surface without merging unlike metrics into a leaderboard.

## Evidence classes

- **A_RESEARCH_PREPRINT_OPEN_CODE** — primary research artifact with explicit protocol and public implementation.
- **A_PRIMARY_BENCHMARK** — benchmark owner / canonical benchmark repository.
- **B_VENDOR_REPRODUCIBLE_SYSTEMS** — vendor-authored result with an open reproducible systems harness.
- **C_INDEPENDENT_WEB_BENCHMARK** — independent repeated benchmark with stated model, hardware and protocol.

## New calibration surfaces

### Same-model framework overhead

Agent Harness reports CrewAI, LangGraph and AutoGen on identical AWS m6i.4xlarge hardware, GPT-4o via Azure OpenAI, temperature 0, with 50 runs per task suite. For its research-synthesis workload:

| Framework | Median | P95 | Cost / 1000 | token overhead |
|---|---:|---:|---:|---:|
| LangGraph | 14.1 s | 19.8 s | $41.70 | +9% |
| CrewAI | 18.4 s | 31.2 s | $48.20 | +18% |
| AutoGen | 22.7 s | 41.5 s | $67.40 | +31% |

Derived ratios are normalized only inside this one experiment.

### Pure orchestration overhead

Swarms GraphWorkflow publishes a no-op-node systems harness against LangGraph 1.0.4. The no-op design isolates orchestration cost from model latency. Reported headline values include 7.0x geometric-mean steady-state speedup, 62.5x for a 200-node chain (0.29 ms vs 18.15 ms), 2.7x–4x for shallow wide graphs, 21.6x–31.3x compilation speedup and 7.9x cold-path speedup.

These values define an external systems envelope. GREMLIN is **not** assigned any value on this axis until `GREMLIN_ORCHORBITAL_SYSTEMS_OVERHEAD_V0_1` is actually executed.

### Fixed-model harness effect

The 2026 *Beyond Prompts* preprint evaluates harness optimization around a fixed inner model with held-out scorecards. PRISM-MW reports mean held-out lifts of 14.2 pp on BFCL multi-round, 14.9 pp on tau2-Retail and 10.1 pp on tau2-Telecom. Their unweighted descriptive mean is 13.07 pp.

This is external evidence that the runtime harness around fixed model weights can materially affect held-out task performance. It is not evidence that GREMLIN has the same lift.

### tau benchmark lineage

The current tau benchmark repository uses policy-constrained tool tasks and environment-based scoring. Version/task pins must be recorded because task fixes can make older and newer results non-comparable.

## Firewall

No cross-source composite score is allowed. In particular:

- GREMLIN context reduction is not token-overhead percentage.
- no-op framework overhead is not model task latency.
- held-out percentage-point lift is not a framework speedup.
- vendor reproducibility does not equal independent validation.
- no GREMLIN answer-quality claim exists until real same-model receipts are executed.
