# GREMLIN KAKU Scalar Facets v0.4

Status: IMPLEMENTED PRE-VECTOR FACET CANDIDATE

## 1. Construction order

v0.4 keeps the scalar-first order:

```text
semantic relation
-> KAKU identity
-> scalar observations / facets
-> scalar facet envelope
-> Radical composition
-> Radical ethics / hard gates
-> PRE_VECTOR_ADMISSION
-> PhaseNav realization
```

The v0.4 KAKU envelope carries only pre-vector state:

```text
vector_synthesis_allowed = false
vector_bound             = false
t36_realization_present  = false
semantic_mass_present    = false
execution_admitted       = false
canon_allowed            = false
```

## 2. Affect becomes a facet family

The historical KAKU scalar packet used one `affect` slot. CIEL's affective lexicon supplies a richer scalar family:

```text
Valence    V in [-1,+1]
Arousal    A in [0,1]
Dominance  D in [-1,+1]
Confidence Q in [0,1]
```

v0.4 preserves these as four separate scalars:

```text
GREMLIN_AFFECT_VAD_FACETS_V0_4
```

The packet binds the pinned donor implementation:

```text
AdrianLipa90/CIEL-Omega-ApokalypOS
aa0da54ef29a1f80dd0390427935342225388950
src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/memory/affective_lexicon.py
```

Donor role:

```text
SCALE_AND_MODEL_DONOR
```

The packet also computes the donor's candidate phase mapping:

```text
phi_V = pi(V+1)
phi_A = 2pi A
phi_D = pi(D+1)

z_A = [exp(i phi_V)+exp(i phi_A)+exp(i phi_D)] / 3
R_A = |z_A|
phi_Affect = arg(z_A), when R_A resolves the circular mean
```

This derived phase retains status:

```text
MODEL_REALIZATION_CANDIDATE
```

and the packet explicitly records:

```text
collapsed_affect_scalar_present = false
```

## 3. Intention: anchor, target, alignment

The current CIEL/NOEMA concept registry exposes a live scalar anchor:

```text
source:
  /dev/shm/ciel_noema/phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl
selector:
  name = Intention
field:
  geometric_phase_rad
```

v0.4 binds this as:

```text
intention_phase_anchor
scale = RADIAN_PHASE/v0.4
```

The anchor alone carries phase provenance. Alignment additionally requires an explicit future target:

```text
GREMLIN_INTENTION_TARGET_PHASE_V0_4
```

The target phase is canonicalized to:

```text
[0, 2pi)
```

Given anchor phase `phi_I` and target phase `phi_T`:

```text
delta = wrap_pi(phi_I - phi_T)
S_I   = cos(delta)
C_I   = (1 + cos(delta))/2
      = cos^2(delta/2)
```

where:

```text
S_I in [-1,1]
C_I in [0,1]
```

The resulting record is:

```text
GREMLIN_INTENTION_ALIGNMENT_CANDIDATE_V0_4
```

with epistemic status:

```text
MODEL_REALIZATION_CANDIDATE
```

The live provenance snapshot stores the anchor while preserving:

```text
target_status    = UNRESOLVED
alignment_status = UNRESOLVED
```

until a target declaration exists.

## 4. Formula recomputation firewall

Content commitments protect byte/content identity. v0.4 adds an independent formula firewall:

```text
tools/gremlin_kaku_scalar_facet_firewall_v04.py
```

For affect, the firewall rebuilds VAD phase results from the four primary facets.

For intention, the firewall recomputes:

```text
anchor - target
-> wrapped delta
-> cos(delta)
-> (1+cos(delta))/2
```

A modified derived value with a newly calculated content commitment therefore opens a FAIL state under formula recomputation.

## 5. KAKU scalar facet envelope

A complete candidate envelope binds:

```text
valuation observation receipt
Affect V/A/D/Q facet packet
Intention alignment candidate
Epistemic-support observation receipt
```

Schema:

```text
GREMLIN_KAKU_SCALAR_FACET_ENVELOPE_V0_4
```

Its content commitment binds all four scalar-family lineages while retaining affect as a multi-scalar family.

A complete KAKU facet envelope still declares:

```text
radical_admission_required = true
vector_synthesis_allowed   = false
```

The Radical therefore remains the contextual gate before PhaseNav realization.

## 6. Current source frontier

v0.4 adds representation and derivation contracts while preserving the v0.3 source-readiness firewall.

Current frontier:

```text
valuation          UNRESOLVED_LIVE_PRODUCER
affect             MODEL_DONOR_ONLY
intention anchor   LIVE_CIEL_NOEMA_OBSERVED
intention target   candidate-specific declaration required
intention alignment candidate formula implemented
epistemic support  UNRESOLVED_LIVE_PRODUCER
```

Consequently global vector synthesis remains closed.

## 7. Provenance

Live anchor snapshot:

```text
provenance/INTENTION_PHASE_ANCHOR_LIVE_WITNESS_V0_4.json
```

The witness records a live NOEMA/CIEL anchor receipt and preserves separate target/alignment status.

## 8. Next gate

The next scalar work should focus on source closure rather than geometric compression:

```text
1. valuation producer
2. affect live observation contract / facet acquisition
3. epistemic-support evidence aggregation
4. contradiction-load producer
5. recursive-integrity producer
6. ethics-coordinate map for directed Radical exchange
```

Only after those source contracts close should the facet envelope be admitted into a live Radical ethics exchange.
