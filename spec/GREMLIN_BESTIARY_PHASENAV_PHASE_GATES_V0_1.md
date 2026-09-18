# GREMLIN Bestiary PhaseNav Phase Gates v0.1

Status: CANDIDATE / THREE-WAY COMPUTATIONAL REALIZATION PASS / EXACT 36D / NO PHYSICAL ANALOG CLAIM / NO EXTERNAL EFFECTS

## Objective

Bind the GREMLIN Bestiary to an exact 36-dimensional PhaseNav phase state and a deterministic phase-gate substrate without assigning invented semantic meanings to the 36 coordinates.

The gate is a reference execution layer for hybrid and analog-realizable experiments. It does not claim that the current Python implementation is physical analog hardware.

## State

`theta = (theta_0,...,theta_35) in T^36`, each coordinate in `[0,2pi)`.

The coordinate order is preserved exactly. Axis semantics remain unassigned until a separate PNCS basis-binding gate supplies them.

## Phase gate

For species carrier `b_i`, current state `theta_i`, nearest-neighbour coordinates `theta_(i-1), theta_(i+1)`, and step `dt`:

```text
drive_i    = a sin(b_i - theta_i)
couple_i   = (k/2)[sin(theta_(i-1)-theta_i)+sin(theta_(i+1)-theta_i)]
harmonic_i = h sin(2(b_i-theta_i))

theta_i' = wrap_2pi(theta_i + dt*(drive_i+couple_i+harmonic_i))
```

Species carriers are deterministic routing/gate identities derived from the species label. They are **not** semantic-axis assignments.

## Species covered

`HUMMINGBIRD, OCTOPUS, SPIDER, RAVEN, HOUND, MOLE, OWL, ANT, MANTIS, FOX, BEAVER, BAT, CANARY, SERPENT, CHAMELEON, BELZEBUB, GREMLIN, FERRET`.

The first implementation contains one concrete reference operator for every species:

- HUMMINGBIRD: immutable T^36 capture;
- OCTOPUS: bounded phase-similarity routing;
- SPIDER: pairwise phase-coherence relation graph;
- RAVEN: phase-similarity memory recall;
- HOUND: torus residual/anomaly scan;
- MOLE: local target-directed phase relaxation;
- OWL: claim/evidence phase-support audit;
- ANT: bounded phase-variant enumeration;
- MANTIS: torus duplicate pruning;
- FOX: geodesic phase-plan construction;
- BEAVER: weighted circular candidate construction;
- BAT: weak phase-signal spectral scan;
- CANARY: phase-speed CUSUM sentinel;
- SERPENT: latent-field temperature + taste signature;
- CHAMELEON: reversible phase skin/profile transform, explicitly **not cryptography**;
- BELZEBUB: robust medoid-centred defensive synthesis;
- GREMLIN: verified-head circular aggregation candidate;
- FERRET: authorization boundary only; no action is executed by this module.

## Realization classes

`HYBRID`: digital control/provenance is essential to the present operator.

`ANALOG_CORE_HYBRID_CONTROL`: the numerical core is expressed as continuous phase/coherence/dynamical operations suitable for later analog realization, while routing, receipts and authority remain digital/hybrid.

`HYBRID_AUTHORITY_BOUNDARY`: effect admission remains explicit and fail-closed.

No species is declared physically analog by this v0.1 gate.

## Validation

Exact three-way functional-code evidence head: `87e7043ad41c6c2924c85d93ad8407ce5f2b3792`.

Dedicated PhaseNav phase-gate workflow `35291358763`: `131/131 PASS`.

Repository-wide fail-loud audit `35291358759`: `1303 PASS / 1 SKIP / 0 FAIL`.

Frozen NumPy batch workload: 512 states x 36 coordinates, 7 repeats per species, all 18 species.

Observed batch-vector equivalence and performance on the hosted CI fixture:

```text
max scalar/vector torus error = 0.0
equivalence tolerance          = 1e-12
all 18 species equivalent      = PASS
all continuity probes finite   = PASS
min measured speedup           = 3.020201x
median measured speedup        = 3.218813x
max measured speedup           = 3.240178x
```

The speedup is an environment-specific Python/NumPy batch result, not a hardware-independent throughput claim.

### Scalar / vector / continuous phase-flow gate

The same frozen phase workload was evaluated through three numerical realizations of the same phase field:

```text
scalar digital     = forward-Euler PhaseGate36
vector digital     = NumPy batch forward-Euler of the same field
continuous ref.    = RK4 integration of the exact continuous T^36 field
```

Predeclared gates:

```text
scalar/vector max coordinate error <= 1e-12
fine Euler vs continuous max RMS   <= 1e-2 rad
fine/coarse continuous-error ratio <= 0.50
```

Observed exact-head result:

```text
species tested                         = 18 / 18
all species pass                       = true
scalar/vector max coordinate error     = 0.0
max fine-vs-continuous RMS error       = 0.0008214511194856206 rad
max fine/coarse convergence ratio      = 0.12290964222812932
analog-core numerical pass             = 9
hybrid / authority-boundary pass       = 9
fully analog physical pass             = 0
hardware analog witness                = false
```

