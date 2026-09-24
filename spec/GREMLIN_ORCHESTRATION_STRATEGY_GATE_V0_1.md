# GREMLIN Orchestration Strategy Gate v0.1

Status: **CANDIDATE / NOT WIRED INTO PRODUCTION ROUTING**  
`canon_allowed=false`

## Purpose

Select the orchestration *mode* before GREMLIN's existing exact minimal-capability-cover planner selects concrete operators.

The gate does not replace `minimal_capability_cover`, the authority boundary, or the existing continuation/escalation rules.

## Candidate modes

- `DETERMINISTIC_MINIMAL_COVER` — known single-shot path, no runtime discovery requirement, low routing uncertainty.
- `BOUNDED_DYNAMIC_ORCHORBITAL` — open multi-turn work that explicitly requires runtime discovery.
- `HYBRID_GUARDED` — mixed or uncertain cases that should retain dynamic escape hatches without defaulting to unconstrained self-orchestration.

## External calibration

The public `orchestra-bench` project compares single, explicit DAG, self-orchestration and guarded hybrid strategies while holding model, tools, tasks and temperature fixed.

Its reported local pilot found explicit deterministic orchestration at least as successful as self-orchestration across three tested local models on known single-shot tasks. On the external tau2 retail validation, the ordering could flip: runtime self-orchestration was stronger on one Claude Haiku 4.5 slice and tied the single-agent strategy on Sonnet 4.5.

The same study reports an open-ended AWS case where an unguarded coordinator hit a six-delegation cap on every run, while the guarded hybrid stopped at two. That observation motivates the *candidate default* `delegation_cap=2`; it is not claimed to be a universal optimum.

Source: https://github.com/Himanshu-Sangshetti/orchestra-bench

## Firewall

This gate is a task-shape policy candidate, not a benchmark winner selector.

- It does not encode external success rates as GREMLIN scores.
- It does not claim deterministic routing is universally superior.
- It does not claim dynamic routing is universally superior.
- It keeps exact minimal capability cover mandatory for admitted work.
- Budget or authority failures remain fail-closed.
- Production executor wiring requires a separate validation gate.
