# GREMLIN Orbital Hive Memory v0.1

Status: `REFERENCE_IMPLEMENTED / APPEND_ONLY / FAIL_CLOSED_LATCH / SHARED_COGNITION_ONLY / LIVE_AUTHORITY_NOT_PROMOTED`

## Purpose

This layer turns GREMLIN's existing semantic routing, Bestiary mass-orbit scheduling, persistent lineage and PhaseNav phase carriers into a shared synchronous working-memory surface.

The central rule is:

```text
importance determines orbit
meaning determines angle
relation determines phase
closure triggers persistence
```

It is a memory/orchestration contract. It does not grant execution, repository-write, publication or canon authority.

## Flat concentric table

For information item `I_i`, the reference coordinate is

\[
I_i=(r_i,\theta_i,\phi_i,s_i,p_i,\Pi_i),
\]

where:

- `p_i` is normalized information priority;
- `r_i` is its concentric orbit/radius;
- `theta_i` is a deterministic semantic address;
- `phi_i` is a caller-supplied relational phase reduced modulo `2 pi`;
- `s_i` is `OPEN`, `ALIGNING`, `DISPUTED`, `QUARANTINED`, or `LOCKED`;
- `Pi_i` is provenance lineage.

The current reference layout has 36 concentric rings. Higher priority is assigned to a smaller radius. The flat readout is sorted inner-to-outer and then by semantic angle and relational phase.

### Semantic-address firewall

`semantic_angle(key)` hashes an explicit upstream semantic key into `[0,2 pi)`. This is deterministic addressing only. It does **not** claim that lexical/semantic distance is physically represented by angular distance. A later PhaseNav/CIELingo semantic geometry may replace this reference address only through an explicit typed interface.

### Phase firewall

`relation_phase` is not inferred from payload text. It must be supplied by the caller/upstream relational layer. The Hive stores and normalizes the phase but does not invent its physical meaning.

## Latch

An information item can be latched only when all five independent gates are true:

```text
evidence_ready
dependencies_closed
contradiction_audited
provenance_complete
phase_coherent
```

The latch is therefore a conjunction, not a confidence average.

When all gates pass, GREMLIN emits a BLAKE2b content-addressed latch receipt over:

- source record id;
- payload hash;
- exact orbital/semantic/phase coordinate;
- provenance;
- dependencies;
- complete closure-gate state;
- authority class.

The resulting `LOCKED` record is a new append-only version. It does not overwrite its parent.

## Conflict semantics

A contradiction does not erase memory. It creates a `DISPUTED` child with:

- preserved parent lineage;
- preserved coordinate;
- explicit contradiction reference;
- `contradiction_audited=false`.

`DISPUTED` and `QUARANTINED` records cannot latch.

This prevents last-writer-wins collapse and preserves competing hypotheses at their exact historical coordinates.

## Authority invariant

Every record carries:

```text
authority = SHARED_COGNITION_ONLY
```

The Hive may synchronize perception, analysis state and consensus status across GREMLIN/OCTOPUS/BELZEBUB/HOUND/etc., but it cannot create mutation authority.

\[
\boxed{\text{shared cognition} \neq \text{shared authority}}
\]

Repository writes, messages, publications and other external effects still require their normal admission/authorization path.

## Persistence

`SQLiteHiveStore` is append-only and uses SQLite WAL with `synchronous=FULL`. The durable rows are content-addressed records rather than mutable subject snapshots.

This is deliberately compatible with GREMLIN's existing persistence discipline while remaining separate from worker/task/lease tables, so Hive-memory corruption cannot silently rewrite Worker ABI coordination state.

## Integration with existing GREMLIN layers

```text
OCTOPUS / Bestiary inputs
        |
        v
semantic key + priority + relation phase
        |
        v
ORBIT ASSIGNMENT
        |
        v
36-ring flat Hive table
        |
        +--> HOUND evidence/provenance
        +--> RAVEN contradiction checks
        +--> SPIDER dependency closure
        +--> BELZEBUB adversarial quarantine
        |
        v
five-gate closure
        |
        v
LATCH RECEIPT
        |
        v
persistent orbital memory
```

The existing Bestiary scheduler continues to own worker cadence/mass/radius. Hive `priority_orbit` describes **information placement**, not worker species mass. These are two distinct typed orbital roles and must not be silently equated.

## Claim status

- deterministic 36-ring priority placement: `REFERENCE_DEFINITION`;
- deterministic semantic-key angle: `REFERENCE_ADDRESSING_ONLY`;
- supplied phase normalization: `EXACT_NUMERIC_OPERATION`;
- append-only parent lineage: `IMPLEMENTED`;
- five-gate fail-closed latch: `IMPLEMENTED`;
- BLAKE2b latch receipt: `IMPLEMENTED`;
- SQLite WAL append-only persistence: `IMPLEMENTED`;
- semantic geometry interpretation: `OPEN`;
- live NOEMA Hive synchronization: `OPEN / NOT PROMOTED`;
- production/canon authority: `DENIED BY CONTRACT`.
