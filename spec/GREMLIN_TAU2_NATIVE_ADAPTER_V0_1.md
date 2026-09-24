# GREMLIN τ² Native Receipt Adapter v0.1

Status: **ADAPTER HARDENED / NATIVE τ² EXECUTION NOT YET RUN**  
`canon_allowed=false`

## Upstream pin

Repository: `sierra-research/tau2-bench`  
Pinned commit: `b7ea9074c1cba482b30687fecdb5c8425fd6f619`  
Observed upstream commit date: 2026-09-17.

The pin is mandatory. A results file produced by another τ² commit fails closed unless the pin is deliberately changed and separately reviewed.

## Native scoring boundary

GREMLIN does not replace the τ² evaluator. It imports native `reward_info.reward` values after the pinned upstream evaluator has completed.

Version 0.1.2 mirrors the pinned upstream **agent metric semantics**:

[
\widehat{pass^k}=\frac{\binom{c}{k}}{\binom{n}{k}},
]

where `n` is the number of evaluated non-infrastructure trials for a task and `c` is the count of successful trials.

A reward is successful under the same pinned upstream tolerance:

[
1-10^{-6}\le r\le1+10^{-6}.
]

`infrastructure_error` simulations are excluded from τ²-compatible reward/pass metrics, matching `tau2.metrics.agent_metrics`. They remain preserved in raw diagnostics and termination counts.

## Trial integrity

For a benchmark run declaring `num_trials=k`, every task must contain exactly the trial identifiers:

`0,1,...,k-1`.

Missing, duplicated, shifted or non-contiguous trial IDs fail closed before aggregation.

## Important correction from adapter v0.1.0

The first adapter draft calculated an ordered-prefix diagnostic ("first k recorded trials all succeed") and labeled the aggregate like a pass-k metric. That is **not** τ²'s upstream `pass^k` definition.

v0.1.1 corrects this:

- official-compatible values are named `pass_hat_k`;
- ordered-prefix all-success remains available only as a per-task diagnostic;
- it is explicitly marked as **not** τ² `pass^k`;
- infrastructure-error filtering and success tolerance now match the pinned upstream implementation.

The earlier semantic mismatch is retained in benchmark provenance rather than silently overwritten.

## Comparison readiness

The receipt sets `comparison_ready=true` only when:

- no infrastructure errors occurred;
- the full declared `num_trials` remains available for `pass_hat_k`;
- every task remains represented in the evaluated set.

This is stricter than simply being importable. A run can be correctly imported while still being unsuitable for a clean competitor comparison.

## Provenance

The receipt binds:

- exact upstream τ² commit from native run metadata;
- expected agent model when supplied;
- expected trial count when supplied;
- optional GREMLIN commit SHA;
- SHA-256 for loaded result files;
- aggregate source digest;
- raw termination counts;
- the exact metric semantics used.

## Next gate

A legitimate GREMLIN τ² result still requires actual execution on the pinned upstream benchmark with identical model/configuration across comparison arms. This adapter only guarantees that native results are imported without changing the evaluator's semantics.


## Infrastructure placeholder compatibility

At the pinned upstream commit, `make_infra_failure_sim()` constructs an
`infrastructure_error` SimulationRun without `reward_info`. Adapter v0.1.2
therefore accepts a missing reward only for infrastructure-error placeholders,
preserves that trial in raw provenance, and excludes it from τ²-compatible
metrics. Missing reward information on any non-infrastructure simulation still
fails closed.

This behavior was added after direct inspection of
`src/tau2/runner/controller.py` at the pinned upstream commit.
