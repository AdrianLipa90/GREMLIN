# GREMLIN Valuation and Integrity Antecedent Bundles v0.7

Status: IMPLEMENTED_CANDIDATE

## Purpose

v0.7 binds three pre-vector semantic structures used before PhaseNav realization:

1. valuation over a declared comparison set,
2. contradiction as an evidenced incompatibility relation,
3. recursive integrity as an evidenced structural antecedent over contradiction and recursive re-entry.

The layer preserves lineage and scale information so later potential, energy, geometry and vector synthesis can consume auditable inputs.

## 1. Valuation

Semantic binding: `CLX2-AFFECT-001`.

A valuation item binds:

- an `option_id`,
- a finite scalar value,
- an explicit `scale_id`,
- a source reference,
- an epistemic status.

The value is encoded with the exact Python binary64 hexadecimal representation. The value origin is recorded as `EXPLICIT_DECLARATION_OR_UPSTREAM_PRODUCER`.

A valuation profile binds one comparison set and one criterion. All members of a profile share one declared scale. Canonical ordering is by `option_id`. The declared scale is preserved without implicit normalization.

A KAKU valuation binding selects exactly one option from one committed valuation profile and retains both the profile commitment and selected item commitment.

Valuation authority flags remain closed for truth, epistemic support, execution and canon promotion. Vector synthesis remains closed at this layer.

## 2. Contradiction antecedents

Semantic binding: `CLX2-DYN-009`.

A contradiction item records `DECLARED_INCOMPATIBILITY` between exactly two committed states. Endpoint kinds are:

- `COMMITMENT`,
- `CONSTRAINT`,
- `PREDICTION`,
- `GOAL`.

Each contradiction carries a criterion reference, one or more evidence references and an epistemic status. Endpoint order and evidence references are canonicalized before commitment sealing.

A Radical contradiction bundle binds a canonical set of contradiction items and records `declared_conflict_count` as structural metadata. `contradiction_load_scalar_present` remains false and `scalarization_status` remains `UNRESOLVED` pending an explicit reduction law.

## 3. Recursive-integrity antecedents

Semantic binding: `CLX2-DYN-010`.

Dependency terms are fixed to:

- `CLX2-TIME-009` — Recursive Re-entry,
- `CLX2-DYN-009` — Contradiction.

Recursive-integrity evidence is organized by four aspects:

- `TRAVERSE_CONTRADICTION`,
- `REENTER_RELATIONAL_LOOP`,
- `DISTINCTION_PRESERVATION`,
- `FRAGMENTATION_CONTROL`.

Each aspect is bound to one of `EVIDENCED`, `UNRESOLVED`, or `FAILED`, together with source and source commitment.

Bundle state is derived deterministically:

- any `FAILED` aspect -> `FAILED_EVIDENCE_PRESENT`,
- any missing or `UNRESOLVED` aspect -> `OPEN`,
- all four aspects `EVIDENCED` -> `COMPLETE_EVIDENCED`.

The Radical identifier must match the contradiction bundle lineage. The recursive re-entry commitment and contradiction-bundle commitment are both retained.

`recursive_integrity_scalar_present` remains false and `scalarization_status` remains `UNRESOLVED`. This preserves the full antecedent structure for a later declared scalarization or relational potential map.

## 4. Commitment and fail-closed validation

Every item and bundle is sealed with a domain-separated BLAKE2b-256 commitment over canonical JSON. Validators recompute commitments and verify structural invariants.

Tampering with values, states, lineage, ordering contracts or authority flags causes validation failure.

## 5. Pre-vector frontier

v0.7 extends the scalar/antecedent plane while retaining the existing admission boundary. Its outputs are intended to feed the next relational layer:

`KAKU/RADICAL antecedents -> relational potential -> energy/mass layer -> relational geometry -> vector field -> exact PhaseNav realization`.

The potential, energy and geometry mappings require their own explicit coordinate, dimensional and provenance contracts before vector synthesis is admitted.
