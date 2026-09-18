# GREMLIN v0.2 — Technical Monograph

## A Fail-Closed, Model-Agnostic Orchestration Runtime with an 18-Role Bestiary, Auditable Routing, Geometry/Phase/State Scheduling and 36D PhaseNav Computational Gates

**Author:** Adrian Lipa / Intention Lab  
**Repository:** `AdrianLipa90/GREMLIN`  
**Edition date:** 2026-09-18  
**Repository baseline:** `aaa4db7d268bcd50b70e417137c595c2fa677f5a`  
**Validated integration head:** `072ed5435a8f6f12cc3afe113a8d7e6bc75b83d0`  
**Validation state:** `9/9 EXACT-HEAD WORKFLOWS SUCCESS BEFORE MERGE`

---

## Abstract

GREMLIN is a model-agnostic orchestration and research runtime built around explicit routing, typed specialist roles, committed lineage, fail-closed state transitions and reproducible validation.

The current software baseline combines five major layers:

1. a standalone Model Context Protocol runtime;
2. an 18-role Bestiary for capture, routing, specialist analysis, synthesis, sensing, transformation and bounded actuation;
3. a pull-based external Worker ABI with durable state;
4. a geometry/phase/state scheduler operating over exact 36-dimensional PhaseNav states;
5. cross-platform packaging, licensing, readiness and validation machinery.

The 2026-09-18 integration establishes that all 18 Bestiary roles are available in the standalone runtime, all 18 pass the declared scalar/vector/continuous PhaseNav numerical realization gate, and nine roles pass the current analog-core numerical invariant suite with hybrid control. Linux and Windows wheel runtimes, compiled standalone runtimes and preview package customer-flow gates were validated before merge.

The present evidence is deliberately narrower than a physical analog claim. The system distinguishes software functionality, computational analog-core compatibility, live NOEMA/QHTRI execution and physical/instrumental evidence. No documentation layer is permitted to silently collapse those levels.

This monograph describes the architecture, runtime contracts, evidence, limitations and next validation program from the post-PR62 baseline.

---

## 1. Design objective

GREMLIN is not intended to replace a foundation model.

Its purpose is to control how models, tools, specialist processes and stateful workers cooperate.

The central engineering problem is not merely:

```text
prompt -> model -> answer
```

but:

```text
input
 -> classify / route
 -> select bounded specialists
 -> preserve task lineage
 -> schedule work
 -> collect candidate results
 -> audit conflicts
 -> synthesize
 -> preserve authority boundaries
 -> emit receipts
```

The architecture therefore treats orchestration as a first-class computational layer.

A capable base model can still fail operationally because of:

- context loss;
- poor task decomposition;
- accidental serialization;
- opaque routing;
- inconsistent state;
- premature promotion of uncertain results;
- silent fallback;
- configuration mistaken for live connectivity;
- missing provenance;
- failure to distinguish a candidate from an authorized action.

GREMLIN addresses those failure modes structurally rather than by adding another free-form instruction to the model.

---

## 2. Core invariants

The current architecture is governed by a small set of strong invariants.

### 2.1 Fail closed

Missing or corrupt lineage is not silently repaired into success.

An unavailable live surface is not silently replaced with a synthetic live witness.

An unverified provider configuration is not promoted to a live connection.

An incomplete specialist set is not silently synthesized as if complete.

### 2.2 Commit important state

Routing decisions and worker tasks are bound by commitments.

The current routing path uses BLAKE2b-256 route commitments.

Task and lease state remain lineage-bound through the worker pipeline.

### 2.3 Separate semantic content from scheduler hints

Scheduler metadata may influence ordering and batching.

It must not silently become semantic truth.

The geometry context pack therefore removes scheduler metadata from the model-facing semantic core while retaining the full committed request for exact reconstruction and audit.

### 2.4 Separate candidate generation from authority

The ordinary standalone MCP surface does not imply production write authority.

