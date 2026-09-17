# GREMLIN Bestiary PhaseNav Phase Gates v0.1

Status: CANDIDATE / PURE REFERENCE 22/22 PASS / NO PHYSICAL ANALOG CLAIM / NO EXTERNAL EFFECTS

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

Pure reference suite: `22/22 PASS`.

Coverage includes exact 36D fail-closed shape/bounds, scalar/batch equivalence, deterministic identities, all 18 species operators, injected BAT harmonic detection, CANARY drift detection, SERPENT temperature/novelty response, CHAMELEON reversible roundtrip, defensive synthesis, and FERRET fail-closed authority.

## Authority

All returned species results are candidates:

```text
canon_allowed = false
external_effects = false
```

FERRET may return an `ADMITTED` authority verdict only when explicit authorization, scope match and receipt validity are all true. Even then this module does **not** execute the external action.

## Next gate

1. run repository CI on the exact feature-branch head;
2. add a frozen phase workload and benchmark scalar vs batch-first PhaseNav kernels;
3. bind species phase carriers to exact PNCS/PhaseNav operator vectors where authoritative vectors exist;
4. run live T^36 replay under fresh NOEMA tether with no static fallback;
5. only after numerical equivalence, test hardware/analog realization candidates separately.
