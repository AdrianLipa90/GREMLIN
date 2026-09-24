# GREMLIN τ-bench Native Receipt Adapter v0.1

Status: **ADAPTER READY / NATIVE τ-BENCH EXECUTION NOT YET RUN**  
`canon_allowed=false`

## Upstream pin

Repository: `sierra-research/tau2-bench`  
Pinned main commit: `b7ea9074c1cba482b30687fecdb5c8425fd6f619`  
Observed upstream commit date: 2026-09-17.

The pin is mandatory. A results file produced by another τ-bench commit fails closed unless the expected pin is explicitly changed and separately reviewed.

## Why importer-first

GREMLIN must not replace τ-bench's evaluator with a home-grown quality score.

The adapter therefore consumes native τ-bench `results.json` / directory-format simulation files after τ-bench has already evaluated trajectories. It reads:

- `info.git_commit`;
- agent/user implementation and model identifiers;
- domain and trial count;
- each `SimulationRun.task_id`, `trial`, `reward_info.reward`, `duration`, cost and termination reason.

GREMLIN does **not** reinterpret reference actions or reconstruct task correctness.

## Native scoring boundary

Current τ-bench evaluates policy-constrained tool interaction through its own environment/action/communication evaluators. Standard task `evaluation_criteria.actions` may be a reference trajectory used to derive target state and is not universally a required exact tool-call trace.

Accordingly, this adapter treats the native `reward_info.reward` as authoritative for τ-bench performance.

## Aggregates

For a run with `k` trials per task:

- `pass_1` = fraction of tasks whose first recorded trial has native reward 1.0;
- `pass_j` = fraction whose first j trials all have reward 1.0;
- `pass_k` = fraction passing every recorded trial.

It also records native mean reward, median/P95 duration, reported agent/user costs, termination-reason counts and per-task reward vectors.

No winner score or valuation multiplier is produced.

## Provenance

The receipt binds:

- exact τ-bench upstream commit from native run metadata;
- expected model identifier when supplied;
- expected number of trials when supplied;
- optional GREMLIN commit SHA;
- SHA-256 for the source results metadata and all loaded simulation files;
- aggregate source digest.

## Supported storage

- monolithic text `results.json`;
- directory-format `results.json + simulations/*.json`.

## Next execution gate

A legitimate GREMLIN τ-bench quality result requires:

1. checkout/install of the pinned τ-bench commit;
2. a registered GREMLIN candidate agent or externally callable adapter using the same foundation model as the reference arm;
3. identical domain/task split, user simulator, model configuration, seed policy and trial count;
4. native τ-bench execution and evaluation;
5. import through this adapter without reward rewriting.