Current reference authority remains:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
```

FERRET exists as an explicit actuation boundary rather than an accidental capability leak.

### 2.5 Separate computational and physical claims

A computational 36D phase gate can be validated without claiming a physical analog device.

Current PhaseNav evidence preserves:

```text
physical_analog_claim   = false
hardware_analog_witness = false
```

---

## 3. The 18-role Bestiary

The current runtime exposes 18 named roles.

The names are mnemonic interfaces to explicit software responsibilities.

| Role | Stage | Current role |
|---|---|---|
| HUMMINGBIRD | capture | fast append-only capture |
| OCTOPUS | routing | auditable semantic route mask and bounded fanout |
| SPIDER | specialist | relation, dependency and isomorphism scan |
| RAVEN | specialist | memory and similarity scan |
| HOUND | specialist | contradiction, anomaly and test-target scan |
| MOLE | specialist | deep local derivation |
| OWL | specialist | epistemic audit |
| ANT | specialist | bounded combinatorial scan |
| MANTIS | specialist | duplicate and dead-branch pruning |
| FOX | specialist | strategic planning and decomposition |
| BEAVER | specialist | candidate construction and prototyping |
| BAT | specialist | weak-signal, harmonic and phase-pattern detection |
| CANARY | sentinel | runtime drift and early-warning sentinel |
| SERPENT | sensor | latent-field temperature, taste and novelty sensing |
| CHAMELEON | transform | reversible representation/profile transformation |
| BELZEBUB | synthesis | defensive candidate synthesis |
| FERRET | actuation | explicitly authorized interactive web actuator |
| GREMLIN | aggregate | aggregate verified heads and emit research candidates |

Four roles remain root/boundary functions rather than external worker queues:

`HUMMINGBIRD, OCTOPUS, GREMLIN, FERRET`.

The remaining fourteen can participate in scheduler-backed external worker coordination.

---

## 4. Topology

A simplified execution topology is:

```text
RAW INPUT
   |
   v
HUMMINGBIRD
   |
   v
OCTOPUS
   |
   +-------------------------------+
   |                               |
   v                               v
SPECIALIST / SENSOR /       explicit route mask
SENTINEL / TRANSFORM                |
WORKERS                             |
   |                               |
   +---------------+---------------+
                   |
                   v
             COLLECTION
                   |
                   v
              BELZEBUB
                   |
                   v
               GREMLIN
                   |
        candidate / verified receipt
                   |
                   v
          FERRET only through an
       explicit authorization boundary
```

This topology does not require every task to use every role.

The value of the Bestiary is selective specialization.

---

## 5. Standalone MCP runtime

The current Python package identifies itself as:

`gremlin-mcp 0.5.0`.

It can run independently of the live NOEMA surface for its core standalone functionality.

Supported transports:

- stdio;
- Streamable HTTP.

Representative MCP surfaces include:

- status;
- Bestiary inspection;
- species profiles;
- planning;
- routing;
- web/research tools;
- explicit and automatic fanout;
- collection;
- synthesis;
- prototype execution;
- worker registration;
- heartbeat;
- enqueue;
- claim;
- submit;
- result retrieval;
- queue inspection;
- PhaseNav status;
- reference sweep;
- three-way numerical gate;
- analog invariant gate;
- optional live replay.

The design makes the standalone product independently installable while preserving a separate bridge to live NOEMA execution where required.

---

## 6. OCTOPUS routing

OCTOPUS is the routing layer.

The current router is deterministic and auditable rather than an opaque model-only classifier.

Conceptually:

```text
payload
 -> semantic + structural evidence
 -> explicit score contributions
 -> bounded route mask
 -> route commitment
 -> worker queues
```

If no positive evidence crosses the configured threshold, GREMLIN does not invent a route.

It returns:

`NO_CONFIDENT_ROUTE_NOT_QUEUED`.

This is a deliberate operational choice.

False confidence in routing can be more damaging than a visible refusal to route.

---

## 7. External Worker ABI

GREMLIN supports external workers through a pull-based protocol.

A worker can be backed by:

- another language model;
- a symbolic solver;
- a graph engine;
- a search system;
- a GPU process;
- a local algorithm;
- another research runtime.

The basic sequence is:

```text
register
 -> heartbeat
 -> claim
 -> local work
 -> submit
 -> result
