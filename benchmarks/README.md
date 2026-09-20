# GREMLIN Benchmarks

## Research orchestration

- `gremlin_research_orchestrator_v01.py` — preserved initial selective-route benchmark; preregistered quality gate failed.
- `gremlin_research_orchestrator_v02.py` — full staged-plan species-union benchmark after correcting the measurement level and adding explicit RAVEN/ANT/MANTIS stages.
- Provenance: `provenance/GREMLIN_RESEARCH_ORCHESTRATOR_BENCHMARK_V0_2.md`.

The benchmark is a GREMLIN control-plane comparison against a seven-specialist broadcast baseline. It is not an external service or answer-quality comparison.


## Full system benchmark v0.1

The unified internal benchmark is implemented in:

- `benchmarks/gremlin_full_system_v01.py`
- `benchmarks/gremlin_memory_governance_v01.py`
- methodology: `spec/GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1.md`

It keeps four verdict classes independent:

1. constitutional exact invariants;
2. declared runtime constitutional coverage;
3. memory/governance exact invariants;
4. semantic/performance regression.

The suite reuses the exact runtime non-bypass theorem instead of maintaining a second coverage definition. It also replays the existing research-orchestrator, OOD-routing, Bestiary virtual-topology, geometry-scheduler and PhaseNav scalar/vector benchmarks.

New exact lanes include constitutional ablation/fault injection, Hive anti-entropy convergence, durable SQLite/WAL recovery, RAPHAEL rollback governance and FERRET single-use actuation.

New latency/scaling measurements are measure-only. They do not receive arbitrary promotion thresholds. Negative logical or regression findings are preserved in the machine-readable receipt rather than compensated by speed.

The generated receipt is:

`provenance/GREMLIN_FULL_SYSTEM_BENCHMARK_V0_1.json`

The suite is an internal architecture benchmark. It does not claim external LLM answer-quality superiority or production SLO certification.
