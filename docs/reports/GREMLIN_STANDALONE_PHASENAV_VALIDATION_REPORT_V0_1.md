# GREMLIN Standalone PhaseNav Validation Report v0.1

Status: **CANDIDATE / CORE VALIDATION PASS / PACKAGING PREVIEW GATE RUNNING**

Repository: `AdrianLipa90/GREMLIN`

Branch: `feat/bestiary-phasenav-phase-gates-v0.1`

Validated branch head at report cut: `3a841b73ca37e9904ccab7fb2eba0ac590b3125c`

Base `main` SHA: `b33d8c3fec014db4686856958c17e0e948192742`

Pull request: **#62**, draft, mergeable. No merge to `main` was performed.

## 1. Purpose

This report closes the import/runtime question for the vectorized GREMLIN Bestiary
PhaseNav implementation and records the evidence boundary precisely.

The target was not merely "imports work from the repository checkout". The target
was an independently installable/runtime-capable GREMLIN surface with:

- all 18 Bestiary roles present in the standalone MCP core;
- scalar, NumPy-vector and continuous T^36 PhaseNav realizations importable;
- no dependency on a live NOEMA surface for the computational core;
- optional live PhaseNav/NOEMA replay with no static fallback;
- Linux and Windows isolated-wheel execution outside the source tree;
- Linux and Windows compiled standalone executable support;
- fail-closed authority semantics retained.

## 2. Runtime surface after hardening

The standalone surface now exposes three distinct executable aliases:

```text
gremlinctl            installation / diagnostics / configuration control
gremlin-product-mcp   licensed product MCP boundary
gremlin-mcp           full GREMLIN + Hive + PhaseNav Bestiary MCP runtime
```

The Nuitka standalone build explicitly includes:

```text
gremlin_mcp.server_with_hive
gremlin_mcp.phasenav_runtime
tools.gremlin_bestiary_phasenav_phase_gates_v01
tools.gremlin_bestiary_phasenav_numpy_v01
tools.gremlin_bestiary_phasenav_threeway_v01
tools.gremlin_bestiary_phasenav_analog_invariants_v01
tools.gremlin_bestiary_phasenav_live_binding_v01
```

`numpy>=1.26,<3` is now an explicit package dependency. Vector execution therefore
does not rely on an undeclared environment package.

Linux Debian packaging exposes `/usr/bin/gremlin-mcp`; the Windows standalone
runtime contains `gremlin-mcp.exe`. Preview and Early Access package workflows
have been tightened to execute the same PhaseNav self-test from installed/compiled
runtime surfaces.

## 3. Standalone self-test

A bounded public runtime gate was added:

```text
gremlin-mcp --self-test-phasenav
```

Its contract is `GREMLIN_STANDALONE_PHASENAV_SELF_TEST_V0_1`.

A PASS requires:

- 18/18 Bestiary roles available;
- NumPy vector backend available;
- standalone reference sweep PASS;
- scalar/vector/continuous three-way suite PASS;
- analog-core specialist invariant suite PASS;
- `live_noema_required=false`;
- `external_effects=false`;
- `canon_allowed=false`;
- `physical_analog_claim=false`.

The standalone computational core does **not** require
`/dev/shm/ciel_noema`. Live replay remains a separate optional fail-loud path.

## 4. Exact-head CI evidence

### Repository fail-loud audit

Workflow run: `35331457703`

Result:

```text
1312 passed
1 skipped
0 failed
standalone wheel outside source tree: PASS
```

The wheel smoke emitted `STANDALONE_WHEEL_IMPORT_SURFACE_PASS`.

### Installation architecture

Workflow run: `35331457764`

Linux job:

```text
146 passed
1 skipped
ISOLATED_LINUX_WHEEL_RUNTIME_PASS
PhaseNav standalone self-test: PASS
species_count = 18
live_noema_required = false
```

Windows job:

```text
72 passed
4 skipped
ISOLATED_WINDOWS_WHEEL_RUNTIME_PASS
PhaseNav standalone self-test: PASS
species_count = 18
live_noema_required = false
```

This closes the previous Windows evidence gap: the Windows gate now builds a real
wheel, installs it into a fresh venv, changes execution context away from the source
tree, imports GREMLIN/PhaseNav, and runs `gremlin-mcp --self-test-phasenav`.

### GREMLIN MCP

Workflow run: `35331457773`

```text
86 passed
0 failed
```

### Product licensing

Workflow run: `35331457826`

```text
48 passed
0 failed
```

### PhaseNav Bestiary gate

