# GREMLIN External Orchestration Landscape / Quasi-Benchmark v0.1

Status: **CANDIDATE / EXTERNAL RESEARCH**  
Branch target: `feat/semantic-graph-transformer-v01-20260923`  
`canon_allowed=false`

## Purpose

This first pass converts public benchmark observations into a typed evidence graph for GREMLIN. It deliberately does **not** make an overall "GREMLIN beats X" claim. Different sources use different models, tools, tasks, retry budgets, environments and scoring rules.

The graph separates four surfaces:

1. `TASK_QUALITY` — task completion / accuracy on external benchmark datasets.
2. `ORCHESTRATION_EFFICIENCY` — context, token, fan-out and latency overhead.
3. `CONTEXT_STRESS` — degradation as irrelevant tools/domains/context grow.
4. `RECOVERY_CONTROL` — behavior under injected failures, state and retry loops.

## External observations

### Microsoft Magentic-One / AutoGen

Microsoft reports Magentic-One at 38.0% task completion on GAIA, 27.7% accuracy on AssistantBench and 32.8% task completion on WebArena. These are genuine agent-task metrics, but they are not directly comparable to GREMLIN's current internal routing benchmarks because the tasks, model stack and environment differ.

Source: https://www.microsoft.com/en-us/research/wp-content/uploads/2024/11/Magentic-One.pdf

### LangGraph / LangChain context stress

LangChain's ReAct study ran 30 tasks per domain, three repeats per task (90 runs per domain). It reports that adding irrelevant domains and tools generally degrades agent performance. In the calendar task, gpt-4o fell to 2% at seven domains. Control-agent scores included 71% for o1 and 68% for o3-mini on calendar scheduling; customer-support control scores included 83% Claude 3.5 Sonnet, 77% o1 and 83% o3-mini.

This supports a GREMLIN design hypothesis: routing only the relevant capability cone can matter even when the foundation model is unchanged.

Source: https://www.langchain.com/blog/react-agent-benchmarking

### Google ADK 2.0 illustrative efficiency example

Google's ADK 2.0 post gives an explicitly **illustrative** workflow using Gemini 3.5 Flash and mock API responses:

- vanilla LLM agent: 5,152 tokens / 7.2 s;
- deterministic ADK workflow: 2,265 tokens / 5.7 s.

Derived reductions are 56.04% in token usage and 20.83% in latency. These are vendor illustrative results, not an independent production benchmark.

Source: https://developers.googleblog.com/why-we-built-adk-20/

### AIMultiple 2026 independent web benchmark

AIMultiple reports 2,000 runs across five tasks. In its unstructured-data Task 5:

- AutoGen: 8,170 prompt tokens, 47 s median;
- LangGraph: 9,150 tokens, 70 s median;
- LangChain: 10,070 tokens, 86 s median.

Normalized to AutoGen for that one task, LangGraph is 1.12x tokens / 1.49x latency and LangChain is 1.23x tokens / 1.83x latency. These ratios are source-specific and must not be generalized to other workloads.

Source: https://aimultiple.com/agentic-frameworks

### OpenAI Agents SDK

OpenAI's public evaluation guidance emphasizes trace grading, exact tool/handoff behavior, datasets and repeated eval runs. No directly comparable public framework-overhead number is used in v0.1; absence of a number is retained as absence rather than estimated.

Source: https://developers.openai.com/api/docs/guides/agent-evals

## GREMLIN measurements inserted into the same graph

Current SGT live A/B:

| Sentences | Context reduction | Routing latency reduction | Dispatch reduction |
|---:|---:|---:|---:|
| 110 | -17.262% | 8.886% | 50% |
| 550 | 31.665% | 14.732% | 50% |
| 1100 | 65.890% | 5.035% | 50% |

A first fixture-specific linear interpolation puts the context break-even near **265 sentences**. This is a routing threshold hypothesis, not a universal constant.

For the two larger fixtures, mean context reduction is **48.78%**. Across all three sizes, mean measured route-latency reduction is **9.55%**, while dispatch fan-out reduction is **50%** in every tested case.

## Interpretation boundary

The public evidence already supports the *problem statement* GREMLIN targets:

- irrelevant context/tools can reduce task success;
- orchestration architecture changes token and latency overhead;
- recovery behavior differs across state/conversation/managerial execution loops;
- deterministic or selective workflow structure can reduce unnecessary model work.

It does **not yet** establish that GREMLIN has better end-to-end answer quality, cost, or reliability than LangGraph, AutoGen, CrewAI, Google ADK or OpenAI Agents SDK.

## Next gate

`GREMLIN_EXTERNAL_SAME_MODEL_AB_V0_2` should freeze:

- one public task suite;
- the same foundation model and temperature;
- identical tools and source corpus;
- identical retry/network budgets;
- task success/correctness;
- exact tool trajectory where appropriate;
- prompt/completion tokens;
- model calls and tool calls;
- median/P95 wall-clock latency;
- cost;
- injected-failure recovery;
- at least three repeats per stochastic task, with larger samples for latency distributions.

Only that experiment can support a head-to-head product claim.
