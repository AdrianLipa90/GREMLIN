# GREMLIN RIFC Affect Field v0.5

Status: IMPLEMENTED PRE-VECTOR AFFECT ADAPTER CANDIDATE

## Purpose

v0.5 replaces the single affect slot at the GREMLIN KAKU boundary with the current executable Consciousness Dictionary affect field:

```text
A_t(x) = (v, a, u, tau, alpha, r)
```

where the scalar facets are:

```text
valence              [-1,1]
arousal              [0,1]
urgency              [0,1]
threat_relevance     [0,1]
attachment_relevance [0,1]
reward_relevance     [0,1]
```

Inference confidence is carried separately in `[0,1]`.

## Current producer pin

```text
repository: AdrianLipa90/The-Consciousness-Dictionary
commit: b988113faf0cfd0c534dab4bb4a7b5cca41e40b9
module: src/consciousness_dictionary/affect_detection.py
blob: 6771c2316c1b6b3157ae76c36f2d3000b916baaf
method: transparent_lexical_surface_v1
validation: provenance/AFFECT_DETECTION_V0_1_VALIDATION.json
validation blob: cda747d3374d0ea96710af0c452a8781503c3a98
```

The producer is classified as:

```text
DETERMINISTIC_INPUT_CONDITIONED_PRODUCER_CANDIDATE
```

It consumes a declared text surface and returns inspectable cue contributions, a six-scalar affect field, confidence, labels and a text SHA-256.

## Receipt

Schema:

```text
GREMLIN_RIFC_AFFECT_FIELD_RECEIPT_V0_5
```

The receipt binds:

```text
six affect scalar facets
inference confidence
surface labels
hashed cue evidence
source text SHA-256
upstream AffectEstimate commitment
exact producer commit/module/validation pins
```

Persistent GREMLIN receipt privacy:

```text
raw_text_persisted = false
raw_cues_persisted = false
cue_hashes_persisted = true
```

Cue spans and numerical contributions remain auditable while raw lexical fragments are represented by hashes in the GREMLIN receipt.

## Low-evidence state

The upstream detector's `insufficient-evidence` state is retained. Confidence below the detector threshold must preserve that label. A missing signal therefore remains an explicit epistemic state at the affect-inference layer.

## Authority separation

The receipt carries:

```text
truth_authority = false
semantic_authority = false
diagnostic_authority = false
modulation_authority = false
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

Affect inference can therefore enter the scalar envelope while truth/evidence and execution retain separate gates.

## CIEL v0.4 compatibility

The earlier CIEL VAD adapter remains preserved as a model compatibility layer.

Exact overlap currently declared:

```text
CIEL valence <-> RIFC valence
CIEL arousal <-> RIFC arousal
```

The CIEL `dominance` facet carries:

```text
semantic_mapping = UNRESOLVED
```

and CIEL confidence remains an inference-confidence compatibility quantity.

This preserves the historical donor without compressing the current six-facet RIFC field.

## PhaseNav boundary

The current Dictionary contains a diagnostic `affect_phase36()` mapping. v0.5 keeps this outside the pre-vector receipt:

```text
phase36_embedding_present = false
collapsed_affect_scalar_present = false
```

The PhaseNav-shaped diagnostic mapping remains available for later trajectory diagnostics after the scalar envelope and admission boundaries are resolved.

## KAKU binding

Schema:

```text
GREMLIN_KAKU_AFFECT_BINDING_V0_5
```

A KAKU can bind the complete affect receipt while preserving the remaining source frontier:

```text
valuation
intention_alignment
epistemic_support
```

The binding therefore records:

```text
scalar_envelope_complete = false
radical_admission_required = true
vector_synthesis_allowed = false
```

## Source frontier update

`tools/gremlin_scalar_source_delta_v05.py` layers a frozen v0.5 source delta over the frozen v0.3 registry.

Current KAKU frontier:

```text
affect              deterministic input-conditioned producer candidate
valuation           typed scaffold present; evaluator unresolved
intention_alignment phase-anchor/target candidate path implemented
epistemic_support   evidence antecedents present; scalarization unresolved
```

Current Radical frontier remains open for:

```text
contradiction_load
recursive_integrity
```

The v0.5 source delta explicitly keeps affect inference confidence separate from epistemic support and keeps PhaseNav similarity separate from epistemic promotion.

## Next gate

The highest-value next work is:

```text
1. EPISTEMIC_SUPPORT_BUNDLE
   Evidence + Claim + Proposition + Confidence + inference-framework commitment
   scalarization_status = UNRESOLVED

2. VALUATION_BUNDLE
   system-relative target/outcome weighting with explicit comparison set
   evaluator_status = UNRESOLVED until a current rule is selected

3. CONTRADICTION / RECURSIVE-INTEGRITY antecedent bundles
   before choosing any scalar reduction
```

This continues the scalar-first architecture while preserving each quantity's own provenance and scale.