Workflow run: `35331457843`

```text
136 passed
0 failed
18 / 18 species three-way realization PASS
scalar/vector max torus error = 0.0
max fine-vs-continuous RMS error = 0.0008214511194856206 rad
max fine/coarse convergence ratio = 0.12290964222812932
analog-core numerical candidates = 9
hybrid / authority-boundary roles = 9
analog-core specialist invariants = 9 / 9 PASS
fully analog physical pass = 0
hardware analog witness = false
```

The hosted NumPy fixture on this run measured:

```text
min speedup    = 2.700553x
median speedup = 2.870740x
max speedup    = 2.976360x
```

These are environment-specific Python/NumPy measurements only, with no promotion
threshold and no hardware-independent performance claim.

## 5. Realization classification

Current numerical classification:

**Analog-core numerical PASS with hybrid control**

```text
BAT
BEAVER
CANARY
FOX
HOUND
MOLE
RAVEN
SERPENT
SPIDER
```

**Hybrid / authority-boundary PASS**

```text
ANT
BELZEBUB
CHAMELEON
FERRET
GREMLIN
HUMMINGBIRD
MANTIS
OCTOPUS
OWL
```

This classification means the first group has a continuous phase-field numerical
core compatible with the tested specialist invariant. It does **not** mean that the
entire specialist semantics or hardware realization is physically analog.

## 6. Cross-platform compiled standalone evidence

A separate cross-platform standalone workflow has already passed on the same runtime
content immediately before the packaging-trigger-only head change:

Workflow run: `35323817592`

Linux compiled Nuitka runtime:

```text
gremlin-runtime        present
gremlinctl             present
gremlin-product-mcp    present
gremlin-mcp            present
gremlin-mcp --self-test-phasenav -> PASS
```

Windows compiled Nuitka runtime:

```text
gremlin-runtime.exe        present
gremlinctl.exe             present
gremlin-product-mcp.exe    present
gremlin-mcp.exe            present
gremlin-mcp.exe --self-test-phasenav -> PASS
```

Both emitted:

```json
{
  "schema": "GREMLIN_STANDALONE_PHASENAV_SELF_TEST_V0_1",
  "status": "PASS",
  "species_count": 18,
  "vector_backend_available": true,
  "threeway_all_species_pass": true,
  "analog_core_invariants_pass": true,
  "live_noema_required": false,
  "external_effects": false,
  "canon_allowed": false,
  "physical_analog_claim": false
}
```

The current head is re-running this gate because the pull-request packaging trigger
was added; no GREMLIN runtime code changed between that successful compiled-runtime
evidence and the report-cut head.

## 7. Packaging preview gate

Workflow run: `35331457645`

At report cut, Linux and Windows preview packaging jobs are actively building the
standalone Nuitka runtime. The workflow has been upgraded to test:

```text
compiled standalone runtime
  -> gremlin-mcp --self-test-phasenav
  -> platform package / installer
  -> install package
  -> installed gremlin-mcp --self-test-phasenav
  -> entitlement/resources checks
  -> customer Connect-Test-READY-Disconnect gate
  -> artifact hash + upload
```

This gate is intentionally recorded as **RUNNING**, not PASS, until both platform
jobs complete successfully.

## 8. Authority and claim boundary

All validated PhaseNav/Bestiary computational paths retain:

```text
external_effects = false
canon_allowed = false
physical_analog_claim = false
hardware_analog_witness = false
static_runtime_fallback = false for live binding
```

`FERRET` remains an explicit authority boundary. Candidate computation does not
implicitly promote to execution or canon.

## 9. Verdict

The original import/runtime concern is closed at the Python package and compiled
standalone-runtime levels:

```text
Linux isolated wheel          PASS
Windows isolated wheel        PASS
Linux compiled standalone     PASS
Windows compiled standalone   PASS
18-role Bestiary import       PASS
PhaseNav vector backend       PASS
three-way numerical gate      PASS
9 analog-core invariants      PASS
repository fail-loud audit    PASS
MCP contract                  PASS
licensing contract            PASS
```

The remaining open validation item at report cut is the **new end-to-end preview
installer/package gate**, which is stricter than the original standalone import
requirement.

Therefore the correct current statement is:

> GREMLIN now has verified independent Linux and Windows Python-wheel and compiled
> standalone runtime surfaces for the full 18-role PhaseNav Bestiary. The PhaseNav
> computational core does not require live NOEMA. Physical fully-analog realization
> is not established. End-to-end preview package/installer validation is running.

No merge to `main` and no canon promotion are authorized by this report.
