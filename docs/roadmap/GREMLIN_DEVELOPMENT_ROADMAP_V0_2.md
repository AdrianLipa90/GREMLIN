# GREMLIN Development Roadmap v0.2

**Date:** 2026-09-18  
**Repository:** `AdrianLipa90/GREMLIN`  
**Baseline main:** `aaa4db7d268bcd50b70e417137c595c2fa677f5a`  
**Status:** `WORKING_ROADMAP / POST-PR62 / EVIDENCE-FIRST / FAIL-CLOSED`  
**Canonical constant:** `kappa = ln(2)/(24*pi)`

## 1. Why v0.2 exists

Roadmap v0.1 captured the state of 2026-08-29, when the repository still described MCP v0.4 as the operational baseline, PR #22 as unfinished and several research lanes as future merge work.

That state is now historical.

As of 2026-09-18, GREMLIN has crossed a materially different engineering boundary:

- MCP v0.5 is on `main`;
- the Bestiary has 18 runtime roles;
- six newer roles — FOX, BEAVER, BAT, CANARY, SERPENT and CHAMELEON — are integrated into the standalone runtime;
- external workers use Worker ABI v0.2.1;
- worker claims are geometry/phase/state scheduled rather than FIFO-primary;
- an exact 36D PhaseNav computational layer is available for all 18 roles;
- the NumPy vector backend is validated against the scalar reference;
- a continuous RK4 reference gate is available;
- nine roles pass the current analog-core numerical invariant suite;
- Linux and Windows wheel runtimes pass;
- Linux and Windows compiled standalone runtimes pass;
- preview packaging and customer-flow readiness gates pass;
- PR #62 was merged only after 9/9 exact-head workflows succeeded.

Roadmap v0.2 therefore starts from a functioning software product surface rather than from the earlier infrastructure build-out.

## 2. Verified current baseline

### 2.1 Main

Current baseline:

`aaa4db7d268bcd50b70e417137c595c2fa677f5a`

This is the merge commit for PR #62:

`GREMLIN Bestiary PhaseNav phase gates v0.1`.

Validated source head:

`072ed5435a8f6f12cc3afe113a8d7e6bc75b83d0`.

Pre-merge base:

`b33d8c3fec014db4686856958c17e0e948192742`.

### 2.2 Exact-head CI closure

The validated head completed all required workflows successfully:

1. Installation Architecture;
2. Product Licensing MCP;
3. MCP v0.5;
4. OOD Routing v0.6;
5. Repository Fail-Loud Audit;
6. Standalone Runtime;
7. Packaging Preview;
8. Bestiary PhaseNav Phase Gates;
9. Geometry Phase Scheduler.

No merge was performed while any of those workflows was incomplete or red.

## 3. Current architecture

The present high-level flow is:

```text
input
 -> HUMMINGBIRD capture
 -> OCTOPUS auditable routing
 -> specialist / sentinel / sensor / transform workers
 -> candidate collection
 -> BELZEBUB defensive synthesis
 -> GREMLIN aggregation
 -> explicit FERRET actuation boundary when separately authorized
```

The current 18 roles are:

`HUMMINGBIRD, OCTOPUS, SPIDER, RAVEN, HOUND, MOLE, OWL, ANT, MANTIS, FOX, BEAVER, BAT, CANARY, SERPENT, CHAMELEON, BELZEBUB, FERRET, GREMLIN`.

Core-only boundaries:

`HUMMINGBIRD, OCTOPUS, GREMLIN, FERRET`.

All remaining roles may be scheduled as external worker species.

## 4. Current computational substrate

### 4.1 Standalone MCP

GREMLIN v0.5 supports:

- stdio;
- Streamable HTTP;
- deterministic OCTOPUS routing;
- BLAKE2b-256 route commitments;
- explicit no-evidence failure;
- Worker ABI v0.2.1;
- process-memory or SQLite/WAL worker state;
- same-species batching;
- standalone PhaseNav self-test;
- optional live NOEMA replay.

### 4.2 Geometry/phase/state scheduling

The current worker scheduler evaluates:

- phase-cluster coherence;
- readiness;
- temperature;
- urgency;
- noise;
- backlog;
- explicit phase availability;
- bounded starvation;
- cadence only as a secondary hint.

The selection law remains deterministic and receipt-bearing.

FIFO is retained only as a comparison proxy, not as the primary scheduling policy.

