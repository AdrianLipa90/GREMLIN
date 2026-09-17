# GREMLIN Bestiary PhaseNav Phase Gates v0.1

Status: CANDIDATE / COMPUTATIONAL VECTOR GATE PASS / EXACT 36D / NO PHYSICAL ANALOG CLAIM / NO EXTERNAL EFFECTS

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

Exact evidence head: `68107a699107655b106ac365fc0610616e76c325`.

Dedicated PhaseNav phase-gate workflow `35288246350`: `64/64 PASS`.

Repository-wide fail-loud audit `35288246332`: `1236 PASS / 1 SKIP / 0 FAIL`.

Frozen NumPy batch workload: 512 states x 36 coordinates, 7 repeats per species, all 18 species.

Observed batch-vector equivalence and performance on the hosted CI fixture:

```text
max scalar/vector torus error = 0.0
equivalence tolerance          = 1e-12
all 18 species equivalent     = PASS
all continuity probes finite  = PASS
min measured speedup           = 2.987266x
median measured speedup        = 3.021190x
max measured speedup           = 3.067365x
```

The speedup is an environment-specific Python/NumPy batch result, not a hardware-independent throughput claim. The continuity probes establish numerical continuity of the implemented phase kernels on the frozen fixture; they do not establish physical analog realization.

Pinned CI receipt: `provenance/GREMLIN_BESTIARY_PHASENAV_NUMPY_CI_RECEIPT_V0_1.json`.

Coverage includes exact 36D fail-closed shape/bounds, scalar/vector-batch equivalence, deterministic identities, all 18 species operators, injected BAT harmonic detection, CANARY drift detection, SERPENT temperature/novelty response, CHAMELEON reversible roundtrip, defensive synthesis, FERRET fail-closed authority, no silent scalar fallback, and repository-wide PNV contract compatibility.

## Authority

All returned species results are candidates:

```text
canon_allowed = false
external_effects = false
```

FERRET may return an `ADMITTED` authority verdict only when explicit authorization, scope match and receipt validity are all true. Even then this module does **not** execute the external action.

## Next gate

The pure computational/vector gate and frozen benchmark gate are now closed for this candidate branch.

1. bind species phase carriers to exact PNCS/PhaseNav operator vectors where authoritative vectors exist; absent an authoritative vector, fail closed rather than inventing one;
2. run live T^36 replay under fresh NOEMA tether with `static_fallback=false`;
3. compare digital scalar, digital batch-vector and phase-flow/hydrodynamic realizations on the same frozen semantic workload;
4. classify each species only from evidence as `HYBRID`, `ANALOG_CORE_HYBRID_CONTROL`, or a later hardware-witnessed analog class;
5. test hardware/analog realization candidates separately. No fully-analog claim is permitted from numerical continuity alone.
