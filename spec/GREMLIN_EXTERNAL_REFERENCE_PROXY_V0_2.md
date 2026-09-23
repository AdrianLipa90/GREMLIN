# GREMLIN External Reference Proxy v0.2

Status: **CANDIDATE / SYNTHETIC REFERENCE PROXY**  
\`canon_allowed=false\`

## Purpose

This pre-gate maps published external agent stress regimes onto previously measured GREMLIN control-plane behavior. It is deliberately **not** a head-to-head competitor benchmark and does not predict answer quality.

## External calibration

1. **LangChain multi-agent benchmark** — same \`gpt-4o\` model, first 100 modified tau-bench retail examples, up to six irrelevant domains, each with 19 tools. Their single-agent baseline falls sharply once two or more distractor domains are present; swarm/supervisor token cost remains flatter as distractors grow.
2. **tau-bench reliability** — the original retail analysis reports GPT-4o function-calling pass^1 around 65.2% on the analysed retail set and pass^8 below 25%, implying at least ~61.7% loss of reliability retention across eight semantically equivalent reruns.
3. **Google ADK 2.0 illustrative workflow** — 5,152 -> 2,265 tokens and 7.2 -> 5.7 s, corresponding to 56.04% token and 20.83% latency reduction. Google explicitly labels this illustrative.
4. **GREMLIN SGT live A/B** — measured anchor points at 110, 550 and 1100 sentences: -17.262%, +31.665% and +65.89% context reduction; dispatch fan-out 4 -> 2.

## Synthetic mapping

For the proxy only, one domain contributes 110 sentence-units. This is an explicit modeling assumption chosen so domain growth can be placed on the already measured SGT axis. We do not claim real tau-bench domains contain 110 sentences.

| Total domains | Distractors | Synthetic sentences | SGT interpolated context delta | Gate | External sharp-drop regime |
|---:|---:|---:|---:|---|---|
| 1 | 0 | 110 | -17.262% | BYPASS | no |
| 2 | 1 | 220 | -5.030% | BYPASS | no |
| 3 | 2 | 330 | +7.201% | USE_SGT | yes |
| 4 | 3 | 440 | +19.433% | USE_SGT | yes |
| 7 | 6 | 770 | +45.355% | USE_SGT | yes |

The first threshold alignment occurs at **3 total domains / 330 synthetic sentences**. The SGT break-even (~265 sentences) was derived before adding the LangChain same-model stress observation, so this is a useful hypothesis rather than a fitted threshold.

At seven total domains, six distractor environments expose 114 irrelevant tools under the published 19-tools-per-distractor setup. A perfect selective router would structurally avoid those irrelevant tool exposures. This proxy does **not** assume perfect GREMLIN task routing on tau-bench; it reports the structural opportunity only.

## Reliability implication

The tau-bench pass^k result makes a single-run correctness benchmark insufficient. The next real GREMLIN comparison must report pass^1 and pass^k, not only average success.

## Claim boundary

Allowed:
- fixture-specific crossover hypothesis;
- structural domain/tool exposure statistics;
- interpolation between measured GREMLIN anchor points;
- external published stress/reliability facts with provenance.

Not allowed:
- GREMLIN quality score inferred from competitor results;
- claim that GREMLIN beats LangGraph, AutoGen, ADK, Magentic-One or OpenAI Agents SDK;
- extrapolation of SGT compression beyond its largest measured anchor;
- treating ideal selective-domain avoidance as measured production savings.

## Next gate: v0.3 real same-model A/B

Run one identical foundation model in: (A) monolithic all-tools context, (B) supervisor/swarm reference architecture, and (C) GREMLIN selective-cone. Freeze tasks, policy text, tools, temperature, retry/network budget and source corpus. Measure final-state correctness, pass^1, pass^k, tokens, model/tool calls, median/P95 latency, cost, failure recovery and provenance integrity.
