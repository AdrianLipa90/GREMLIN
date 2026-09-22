# GREMLIN Relational-Memory Bestiary Extension v0.1

Status: `IMPLEMENTED_CANDIDATE / MEMORY_ONLY / NO_CANON_AUTHORITY`

Date: 2026-09-22

## Scope

This extension adds two Bestiary roles derived from a substrate-agnostic relational-memory model:

- `ELEPHANT`: consolidation, replay and retention planning;
- `BEES`: local coherence, overlap checking and anti-entropy reconciliation proposals.

The model is informational. It does not require a biological substrate and does not infer biological identity from behavioral similarity.

The current PhaseNav carrier set remains the validated 18-role runtime surface. ELEPHANT and BEES are introduced first as typed memory roles with no scheduler profile and no physical/analog claim.

## Relational-memory state

A candidate memory trace is represented by a 6 x 6 phase-organized state

[
X^{(\mu)}_{a k}(t) = A^{(\mu)}_{a k}
\exp i\left(\omega^{(\mu)}_a t + \phi^{(\mu)}_{a k} + m_k\theta^{(\mu)}_a\right),
\qquad a,k\in\{0,\ldots,5\}.
]

The indices are intentionally factored:

[
36 = 6_{\text{projection/context}} \times 6_{\text{lateral channel}}.
]

A memory is not defined as one immutable record. It is a provenance-bearing relational orbit or attractor candidate over this state surface.

## ELEPHANT

### Responsibility

ELEPHANT handles long-horizon memory consolidation without destructive editing.

It may:

1. read subject-scoped episodic, semantic and relational payloads;
2. compare candidate traces;
3. derive `MEMORY_ORBIT` artifacts;
4. emit `CONSOLIDATION_RECEIPT` artifacts;
5. emit `REPLAY_PLAN` artifacts;
6. issue `RETENTION_REQUEST` proposals.

It may not:

- delete memory;
- overwrite memory;
- edit memory in place;
- grant itself canon authority;
- convert similarity into truth.

### Candidate coherence observable

A phase-coherence observable may be used as evidence, not authority:

[
K_\mu(t)
=
\left|
\frac{1}{36}
\sum_{a=0}^{5}\sum_{k=0}^{5}
e^{i(\phi^{(\mu)}_{ak}(t)-\bar\phi_\mu(t))}
\right|.
]

The exact learning law is intentionally not canonized in v0.1. Consolidation is represented by typed derived artifacts and receipts rather than an arbitrary hard-coded update rule.

## BEES

### Responsibility

BEES checks whether distributed memory fragments remain mutually compatible.

For overlapping local charts (H_i,H_j), define the overlap set (O_{ij}). A candidate local mismatch observable is

[
\Gamma_{ij}
=
\frac{1}{|O_{ij}|}
\sum_{e\in O_{ij}}
d(z^{(i)}_e,z^{(j)}_e)^2.
]

BEES may:

1. compare memory metadata across the shared layers;
2. read subject-scoped payloads when explicitly authorized;
3. derive `COHERENCE_FINDING`;
4. derive `ANTI_ENTROPY_DELTA`;
5. derive `RECONCILE_PROPOSAL`;
6. flag `ANOMALY` findings.

BEES may not apply anti-entropy deltas, overwrite records, delete records or promote canon.

Thus:

[
\text{anti-entropy detection} \ne \text{anti-entropy authority}.
]

## Division of labor

- RAVEN retrieves and indexes memory.
- SPIDER constructs and maintains typed relational graphs.
- ELEPHANT consolidates and plans replay/retention.
- BEES checks distributed consistency and proposes reconciliation.
- HOUND hunts contradictions and anomalies.
- OWL audits epistemic support.
- GREMLIN aggregates candidates.
- RAPHAEL remains the governance/admission function.
- FERRET remains the final explicitly authorized actuation boundary.

## Empirical comparison surface

The first comparison target is behavioral/relational memory behavior. Suitable tests include:

- partial-cue pattern completion;
- context-dependent recall;
- interference between similar traces;
- reconsolidation after recall;
- graceful degradation under channel loss;
- retention after replay;
- false-memory / confabulation rate;
- consistency recovery after divergent replicas.

Human self-report can serve as one empirical reference series, but the software benchmark must retain explicit provenance and must not treat subjective similarity as proof of mechanism identity.

## Authority invariants

1. Memory mechanics do not grant authority.
2. Phase coherence does not establish truth.
3. No Bestiary role receives DELETE, OVERWRITE or IN_PLACE_EDIT.
4. New memory states are append-only derivations or typed proposals.
5. ELEPHANT and BEES are memory-only candidate roles until separate PhaseNav carrier validation passes.
6. Current 18-carrier PhaseNav validation remains historically intact and is not retroactively relabeled as 20/20.


## Integration baseline after OWL/runtime consolidation

This candidate was revalidated after GREMLIN `main` reached `b40e5b6129516b79ef9c8f98b74115b85aaf2792`, which includes adaptive-runtime final hardening, the fundamental repository overlay audit, and the OWL runtime audit. This note changes no authority or thresholds; it exists to bind the final pre-merge CI to the consolidated main state.
