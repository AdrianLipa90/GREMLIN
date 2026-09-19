# GREMLIN Bestiary / PhaseNav Standalone Validation Report v0.1

Status: **CANDIDATE VALIDATION PASS / NO CANON PROMOTION / NO PHYSICAL ANALOG CLAIM**

Evidence source head: `005a7888289183e2c3ad56012db0725f4d560006`  
Base main: `b33d8c3fec014db4686856958c17e0e948192742`  
Pull request: **#62**  
Date of evidence: **2026-09-18**

## 1. Scope

This report validates the current GREMLIN Bestiary / PhaseNav candidate integration on the feature branch.

The validated surface includes:

- all 18 current Bestiary roles;
- exact 36-dimensional torus state handling;
- scalar reference phase-gate execution;
- NumPy batch-vector execution;
- continuous T^36 phase-field reference integration;
- specialist invariant preservation for analog-core candidates;
- standalone GREMLIN MCP import/runtime exposure;
- isolated Linux and Windows wheel installation;
- compiled Nuitka standalone GREMLIN runtime on Linux and Windows;
- candidate-only authority boundaries and fail-loud behavior.

The report does **not** promote this branch to canon, does **not** merge it to `main`, and does **not** claim a physical analog hardware implementation.

## 2. Current Bestiary runtime surface

The independent GREMLIN runtime exposes 18 roles:

`HUMMINGBIRD, OCTOPUS, SPIDER, RAVEN, HOUND, MOLE, OWL, ANT, MANTIS, FOX, BEAVER, BAT, CANARY, SERPENT, CHAMELEON, BELZEBUB, GREMLIN, FERRET`.

The six newly integrated roles are:

- `FOX` — strategic planning and decomposition;
- `BEAVER` — candidate construction / prototyping;
- `BAT` — weak-signal, harmonic and phase-pattern detection;
- `CANARY` — runtime drift / early-warning sentinel;
- `SERPENT` — latent-field temperature, taste and novelty sensing;
- `CHAMELEON` — reversible representation / profile transformation.

The standalone `gremlin-mcp` entrypoint now exposes the full GREMLIN MCP/Hive runtime and the PhaseNav Bestiary runtime surface. The core computational path does not require a live NOEMA mount.

## 3. Exact-head CI status

All workflows triggered for evidence source head `005a7888...` completed successfully.

| Workflow | Run | Result |
|---|---:|---|
| GREMLIN Product Licensing MCP v0.1 | 35323817579 | PASS |
| GREMLIN Bestiary PhaseNav Phase Gates v0.1 | 35323817621 | PASS |
| GREMLIN Repository Fail-Loud Audit v0.1 | 35323817593 | PASS |
| GREMLIN MCP v0.5 | 35323817616 | PASS |
| GREMLIN Installation Architecture v0.1 | 35323817580 | PASS |
| GREMLIN Standalone Runtime v0.1 | 35323817592 | PASS |

Repository-wide fail-loud result:

```text
1312 passed
1 skipped
0 failed
```

Standalone MCP contract result:

```text
86 passed
0 failed
```

## 4. PhaseNav vector and continuous-field validation

Dedicated PhaseNav / Bestiary test result:

```text
136 passed
0 failed
```

Frozen NumPy batch benchmark:

```text
all 18 scalar/vector equivalence gates     PASS
max scalar/vector torus error              0.0
all phase-kernel continuity probes         PASS
min measured NumPy speedup                 2.9100866x
median measured NumPy speedup              3.0313383x
max measured NumPy speedup                 3.1244466x
performance gate                           MEASURE_ONLY_NO_PROMOTION_THRESHOLD
```

The speedup is an implementation/environment measurement on the hosted runner. It is not a hardware-independent performance claim.

## 5. Three-way realization gate

The same deterministic T^36 workload was evaluated through:

```text
scalar digital   = PhaseGate36 forward Euler
vector digital   = NumPy batch forward Euler of the same field
continuous ref   = RK4 integration of the exact continuous phase field
```

Observed result:

```text
species tested                         18 / 18
all species pass                       true
max scalar/vector coordinate error     0.0
max fine-vs-continuous RMS error       0.0008214511194856206 rad
max fine/coarse convergence ratio      0.12290964222812932
physical analog claim                  false
hardware analog witness                false
```