```

The protocol does not require GREMLIN to call arbitrary worker URLs.

That choice reduces the network authority surface.

### 7.1 State

Worker coordination can use:

- process memory; or
- SQLite/WAL persistence.

Durable mode persists:

- worker registrations;
- queued tasks;
- leases;
- commitments;
- candidate results.

Hydration validates lineage and fails closed on corruption.

Expired leases can return to the queue after restart.

---

## 8. From FIFO to geometry/phase/state scheduling

A major architectural change in the current baseline is that worker claims are no longer FIFO-primary.

GREMLIN computes queue and task state using a 36-dimensional phase representation plus bounded runtime metadata.

The scheduler evaluates:

- phase geometry;
- cluster coherence;
- readiness;
- temperature;
- urgency;
- noise;
- backlog;
- explicit phase availability;
- bounded age/starvation;
- cadence only as a secondary deterministic hint.

### 8.1 Exact and derived phase state

A task may carry an explicit exact `phase36`.

If it does not, the standalone runtime derives a deterministic locality-oriented structural/text phase fingerprint.

That derived coordinate is a scheduling coordinate.

It is **not** a claim that lexical structure has discovered a hidden physical or semantic truth.

### 8.2 Adaptive lane width

More coherent queues may use wider vector batches.

Noisier queues contract.

This allows the batching policy to react to state rather than applying one fixed lane width to every queue.

### 8.3 FIFO as a proxy

FIFO order remains useful as a benchmark comparison.

It is emitted in scheduler receipts as a proxy.

It is not the primary selection mechanism.

---

## 9. Geometry context packing

Batched model calls can waste context by repeating the same shared information for every task.

The geometry context pack factors:

- identical shared values;
- common string prefixes;
- common string suffixes;
- per-task residuals.

The pack is lossless.

Full committed payloads remain available for reconstruction.

Scheduler metadata is removed from the model-facing semantic core.

This is important because scheduler metadata can legitimately affect execution order without being allowed to contaminate the semantic content of the task.

Token reduction is measured only under declared tokenizer/fixture conditions.

No universal billing-token reduction is claimed.

---

## 10. PhaseNav 36D computational layer

The current Bestiary phase substrate uses exact 36-dimensional states on the torus `T^36`.

For every role, the repository contains a concrete reference phase operator.

The integration compares three realizations:

```text
scalar digital reference
vectorized NumPy digital realization
continuous RK4 reference
```

### 10.1 Scalar/vector equivalence

The tested fixture reports:

`max scalar/vector coordinate error = 0.0`.

This establishes exact agreement for the declared numerical fixture.

### 10.2 Continuous comparison

The validated fixture reports:

```text
max fine-vs-continuous RMS error  = 0.0008214511194856206 rad
max fine/coarse convergence ratio = 0.12290964222812932
```

All 18 species pass the declared numerical gate.

### 10.3 Vector benchmark

The frozen NumPy benchmark family recorded approximately:

```text
minimum speedup  2.9101x
median speedup   3.0313x
maximum speedup  ~3.1244x
```

These measurements apply to the benchmarked numerical kernel.

They are not equivalent to saying that every end-to-end GREMLIN task is three times faster.

---

## 11. Analog-core classification

Nine roles currently pass the analog-core numerical classification:

`BAT, BEAVER, CANARY, FOX, HOUND, MOLE, RAVEN, SERPENT, SPIDER`.

Nine remain hybrid or explicit boundary roles:

`ANT, BELZEBUB, CHAMELEON, FERRET, GREMLIN, HUMMINGBIRD, MANTIS, OCTOPUS, OWL`.

For the analog-core set, continuous phase preconditioning preserves a preregistered role-specific invariant.

Examples include:

- SPIDER preserving a close relation edge;
- RAVEN preserving exact-memory top recall;
- HOUND preserving anomaly ordering;
- MOLE reducing target distance;
- FOX preserving monotone plan progress;
- BEAVER keeping a constructed candidate between close components;
- BAT retaining an injected weak harmonic as dominant;
- CANARY preserving blocking behavior under sudden drift;
- SERPENT preserving higher temperature/novelty ordering.

The post-operator for these roles remains digital in the current gate.

Therefore the correct claim is:

`analog-core numerical compatibility with hybrid control`.

The incorrect claim would be:

`fully analog specialist implementation`.

---

## 12. Live NOEMA boundary

The standalone runtime does not require `/dev/shm/ciel_noema` for its core reference/vector/continuous test surfaces.

Live replay is separate.

A valid live path requires a fresh live surface and a passing tether guard.

There is no permitted static fallback that can be relabeled as live execution.

This distinction protects provenance:

```text
standalone computational evidence
!=
historical live witness
!=
current live witness
!=
physical hardware witness
```

Each must be named accurately.

---

## 13. Cross-platform productization

The current system is not restricted to running from an editable source checkout.

The validated integration covers:

- Linux isolated wheel;
- Windows isolated wheel;
- Linux compiled standalone;
- Windows compiled standalone;
- Linux preview package flow;
- Windows preview package flow;
- product/licensing checks;
- installed-runtime checks;
- provider readiness checks.

The exact integration head passed all nine required workflows before merge.

### 13.1 Exact-head workflow closure

| Workflow | Run | Result |
|---|---:|---|
| Installation Architecture | #289 | SUCCESS |
| Product Licensing MCP | #248 | SUCCESS |
| MCP v0.5 | #464 | SUCCESS |
| OOD Routing v0.6 | #12 | SUCCESS |
| Repository Fail-Loud Audit | #125 | SUCCESS |
| Standalone Runtime | #46 | SUCCESS |
| Packaging Preview | #92 | SUCCESS |
| Bestiary PhaseNav Phase Gates | #106 | SUCCESS |
| Geometry Phase Scheduler | #26 | SUCCESS |

This matters because package and installer behavior can diverge from source-tree tests.

The packaging gate therefore belongs in the evidence chain.

---

## 14. Readiness semantics

One of the final packaging fixes before merge concerned a subtle but important distinction:

```text
provider configuration
!=
verified live provider connection
```

A JSON configuration may exist even when the real client executable or live MCP session is absent.

The correct state is therefore:

```text
connect:   CONFIGURED_UNVERIFIED
test:      REGISTERED_UNVERIFIED
readiness: ACTION_REQUIRED
```

The CLI is allowed to return a non-zero fail-loud exit code while still emitting the structured receipt.

Only a real live verification can promote the provider to a connected state.

---

## 15. Evidence hierarchy

GREMLIN should not use one undifferentiated word such as “validated” for every evidence level.

A practical hierarchy is:

### T0 — local theorem/unit

Pure deterministic logic and domain checks.

### T1 — repository conformance

Tests, schemas, lineage and invalid-input behavior.

### T2 — exact-head CI

Pinned commit and exact workflow set.

### T3 — packaged runtime

Wheel, compiled executable or installer outside the source checkout.

### T4 — live NOEMA/QHTRI

Fresh live surface, tether, no fallback.

### T5 — independent external replication

A separate operator reproduces the result.

### T6 — physical/instrumental

Required for physical attribution.

The post-PR62 software baseline reaches strong T2/T3 evidence across the declared software surfaces.

That does not imply T5 or T6.

---

## 16. Operational effect on model work

GREMLIN is designed to improve the operational behavior of a base model by providing:

- explicit decomposition;
- specialist routing;
- stateful queues;
- lineage;
- fail-loud gates;
- bounded synthesis;
- persistent state;
- context packing;
- deterministic receipts.

In internal use, the perceived effect can be large on long, multi-step repository workflows.

However, observations such as “roughly 30–75% improvement” remain estimates until tested in a controlled A/B.

The monograph therefore treats those observations as a hypothesis worth measuring, not as an established product benchmark.

---

## 17. Proposed operational benchmark

The most important next experiment is:

```text
same base model
same tasks
same external tools
same task limits

