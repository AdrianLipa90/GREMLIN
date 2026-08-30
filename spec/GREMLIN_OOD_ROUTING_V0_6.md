# GREMLIN OOD Routing Hardening v0.6

Status: FEATURE-BRANCH CANDIDATE

Branch: `feat/gremlin-ood-routing-v0.6`

## Objective

Repair the OOD routing failure exposed after the frozen 12-case control-plane benchmark without giving up selective fan-out.

The failure modes addressed here are:

- trigger-swap / paraphrase recall loss;
- weak Polish intent coverage;
- raw-substring false additions such as `contest -> test -> HOUND`;
- punctuation-bound token misses such as `inconsistencies.`;
- divergence between research-planner triggers and the OCTOPUS router.

## Architecture change

The research planner no longer maintains a separate raw-substring trigger path.

```text
free-text query
  -> OCTOPUS Unicode-normalized semantic evidence
  -> absolute per-species evidence floor
  -> staged planner activation
  -> typed stage route
```

The baseline `ACQUIRE_EVIDENCE -> OWL` stage remains present. Optional stages are activated only when the query-level OCTOPUS route contains their specialist.

## Router v0.6

`gremlin_mcp.router` now uses:

- Unicode NFKD + casefold normalization;
- punctuation-stripping semantic tokenization;
- exact token matching for ordinary cues;
- explicit token-prefix matching for declared inflection/stem cues;
- token-sequence matching for phrases;
- weaker weights for ambiguous generic words;
- expanded English paraphrase cues;
- expanded Polish stems and phrases.

Prefix matching is never arbitrary substring matching. Therefore a token such as `contest` cannot satisfy the cue `test`.

Route commitments bind the v0.6 schema, semantic-profile identifier, thresholds, ranked scores and route mask.

## Planner unification

`build_research_plan_v02()` preserves its public entrypoint but advances to implementation version `0.2.1` and semantic profile `OCTOPUS_QUERY_EVIDENCE_V0_6`.

The planner records:

- query route commitment;
- query-level detected species;
- positive query routing evidence;
- typed stage commitments;
- final plan commitment.

A strong cue for one specialist cannot suppress an independently supported second specialist because query stage discovery uses the absolute evidence floor as the controlling threshold.

## OOD regression gate

`benchmarks/gremlin_ood_routing_v06.py` contains three explicit sets:

- 24 English trigger-swap/paraphrase cases;
- 12 Polish intent cases;
- 10 ambiguity traps.

Metrics include:

- specialist precision;
- specialist recall;
- F1;
- exact-route rate;
- omission rate;
- ambiguity false additions;
- selective fan-out reduction relative to six optional-specialist broadcast.

Required CI gates:

```text
precision >= 0.95
recall >= 0.95
exact route >= 0.90
omission rate <= 0.05
ambiguity false additions == 0
fan-out reduction >= 0.50
```

The frozen 12-case v0.2 benchmark is re-run in the same workflow and must retain precision=1, recall=1 and exact staged routing.

## Local pre-push regression result

The implementation was locally exercised against the new explicit regression set before repository write:

```text
24/24 English paraphrase cases exact
12/12 Polish intent cases exact
10/10 ambiguity traps clean
precision = 1.00
recall = 1.00
F1 = 1.00
omission rate = 0.00
ambiguity false additions = 0
selective fan-out reduction = 83.33%
```

This result is a development regression result for the committed explicit cases. It is not a hidden-test or external answer-quality result.

## Authority

The routing/planning layer remains candidate-only and preserves:

```text
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```