### 4.3 Context packing

`GREMLIN_GEOMETRY_CONTEXT_PACK_V0_1` factors shared semantic values and common text context while retaining full committed requests for lineage.

Scheduler metadata is excluded from the model-facing semantic core.

Any token-reduction claim must remain scoped to a named tokenizer and fixture. No universal billing-token claim is permitted from the current evidence.

## 5. Bestiary PhaseNav state

Every current role has an exact 36D computational phase state on `T^36`.

The validated three-way comparison is:

```text
scalar digital
vector digital
continuous RK4 reference
```

Current result:

```text
18/18 species pass
scalar/vector max coordinate error = 0.0
max fine-vs-continuous RMS error = 0.0008214511194856206 rad
max fine/coarse convergence ratio = 0.12290964222812932
```

The present evidence establishes computational compatibility, not physical analog realization.

## 6. Analog-core frontier

Current analog-core numerical candidates:

`BAT, BEAVER, CANARY, FOX, HOUND, MOLE, RAVEN, SERPENT, SPIDER`.

All nine preserve their specialist invariant under continuous phase preconditioning.

Current classification:

`ANALOG_CORE_HYBRID_CONTROL`.

This label is intentionally narrower than:

- fully analog specialist semantics;
- hardware realization;
- physical analog witness;
- universal analog superiority.

## 7. Product and packaging state

The product surface now includes:

- standalone `gremlin-mcp`;
- `gremlinctl`;
- product MCP;
- licensing/entitlement machinery;
- Linux packaging;
- Windows packaging;
- provider configuration;
- readiness diagnostics;
- cross-platform preview installer validation.

A configured JSON provider is not treated as a live connection.

The required fail-loud state is:

```text
CONFIGURED_UNVERIFIED
REGISTERED_UNVERIFIED
ACTION_REQUIRED
```

until a real client proves live MCP connectivity.

## 8. Authority model

GREMLIN remains explicit about software authority.