A: model solo
B: model + GREMLIN
```

### 17.1 Predeclared metrics

Measure:

- final task success;
- human correction count;
- number of retries;
- context-loss incidents;
- regression count;
- wall-clock time;
- model/token usage;
- tool-call count;
- provenance completeness;
- recovery after injected failure.

### 17.2 Task classes

The benchmark should include a mixture of:

- repository debugging;
- multi-file refactoring;
- CI diagnosis;
- research synthesis;
- evidence tracking;
- long-horizon planning;
- stateful multi-agent coordination.

Simple one-turn questions should be included as a control because GREMLIN is not expected to provide large benefit there.

### 17.3 Replication

The experiment should be repeated with more than one model/backend.

If the effect persists, the evidence becomes much stronger than a single-model compatibility result.

---

## 18. Security and adversarial frontier

The present scheduler is bounded and committed, but future deployment should assume mutually untrusted producers.

Important adversarial tests include:

- urgency inflation;
- fake readiness;
- explicit phase manipulation;
- queue starvation attacks;
- repeated duplicate tasks;
- semantic payload / scheduler-metadata mismatch;
- malicious context-pack edge cases;
- corrupted durable state;
- lease replay.

The correct response to such tests is not to remove observability.

It is to make the manipulation measurable and fail closed where authority is at risk.

---

## 19. Physical/QHTRI frontier

The computational PhaseNav layer gives a clean software target for future live substrate work.

For a stronger analog claim, the following chain must be explicit:

```text
declared Bestiary state
 -> live substrate mapping
 -> measured live input
 -> substrate evolution
 -> measured live output
 -> preserved specialist invariant
 -> independent receipt