Analog-core numerical pass with hybrid control:

`BAT, BEAVER, CANARY, FOX, HOUND, MOLE, RAVEN, SERPENT, SPIDER`.

Hybrid or hybrid-authority-boundary pass:

`ANT, BELZEBUB, CHAMELEON, FERRET, GREMLIN, HUMMINGBIRD, MANTIS, OCTOPUS, OWL`.

This classification is deliberately narrower than a physical analog claim. For the nine analog-core species it establishes that the implemented digital phase gate converges toward the corresponding continuous phase-field dynamics on the frozen workload while preserving exact scalar/vector equivalence. The remaining nine retain hybrid semantics because discrete routing, epistemic judgment, construction, aggregation, cryptographic/profile handling, or authority remains part of the role.

Pinned receipts:

- `provenance/GREMLIN_BESTIARY_PHASENAV_NUMPY_CI_RECEIPT_V0_1.json`
- `provenance/GREMLIN_BESTIARY_PHASENAV_THREEWAY_CI_RECEIPT_V0_1.json`

Workflow artifact `10527050191` contains both frozen benchmark JSON files and is pinned by ZIP SHA-256 `295368070189d869fbb5eb9ec51d42d5a1e82ea1a36f3e67aec83ac204023fe6`.

Coverage includes exact 36D fail-closed shape/bounds, deterministic identities, all 18 species operators, scalar/vector trajectory equivalence, continuous-field convergence, injected BAT harmonic detection, CANARY drift detection, SERPENT temperature/novelty response, CHAMELEON reversible roundtrip, defensive synthesis, FERRET fail-closed authority, no silent scalar fallback, and repository-wide PNV contract compatibility.

### Analog-core specialist invariant gate

The shared continuous phase-field result was followed by a specialist-specific
signal-preservation gate for every species currently classified as
`ANALOG_CORE_HYBRID_CONTROL`.

Exact invariant-code evidence head:
`eb9fa0b9ac4dc375e5e240d626e70a20e6347a23`.

Dedicated workflow `35291684002`: `136/136 PASS`.

Repository-wide fail-loud audit `35291683992`:
`1308 PASS / 1 SKIP / 0 FAIL`.

All nine analog-core species preserved their preregistered specialist invariant
after continuous phase preconditioning:

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

passed = 9 / 9
failed = 0
```

Pinned receipt:
`provenance/GREMLIN_BESTIARY_PHASENAV_ANALOG_INVARIANTS_CI_RECEIPT_V0_1.json`.

This gate still uses the existing specialist operator after continuous phase
preconditioning. It therefore strengthens analog-core compatibility evidence,
but it does **not** establish fully analog specialist semantics.

## Live T^36 operator-binding replay

A current-session replay was executed against the canonical live NOEMA surface
`/dev/shm/ciel_noema` after a fresh tether guard returned `ACTIVE` with no
failures. Static fallback remained disabled. The live witness is an independent
local replay of the documented v0.1 equations and the exact explicit binding
profile; hosted CI separately covers the repository implementation.

The live registry contained 36 exact `PHASENAV_OPERATOR_VECTOR_V1` vectors.
Each Bestiary species was bound to an explicit candidate composition of existing
PhaseNav operator vectors.  These compositions are reviewable candidate
bindings; they are not semantic-axis canonization.

Runtime witness:

`provenance/GREMLIN_BESTIARY_PHASENAV_LIVE_T36_RUNTIME_WITNESS_V0_1.json`

Observed on the frozen live snapshot:

```text
species replayed                 = 18 / 18
unique species carriers          = 18 / 18
steps per species                = 16
non-zero phase displacement      = 18 / 18
target distance reduced          = 18 / 18
target distance monotone         = 18 / 18
final/initial distance ratio     = 0.601287 .. 0.783944
static runtime fallback          = false
external effects                 = false
physical analog claim            = false
```

This closes the first independent live computational T^36 replay gate. It demonstrates
that every current species can be driven on the live phase substrate through
its candidate operator composition without leaving the candidate-only
authority boundary.  It does **not** establish a hardware analog realization
or validate the candidate semantic composition as canonical.

## Authority

All returned species results are candidates:

```text
canon_allowed = false
external_effects = false
```

FERRET may return an `ADMITTED` authority verdict only when explicit authorization, scope match and receipt validity are all true. Even then this module does **not** execute the external action.

## Next gate

The computational scalar/vector/continuous-field gate and the analog-core
specialist-invariant gate are closed for this candidate branch.

1. bind the continuous phase path to the current hydrodynamic/QHTRI substrate and compare identical specialist workloads end-to-end;
2. isolate which hybrid roles can move additional decision sub-operators into continuous phase dynamics without weakening provenance or authority;
3. replace selected digital post-operators with explicit continuous candidates one at a time and require invariant equivalence before promotion;
4. test hardware/analog realization candidates separately with measured electrical/physical witnesses. No fully-analog claim is permitted from numerical continuity alone.
