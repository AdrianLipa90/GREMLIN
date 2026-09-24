# GREMLIN External Same-Model A/B Protocol v0.3

Status: **FROZEN CANDIDATE HARNESS**  
\`canon_allowed=false\`

## Goal

Measure architecture effects while holding the foundation model fixed. This protocol compares three arms:

- \`MONOLITHIC_ALL_CONTEXT\` — one model sees every domain instruction and tool.
- \`SUPERVISOR_SAME_MODEL\` — the same model performs routing and then the same model family executes the selected sub-agent task.
- \`GREMLIN_SELECTIVE_CONE\` — GREMLIN performs the control-plane selection; the same foundation model receives only the admitted relevant context/tool surface.

No arm may use a stronger model, different temperature, larger retry budget, different source corpus or network access.

## Frozen workload

The original synthetic suite contains six policy/tool-use tasks across retail, calendar and support. Every base task is repeated at 1, 3 and 7 total domains, producing 18 workload variants. For the distractor conditions, each irrelevant domain contributes 19 irrelevant tool slots, matching the scale used in the published LangChain same-model multi-agent stress setup.

Each workload variant runs eight trials. This is deliberate: tau-bench showed that single-run success can materially overstate repeated reliability, so v0.3 reports both \`pass^1\` and \`pass^8\`-style reliability.

## Common execution configuration

- temperature: 0.0
- network: OFF
- retry budget: 0
- max output tokens: 1024
- same exact model identifier in every receipt

A different model identifier or common-config mismatch is a hard scorer error.

## Task scoring

A trial passes only if all of the following hold:

1. runtime status is \`COMPLETED\`;
2. final structured state exactly equals the frozen expected state;
3. every required tool appears in the tool trace;
4. no forbidden tool appears in the tool trace.

Thus a plausible natural-language answer is insufficient if the state mutation or tool trajectory is wrong.

## Metrics per arm

- \`pass^1\` — first-trial exact pass rate across all 18 workload variants;
- \`pass^k\` — fraction of workload variants passing **all eight** trials;
- mean trial pass rate;
- mean prompt/completion/total tokens;
- mean model calls and tool calls;
- median and P95 wall-clock latency.

The scorer intentionally does **not** calculate a winner, composite score or valuation multiplier.

## Claim firewall

The frozen task suite and scorer may be published before model execution. A model-quality claim requires actual run receipts. Mock receipts, unit tests and synthetic reference proxies prove only the harness.

The current session does not expose three independent inference endpoints, so no v0.3 model result is fabricated. The remaining execution dependency is one model endpoint callable under the exact same identifier/configuration for all three arms.

## External methodological anchors

- LangChain same-model multi-agent architecture benchmark: GPT-4o, modified tau-bench retail, first 100 tasks, irrelevant domains with 19 tools each.
- Sierra tau-bench: objective final-state evaluation and \`pass^k\` reliability.
- OpenAI agent-eval guidance: repeated datasets, trace/tool evaluation and end-to-end workflow grading.

These sources motivate protocol structure; their scores are not copied into GREMLIN's result.