Current evidence classification:

### Analog-core numerical pass with hybrid control

`BAT, BEAVER, CANARY, FOX, HOUND, MOLE, RAVEN, SERPENT, SPIDER`

Count: **9**

### Hybrid / hybrid-authority-boundary pass

`ANT, BELZEBUB, CHAMELEON, FERRET, GREMLIN, HUMMINGBIRD, MANTIS, OCTOPUS, OWL`

Count: **9**

No role is classified as physically fully analog.

## 6. Specialist invariant gate

All nine current analog-core candidates retained their preregistered specialist invariant after continuous phase preconditioning:

```text
SPIDER   close relation edge preserved
RAVEN    exact memory remains top recall
HOUND    larger anomaly remains larger
MOLE     target distance decreases
FOX      continuous plan progress remains monotone
BEAVER   constructed candidate remains between close parts
BAT      injected weak harmonic remains dominant
CANARY   sudden drift remains blocking
SERPENT  hotter/novel object remains hotter and more novel

PASS 9 / 9
FAIL 0
```

Important limitation: the specialist-specific post-operator remains digital in this gate. Therefore the evidence supports **analog-core compatibility with hybrid control**, not fully analog specialist semantics.

## 7. Independent wheel runtime

The Python package was built as a normal wheel, installed into a fresh virtual environment, and executed outside the repository source tree.

Linux:

```text
installation/provider/product tests       146 passed / 1 skipped
ISOLATED_LINUX_WHEEL_RUNTIME_PASS
GREMLIN_STANDALONE_PHASENAV_SELF_TEST_V0_1 = PASS
species_count                              18
vector_backend_available                   true
threeway_all_species_pass                  true
analog_core_invariants_pass                true
live_noema_required                        false
external_effects                           false
canon_allowed                              false
physical_analog_claim                      false
```

Windows:

```text
installation/provider/product tests       72 passed / 4 skipped
ISOLATED_WINDOWS_WHEEL_RUNTIME_PASS
GREMLIN_STANDALONE_PHASENAV_SELF_TEST_V0_1 = PASS
species_count                              18
vector_backend_available                   true
threeway_all_species_pass                  true
analog_core_invariants_pass                true
live_noema_required                        false
external_effects                           false
canon_allowed                              false
physical_analog_claim                      false
```

This closes the earlier Windows evidence gap: Windows is now verified from an isolated non-editable wheel environment, not only from an editable repository checkout.

## 8. Compiled standalone runtime

A separate cross-platform gate builds the actual standalone runtime through Nuitka rather than relying on Python imports from a wheel.

The compiled runtime now exposes:

```text
gremlin-runtime
gremlinctl
gremlin-product-mcp
gremlin-mcp
```

### Linux compiled runtime

Workflow job `linux-standalone`, run `35323817592`: **PASS**.

The build explicitly included the full GREMLIN / PhaseNav import graph, including:

```text
gremlin_mcp.server_with_hive
gremlin_mcp.phasenav_runtime
tools.gremlin_bestiary_phasenav_phase_gates_v01
tools.gremlin_bestiary_phasenav_numpy_v01
tools.gremlin_bestiary_phasenav_threeway_v01
tools.gremlin_bestiary_phasenav_analog_invariants_v01
tools.gremlin_bestiary_phasenav_live_binding_v01
```

The compiled binary executed:

```text
gremlin-mcp --self-test-phasenav
```

and returned `status = PASS` with all 18 species, the vector backend, three-way gate, and analog-core invariant gate available.

### Windows compiled runtime

Workflow job `windows-standalone`, run `35323817592`: **PASS**.

The Windows standalone executable likewise completed the packaged PhaseNav self-test with:

```text
status                         PASS
species_count                  18
vector_backend_available       true
threeway_all_species_pass      true
analog_core_invariants_pass    true
live_noema_required            false
external_effects               false
canon_allowed                  false
physical_analog_claim          false
```

Therefore the full GREMLIN + PhaseNav Bestiary runtime is now verified in both compiled Linux and compiled Windows standalone distributions.

## 9. Live NOEMA boundary