The standalone reference surface preserves:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
```

The PhaseNav validation surface additionally preserves:

```text
physical_analog_claim   = false
hardware_analog_witness = false
```

FERRET is an explicit actuation boundary. Its use requires a separate authorization path and must not be inferred from ordinary Bestiary execution.

## 9. Milestones already closed since v0.1

The following v0.1-era items are no longer future roadmap items:

### Closed A — MCP v0.5 / OCTOPUS routing

Deterministic route scoring, route commitments and fail-closed no-evidence handling are integrated.

### Closed B — 18-role Bestiary integration

FOX, BEAVER, BAT, CANARY, SERPENT and CHAMELEON are now first-class runtime roles.

### Closed C — worker scheduling upgrade

The scheduler is geometry/phase/state based rather than FIFO-primary.

### Closed D — vectorizable PhaseNav gate

The earlier v0.4 Bestiary vector roadmap called for a truly vectorizable PhaseNav kernel. That gate now exists and has been validated against the scalar reference.

### Closed E — Linux/Windows standalone validation

Both isolated wheel and compiled standalone surfaces pass.

### Closed F — preview packaging execution

The earlier standalone report recorded the preview installer self-test as configured but not executed. Exact-head Packaging Preview run #92 subsequently passed and closes that specific evidence gap.

## 10. Primary remaining engineering frontier

The next engineering work should optimize around evidence value rather than adding roles merely for breadth.

### 10.1 Operational A/B benchmark

The highest-value near-term experiment is:

```text
same model
same task set
same tool access
solo orchestration
vs
GREMLIN orchestration
```

Predeclare:

- tasks;
- pass/fail criteria;
- maximum allowed intervention;
- context window;
- model configuration;
- tool budget;
- retry policy.

Measure:

- task success;
- human correction count;
- regressions;
- context-loss incidents;
- wall-clock time;
- token/model use;
- tool calls;
- recovery after failure;
- provenance completeness.

The current informal estimate of material operational improvement must remain an estimate until this experiment is completed.

### 10.2 Multi-model replication

Repeat the operational benchmark across multiple independent model families/backends.

Goal:

distinguish a GREMLIN orchestration effect from compatibility with one particular base model.

### 10.3 Third-party deployment

A stronger external gate is reached when another operator can:

1. install GREMLIN from documented artifacts;
2. attach its own models/workers;
3. reproduce the declared runtime behavior;
4. run the A/B benchmark;
5. produce its own receipts without intervention from the author.

## 11. Primary remaining research frontier

### 11.1 Physical analog/QHTRI witness

For stronger analog claims, the nine analog-core candidates must be bound to the intended physical or quasi-physical substrate.

Required evidence:

- explicit hardware/runtime substrate;
- measured input state;
- measured output state;
- preserved specialist invariant;
- reproducible calibration;
- no hidden digital replacement of the claimed analog stage.

### 11.2 Continuous specialist operators

Where a role currently uses continuous phase preconditioning followed by a digital specialist operator, replace the digital post-operator one role at a time with a preregistered continuous candidate.

Each role receives its own validation gate.

### 11.3 Semantic-axis discipline

The 36 coordinates remain geometry/runtime coordinates unless an axis meaning is separately sourced and validated.

No documentation update may retroactively convert computational coordinates into physical or semantic facts.

## 12. Reliability frontier

### 12.1 Untrusted producer hardening

Scheduler metadata is committed and auditable, but mutually untrusted queue producers remain a future threat model.

Future hardening should test:

- adversarial urgency inflation;
- adversarial readiness claims;
- malicious explicit phase placement;
- starvation manipulation;
- queue poisoning;
- commitment-preserving semantic mismatch.

### 12.2 Recovery and restart tests

Expand crash/restart testing around:

- SQLite/WAL hydration;
- expired leases;
- partially written provider configuration;
- license/readiness interruption;
- concurrent worker restart;
- corrupted lineage.

## 13. Validation tiers

GREMLIN documentation should use explicit validation tiers.

### T0 — unit/theorem

Pure deterministic local checks.

### T1 — repository conformance

Tests, schemas, invalid-input rejection and lineage.

### T2 — exact-head CI

Pinned commit plus exact workflow set.

### T3 — packaged runtime

Wheel, standalone executable or installer executed outside source checkout.

### T4 — live NOEMA/QHTRI

Fresh live surface, tether guard and no static fallback.

### T5 — independent third party

External operator reproduces the result.

### T6 — physical/instrumental

Required for physical analog attribution.

A result must name the highest tier actually achieved.

## 14. Documentation policy

From v0.2 onward:

1. frozen provenance receipts remain immutable;
2. historical reports may receive clearly marked addenda but not silent claim rewrites;
3. new current-state reports pin exact main/PR SHAs;
4. benchmark claims name fixture, platform and scope;
5. estimates are labeled estimates;
6. physical claims require physical evidence;
7. provider configuration is never described as live connectivity without a live witness;
8. merge claims require exact-head verification.

## 15. Definition of GREMLIN software-v1 readiness

For the software product, v1 readiness should require all of the following:

- deterministic installation on Linux and Windows;
- standalone MCP startup;
- 18-role Bestiary manifest;
- OCTOPUS routing;
- external worker registration/lease/submit;
- geometry/phase/state scheduling;
- durable restart-safe state;
- explicit provider readiness;
- stable licensing/entitlement path;
- complete fail-loud audit;
- reproducible release artifacts;
- operational A/B benchmark with preregistered metrics;
- at least one independent external installation.

This is intentionally separate from physical-analog research readiness.

## 16. Definition of GREMLIN research-v1 readiness

The stronger research label additionally requires:

- end-to-end live PhaseNav/QHTRI replay for declared analog-core roles;
- explicit continuous specialist semantics where claimed;
- independent replication;
- source-bound physical interpretation;
- instrument/runtime receipts;
- no mismatch between documentation and executable authority.

## 17. Immediate execution order

1. Synchronize README, current-state report, roadmap and monograph with the post-PR62 baseline.
2. Preserve historical v0.1 reports and append only explicit post-merge notes where necessary.
3. Freeze a benchmark protocol for `model solo vs model + GREMLIN`.
4. Execute the benchmark on a representative task set.
5. Repeat on at least one additional model/backend.
6. Package an external replication kit.
7. Continue physical/QHTRI work separately from software-product claims.
8. Update the monograph again only when a new evidence tier is crossed.

## 18. Current roadmap verdict

GREMLIN is no longer in the stage described by v0.1 as “build the standalone Bestiary/MCP foundation”.

That foundation now exists.

The current problem is stronger and narrower:

**measure the orchestration advantage, reproduce it across independent environments, and keep software, analog-computational and physical claims cleanly separated.**
