# GREMLIN Main-State Report — 2026-09-18

**Repository:** `AdrianLipa90/GREMLIN`  
**Baseline branch:** `main`  
**Baseline merge commit:** `aaa4db7d268bcd50b70e417137c595c2fa677f5a`  
**Validated PR:** #62 — `GREMLIN Bestiary PhaseNav phase gates v0.1`  
**Validated PR head:** `072ed5435a8f6f12cc3afe113a8d7e6bc75b83d0`  
**Pre-merge base:** `b33d8c3fec014db4686856958c17e0e948192742`  
**Merged at:** 2026-09-18T14:25:01Z  
**Status:** `MERGED / 9-OF-9 EXACT-HEAD WORKFLOWS SUCCESS / MAIN IDENTICAL TO MERGE COMMIT`

## 1. Purpose

This report records the repository state after promotion of the validated 18-role Bestiary / PhaseNav / geometry-scheduler integration to `main`.

It is a post-merge state record. It does **not** rewrite or replace frozen historical receipts generated on feature heads. Those receipts retain their original branch names, SHAs, claim scopes and authority fields.

## 2. Current operational surface

The standalone GREMLIN MCP runtime exposes 18 Bestiary roles:

`HUMMINGBIRD, OCTOPUS, SPIDER, RAVEN, HOUND, MOLE, OWL, ANT, MANTIS, FOX, BEAVER, BAT, CANARY, SERPENT, CHAMELEON, BELZEBUB, FERRET, GREMLIN`.

Current role semantics from `gremlin_mcp/core.py`:

| Role | Stage | Current software role |
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
| FERRET | actuation | explicitly authorized interactive web actuator boundary |
| GREMLIN | aggregate | aggregate verified heads and emit research candidates |

The geometry/phase/state worker scheduler admits all roles except the GREMLIN-root boundaries:

`HUMMINGBIRD, OCTOPUS, GREMLIN, FERRET`.

## 3. Standalone MCP and worker architecture

Current standalone package version: `0.5.0`.

The runtime supports:

- stdio MCP transport;
- Streamable HTTP MCP transport;
- deterministic OCTOPUS routing with BLAKE2b-256 route commitments;
- positive-evidence auto-fanout with fail-closed `NO_CONFIDENT_ROUTE_NOT_QUEUED`;
- pull/lease/submit Worker ABI v0.2.1;
- same-species batching;
- process-memory or SQLite/WAL durable worker state;
- geometry/phase/state scheduling rather than FIFO-primary scheduling;
- lossless geometry context packs;
- standalone PhaseNav reference, vector and continuous conformance surfaces;
- optional live NOEMA replay with no static fallback.

## 4. PhaseNav Bestiary result

The Bestiary phase layer uses exact 36-dimensional states on `T^36`.

Validated numerical result:

```text
species tested                         18 / 18
all species pass                       true
max scalar/vector coordinate error     0.0
max fine-vs-continuous RMS error       0.0008214511194856206 rad
max fine/coarse convergence ratio      0.12290964222812932
physical analog claim                  false
hardware analog witness                false
```

The frozen NumPy benchmark recorded:

```text
minimum measured speedup    2.9100866102357243x
median measured speedup     3.03133825193712x
maximum measured speedup    3.1244466x (approx., frozen benchmark family)
```

The speedup is a benchmark result for the declared NumPy fixture and is not a universal end-to-end model-performance claim.

## 5. Analog-core numerical classification

Nine roles currently pass the analog-core numerical classification with hybrid control:

`BAT, BEAVER, CANARY, FOX, HOUND, MOLE, RAVEN, SERPENT, SPIDER`.

Nine roles remain hybrid or explicit authority-boundary roles:

`ANT, BELZEBUB, CHAMELEON, FERRET, GREMLIN, HUMMINGBIRD, MANTIS, OCTOPUS, OWL`.

All nine analog-core candidates retained their preregistered specialist invariant under continuous phase preconditioning.

This remains a computational/hybrid result:

- no physical analog hardware witness;
- no fully analog specialist implementation;
- no automatic promotion of semantic-axis meanings;
- no physical-analog claim.

