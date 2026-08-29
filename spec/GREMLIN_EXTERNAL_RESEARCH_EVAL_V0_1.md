# GREMLIN External Research Eval v0.1

Status: `CANDIDATE_ONLY / EVALUATION_INFRASTRUCTURE`

Authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## Purpose

This layer creates a reproducible bridge between GREMLIN research orchestration and independent deep-research benchmarks. It deliberately separates:

1. internal control-plane routing benchmarks;
2. external retrieval/citation benchmarks;
3. external semantic answer grading;
4. long-form report quality;
5. misleading-evidence robustness.

An internal routing PASS is never promoted into an external answer-quality claim.

## Primary external benchmark: BrowseComp-Plus

Reference repository:

`https://github.com/texttron/BrowseComp-Plus`

BrowseComp-Plus evaluates deep-research systems over a fixed curated corpus of roughly 100K human-verified documents rather than live-web retrieval. Its public run contract includes at least:

```json
{
  "query_id": "...",
  "tool_call_counts": {"search": 0},
  "status": "completed",
  "retrieved_docids": ["..."],
  "result": [
    {"type": "output_text", "output": "..."}
  ]
}
```

GREMLIN v0.1 supports this run shape without vendoring benchmark questions, answers, qrels or corpus documents.

### Deterministic metrics implemented locally

- completion state;
- union of retrieved document IDs;
- retrieval precision/recall against caller-supplied relevance IDs;
- citation extraction from `[docid]` and `【docid】` forms;
- citation precision/recall against caller-supplied relevance IDs;
- per-tool and total tool-call counts;
- deterministic run and score commitments.

### Semantic answer correctness

GREMLIN does not create a substitute answer grader in v0.1.

```text
answer_correctness = null
answer_correctness_status = EXTERNAL_SEMANTIC_JUDGE_REQUIRED
```

This preserves comparability with the benchmark's external semantic judging procedure.

## Benchmark-data boundary

No BrowseComp-Plus benchmark data is committed into GREMLIN by this layer.

The external dataset/corpus remains separately acquired from its upstream sources. The adapter receives only the run-time query identifiers and relevance data explicitly supplied by the evaluator environment.

This boundary avoids:

- silently changing benchmark contents;
- leaking gold answers into GREMLIN source code;
- training/evaluation contamination through committed fixtures;
- licensing ambiguity around benchmark components.

Synthetic unit fixtures are clearly marked and never reported as external benchmark results.

## Run lifecycle

```text
EXTERNAL_QUERY
  -> GREMLIN staged planner
  -> retriever/search tool
  -> retrieved_docids ledger
  -> evidence analysis
  -> candidate answer with docid citations
  -> BrowseComp-Plus-compatible run JSON
  -> official/compatible external evaluator
  -> external score receipt
```

## Required provenance

A future real run must record:

```text
benchmark_name
benchmark_version/ref
query_id
corpus/index identity
retriever identity
GREMLIN commit
planner commitment
route commitments
retrieved_docids
tool_call_counts
answer output
elapsed time
provider/model identity if applicable
external evaluator identity
external evaluator output hash
```

## Cost and efficiency metrics

In addition to benchmark correctness, GREMLIN should record:

```text
search calls/query
fetch calls/query
retrieved docs/query
specialist tasks/query
model calls/query
tokens/query when available
wall-clock latency/query
provider cost/query when available
```

The strategic comparison is therefore not only answer pass rate, but a Pareto surface:

```text
correctness × evidence quality × robustness / cost × latency × fan-out
```

## Secondary external benchmark: DeepResearch Bench

Reference repository:

`https://github.com/Ayanami0730/deep_research_bench`

This benchmark is reserved for the next adapter because it evaluates long-form research reports and citation behavior rather than only short final answers. GREMLIN should not claim DeepResearch Bench compatibility until its output/report adapter and evaluator contract are implemented and tested.

## Robustness frontier: DRNOISE

Reference paper:

`arXiv:2607.17291`

DRNOISE tests paired clean/noisy research environments where a plausible conflicting document is added against corroborating indirect evidence chains.

This is the intended external robustness gate for:

```text
HOUND contradiction detection
SPIDER evidence-chain reconstruction
BELZEBUB synthesis discipline
provenance commitments
DUCL risk/capability lineage
```

At v0.1 the benchmark is recorded as `TARGET_IDENTIFIED / ADAPTER_NOT_IMPLEMENTED`. No score is claimed.

## Validation invariants

1. Synthetic fixtures cannot be labelled external benchmark results.
2. External answer accuracy remains unscored without the external semantic judge.
3. Gold answers are not embedded in GREMLIN source code.
4. Dataset/corpus identity must be recorded for real runs.
5. Tool-call counts must be non-negative and auditable.
6. Retrieved document IDs are deduplicated deterministically.
7. Citation metrics are computed independently from answer correctness.
8. Failed/incomplete runs remain failed/incomplete.
9. Internal control-plane PASS cannot satisfy an external-quality gate.
10. External scores require a receipt tying GREMLIN head, benchmark ref and evaluator identity together.