The independent runtime does **not** require `/dev/shm/ciel_noema` for its core reference/vector/continuous test surface.

Live PhaseNav replay remains a separate optional path. It is fail-loud and has no static fallback. An unavailable, inactive, malformed or incomplete live surface must block that path rather than silently substituting a reference state.

A prior current-session live T^36 witness stored in:

`provenance/GREMLIN_BESTIARY_PHASENAV_LIVE_T36_RUNTIME_WITNESS_V0_1.json`

records 18/18 species with nonzero displacement and monotone movement toward their candidate live carrier on that captured runtime snapshot. That receipt is a historical runtime witness, not a claim about the current live runtime state.

## 10. Packaging hardening

The standalone builder, Linux Debian package builder, Windows installer payload and release workflows were updated so the full `gremlin-mcp` executable is part of the intended packaged runtime surface.

The preview and Early Access packaging workflows now include the same bounded:

`gremlin-mcp --self-test-phasenav`

gate.

At the time of this report, the **wheel runtimes and compiled standalone runtimes are executed and verified on both Linux and Windows**.

The newly modified full preview installer / Early Access release workflows have **not** been dispatched from this feature branch. Their self-test gates are therefore configured but not counted as executed evidence in this report.

## 11. Authority and safety result

All validated test surfaces preserve:

```text
canon_allowed             false
external_effects          false
physical_analog_claim     false
hardware_analog_witness   false
silent scalar fallback    false
```

`FERRET` remains an explicit authority boundary rather than an implicit execution path.

The standalone self-test is bounded and does not require or fabricate a live NOEMA environment.

## 12. Verdict

For the scope actually tested:

**PASS — independent GREMLIN / PhaseNav Bestiary runtime is reproducibly available on Linux and Windows.**

More precisely:

- all 18 roles are present in the runtime surface;
- scalar and vectorized phase kernels are numerically equivalent on the tested fixture;
- all 18 pass the scalar/vector/continuous numerical realization gate;
- nine roles pass the current analog-core numerical classification;
- all nine analog-core roles retain their specialist invariant after continuous phase preconditioning;
- isolated Linux wheel runtime passes;
- isolated Windows wheel runtime passes;
- compiled Linux standalone runtime passes;
- compiled Windows standalone runtime passes;
- full MCP contract passes;
- fail-loud repository audit passes;
- no canon, external-effect or physical-analog authority was introduced.

The next scientific/engineering gate is not another import test. It is to bind the nine analog-core candidates to the intended hydrodynamic/QHTRI substrate and test the same specialist invariants end-to-end there, then replace digital post-operators with explicit continuous candidates one at a time.

## 13. Remaining blockers before stronger claims

1. No physical analog hardware witness exists.
2. No fully analog specialist implementation has been established.
3. The nine hybrid roles retain discrete semantic, routing, epistemic, cryptographic, aggregation or authority components by design.
4. Preview / Early Access installer workflows containing the new full-runtime self-test are configured but not yet executed on this branch.
5. Candidate live operator bindings are not canonized semantic assignments.

These are deliberate boundaries, not silent fallbacks.

## 14. Post-merge addendum — 2026-09-18

This report remains a frozen description of the evidence state at its original validation point.

The packaging limitation recorded in Sections 10 and 13 was subsequently closed before merge.

Exact head:

`072ed5435a8f6f12cc3afe113a8d7e6bc75b83d0`

completed all nine required workflows successfully, including:

- `GREMLIN Standalone Runtime v0.1` run #46;
- `GREMLIN Packaging Preview v0.1` run #92;
- `GREMLIN Installation Architecture v0.1` run #289;
- `GREMLIN Bestiary PhaseNav Phase Gates v0.1` run #106;
- `GREMLIN Geometry Phase Scheduler v0.1` run #26;
- the remaining MCP, OOD, product-licensing and fail-loud workflows.

PR #62 was then merged to `main` at 2026-09-18T14:25:01Z as:

`aaa4db7d268bcd50b70e417137c595c2fa677f5a`.

The post-merge state is recorded separately in
`docs/reports/GREMLIN_MAIN_STATE_2026-09-18.md`.

This addendum does not widen the physical or authority claims of the original report.