## 6. Geometry phase scheduler

Worker claims are no longer FIFO-primary.

The scheduler uses:

- exact or derived 36D phase coordinates;
- phase-cluster coherence;
- readiness;
- temperature;
- urgency;
- noise;
- bounded starvation protection;
- adaptive vector lane width;
- deterministic cadence only as a secondary tie-break;
- committed scheduler receipts.

Explicit scheduler metadata is excluded from the model-facing semantic context pack while the full committed request remains present for lineage verification.

This separation is intentional: scheduler hints may affect queue ordering, but they do not silently rewrite the semantic payload seen by the worker.

## 7. Cross-platform packaging state

The exact PR head passed both isolated-wheel and compiled-standalone validation on Linux and Windows.

The previously open packaging evidence gap is now closed for the preview workflow.

Exact-head workflow results:

| Workflow | Run | Result |
|---|---:|---|
| GREMLIN Installation Architecture v0.1 | #289 | SUCCESS |
| GREMLIN Product Licensing MCP v0.1 | #248 | SUCCESS |
| GREMLIN MCP v0.5 | #464 | SUCCESS |
| GREMLIN OOD Routing v0.6 | #12 | SUCCESS |
| GREMLIN Repository Fail-Loud Audit v0.1 | #125 | SUCCESS |
| GREMLIN Standalone Runtime v0.1 | #46 | SUCCESS |
| GREMLIN Packaging Preview v0.1 | #92 | SUCCESS |
| GREMLIN Bestiary PhaseNav Phase Gates v0.1 | #106 | SUCCESS |
| GREMLIN Geometry Phase Scheduler v0.1 | #26 | SUCCESS |

Therefore the merge gate was **9/9 SUCCESS** on the exact head that was merged.

## 8. Provider readiness semantics

The preview customer-flow gate now distinguishes configuration from verified live connectivity.

For a JSON-configured provider without a proven live MCP session:

```text
connect status      CONFIGURED_UNVERIFIED
test status         REGISTERED_UNVERIFIED
readiness status    ACTION_REQUIRED
live claim          false
```

The CLI intentionally returns a fail-loud non-zero readiness/test code for the unverified state while still returning a structured receipt.

This prevents a configuration file from being misrepresented as a live connection.

## 9. Authority boundary

The standalone MCP reference authority remains fail-closed:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
physical_analog_claim    = false
hardware_analog_witness  = false
```

FERRET remains a separately authorized actuation boundary; its existence does not grant implicit external-effect authority to the Bestiary, scheduler or PhaseNav self-test surfaces.

## 10. What is now established

Within the tested software scope, the repository establishes:

1. an 18-role GREMLIN Bestiary available from the standalone runtime;
2. deterministic and auditable routing;
3. scheduler-backed external worker coordination;
4. exact 36D PhaseNav computational realization;
5. scalar/vector equivalence on the tested fixture;
6. continuous-reference convergence on the tested fixture;
7. analog-core numerical compatibility for nine roles;
8. Linux and Windows isolated-wheel operation;
9. Linux and Windows compiled standalone operation;
10. preview-package installation and customer-flow validation;
11. fail-loud readiness semantics;
12. repository-wide exact-head CI closure before merge.

## 11. What is not established

This report does not claim:

- a physical analog realization;
- a hardware QHTRI witness for the new Bestiary;
- universal model-quality improvement;
- a universal token-cost reduction;
- a production enterprise deployment;
- independent third-party scientific validation;
- that internal operational estimates such as a 30–75% workflow improvement are benchmark results.

Those are separate future evidence gates.

## 12. Next validation target

The next high-value validation is a preregistered operational A/B:

```text
same base model + same tasks
GPT/model solo
vs
same base model + GREMLIN
```

Recommended metrics:

- task success rate;
- human correction count;
- regression count;
- context-loss incidents;
- wall-clock completion time;
- model/token usage;
- tool-call count;
- provenance completeness;
- failure recovery rate.

This would convert current operational experience into a reproducible performance claim without overstating the existing evidence.