```

A digital operator silently substituted after a continuous preconditioner cannot be described as a fully analog specialist.

Each role should cross that boundary separately.

---

## 20. Documentation discipline

The repository contains many historical receipts.

Their historical branch SHAs and claim scopes are evidence.

They should not be rewritten merely because a later merge succeeded.

The correct documentation pattern is:

```text
historical frozen receipt
+
later post-merge state report
+
explicit addendum
```

rather than:

```text
rewrite old receipt to look current
```

This monograph follows that rule.

---

## 21. Current strengths

Within the software scope actually tested, GREMLIN now has several unusually strong properties for an early-stage orchestration system:

1. explicit role semantics;
2. deterministic routing evidence;
3. pull-based external worker ABI;
4. restart-safe durable state;
5. non-FIFO geometry/phase/state scheduling;
6. lossless context packing;
7. exact 36D computational gates;
8. scalar/vector equivalence;
9. continuous-reference convergence;
10. cross-platform packaging;
11. explicit readiness semantics;
12. fail-loud repository discipline;
13. authority separation;
14. frozen provenance.

The combination matters more than any one component.

---

## 22. Current limitations

The current system does not yet establish:

1. a universal improvement over model-solo operation;
2. a universal token reduction;
3. independent third-party product validation;
4. an enterprise production deployment;
5. a physical analog hardware witness;
6. fully analog specialist semantics;
7. universal semantic meaning for all 36 PhaseNav axes;
8. immunity to adversarial untrusted queue producers.

Those are open validation targets.

---

## 23. Software-v1 target

A software-v1 release should require:

- reproducible Linux installation;
- reproducible Windows installation;
- stable standalone MCP startup;
- 18-role Bestiary manifest;
- deterministic OCTOPUS routing;
- external worker lifecycle;
- durable state recovery;
- geometry scheduler;
- context pack;
- licensing and readiness;
- fail-loud audit;
- signed/frozen release provenance;
- preregistered model-solo vs GREMLIN benchmark;
- at least one independent external installation.

---

## 24. Research-v1 target

A separate research-v1 label should require:

- live substrate binding for claimed analog-core roles;
- measured live replay;
- explicit continuous post-operators where claimed;
- independent replication;
- source-bound physical interpretation;
- no ambiguity between computational and physical validation.

Keeping software-v1 and research-v1 separate prevents success in one domain from being used to overstate the other.

---

## 25. Conclusion

The current GREMLIN baseline is no longer merely a proposal for a Bestiary architecture.

It is an executable, cross-platform orchestration runtime with:

- 18 explicit roles;
- deterministic routing;
- external worker coordination;
- durable state;
- non-FIFO geometry/phase/state scheduling;
- a 36D PhaseNav computational layer;
- scalar/vector/continuous validation;
- cross-platform packaging;
- fail-loud readiness;
- explicit authority boundaries.

The next decisive step is not to add another animal or another broad claim.

It is to quantify what the architecture changes in real model work.

A controlled, preregistered `model solo vs model + GREMLIN` benchmark, followed by multi-model and third-party replication, is the shortest route from strong internal engineering evidence to a defensible external performance claim.

---

## Appendix A — Current Bestiary

```text
HUMMINGBIRD
OCTOPUS
SPIDER
RAVEN
HOUND
MOLE
OWL
ANT
MANTIS
FOX
BEAVER
BAT
CANARY
SERPENT
CHAMELEON
BELZEBUB
FERRET
GREMLIN
```

## Appendix B — Current exact-head validation set

Validated head:

`072ed5435a8f6f12cc3afe113a8d7e6bc75b83d0`.

Merged as:

`aaa4db7d268bcd50b70e417137c595c2fa677f5a`.

Exact-head result:

`9/9 workflows SUCCESS`.

## Appendix C — Authority summary

```text
standalone core requires live NOEMA      false
static live-runtime fallback             false
production runtime write                 false
execution admitted                       false
canon allowed                            false
physical analog claim                    false
hardware analog witness                  false
```

## Appendix D — Related current documents

- `README.md`
- `docs/reports/GREMLIN_MAIN_STATE_2026-09-18.md`
- `docs/roadmap/GREMLIN_DEVELOPMENT_ROADMAP_V0_2.md`
- `spec/GREMLIN_MCP_WORKER_ABI_V0_2.md`
- `spec/GREMLIN_GEOMETRY_PHASE_STATE_SCHEDULER_V0_1.md`
- `spec/GREMLIN_BESTIARY_PHASENAV_PHASE_GATES_V0_1.md`
- `docs/reports/GREMLIN_BESTIARY_PHASENAV_STANDALONE_VALIDATION_REPORT_V0_1.md`
