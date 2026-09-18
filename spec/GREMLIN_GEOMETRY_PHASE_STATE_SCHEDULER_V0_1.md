# GREMLIN Geometry / Phase / State Scheduler v0.1

Status: CANDIDATE / DETERMINISTIC / FAIL-CLOSED / FIFO-NONPRIMARY

## Objective

Replace ordinary FIFO selection inside the standalone GREMLIN worker queue with
a deterministic scheduler whose primary coordinates are:

1. task geometry on PhaseNav `T^36`;
2. phase-cluster coherence;
3. task state: readiness, temperature, urgency and noise;
4. vector-lane capacity;
5. legacy orbital cadence only as a secondary tie-break where a legacy profile exists.

The scheduler changes task ordering only. It does not grant execution, runtime
write, canon promotion or physical/analog authority.

## Queue semantics

A routed task is still queued under one species. The scheduler does not override
OCTOPUS routing.

When a multi-species worker asks for work without naming a species, GREMLIN
scores each non-empty registered species queue from its current geometric/state
distribution. It selects the queue with the strongest coherent work packet,
not the oldest globally queued task.

Within the selected species, GREMLIN chooses a seed near the queue's circular
`T^36` centroid and greedily constructs a phase/state-near batch. FIFO order is
computed only as a benchmark/proxy comparator and is never the primary selector.

## Task scheduling metadata

Optional metadata is carried inside the committed task payload:

```json
{
  "_gremlin_scheduler": {
    "phase36": [0.0, "... exactly 36 values ..."],
    "ready": true,
    "readiness": 1.0,
    "temperature": 0.5,
    "urgency": 0.0,
    "noise": 0.1
  }
}
```

All scalar state fields are bounded to `[0,1]`. `phase36` must be exactly 36
finite values in `[0,2pi)`.

If `phase36` is absent, GREMLIN derives a deterministic locality-oriented
scheduling fingerprint from canonical payload tokens. Shared tokens contribute
the same per-axis phasors, so structurally related payloads tend to occupy
closer regions of `T^36`. This derived coordinate is explicitly a scheduling
fingerprint, not a semantic-truth claim.

Because scheduler metadata lives inside the committed payload, changes to it
change the task commitment. Persistence therefore does not create an
uncommitted scheduling side channel.

## Joint distance

For two task states `a,b`:

```text
D_state(a,b)
  = 0.76 * D_T36(a,b)
  + 0.14 * |temperature_a - temperature_b|
  + 0.10 * |readiness_a - readiness_b|
```

where `D_T36` is circular RMS phase distance normalized by `pi`.

A task with `ready=false` is ineligible for lease selection.

## Queue selection

Queue score combines:

```text
0.42 cluster coherence
0.20 information/noise term
0.14 mean readiness
0.10 maximum urgency
0.07 bounded backlog term
0.04 explicit-phase fraction
0.03 starvation-firewall age term
```

Cadence is not part of the primary score. For otherwise comparable queue scores,
legacy orbital cadence is only a secondary deterministic hint.

## Batch selection

The batch seed maximizes a bounded combination of centroid proximity,
information quality, readiness, urgency, explicit carrier resonance and a small
starvation firewall.

Following members maximize phase/state proximity to the previous selected
member while preserving task priority and low-noise preference.

The selected batch remains same-species.

## Geometry-adaptive lane

The vector lane is no longer a constant FIFO chunk. Queue coherence controls the
active width:

```text
width = vector_width * (0.50 + 1.50 * cluster_coherence)
```

rounded and bounded by worker `max_batch` and, for legacy Bestiary roles, the
existing orbital-lane ceiling.

Thus coherent work can be processed in wider batches while geometrically noisy
queues contract automatically.

## Worker roles

External geometry-scheduled worker roles are:

```text
SPIDER RAVEN HOUND MOLE OWL ANT MANTIS
FOX BEAVER BAT CANARY SERPENT CHAMELEON BELZEBUB
```

The following remain GREMLIN-root boundaries:

```text
HUMMINGBIRD  capture
OCTOPUS      routing
GREMLIN      aggregation/root
FERRET       explicit actuation boundary
```

## Receipts

Every lease returns a `scheduler` receipt containing:

- mode and schema;
- species queue metrics;
- selected task IDs;
- phase-source counts;
- selected phase/state transition cost;
- a FIFO transition-cost proxy over the same batch size;
- selected noise-cost proxy;
- FIFO noise-cost proxy;
- estimated payload-token volume;
- geometry lane width and legacy cap;
- `fifo_primary=false`.

These metrics are audit data, not authority.

## Token/noise claim discipline

v0.1 may report lower phase-transition and noise proxies relative to FIFO.

It MUST NOT claim real token savings until the same workload is measured through
an end-to-end worker/model path with actual tokenizer/accounting. Reduced phase
travel and increased within-batch coherence are engineering hypotheses for
context reuse, not proof of reduced billed/model tokens.

## Authority

Always:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
```

The scheduler does not alter FERRET authorization or NOEMA/PhaseNav native
authority.

## Validation gates

v0.1 requires:

- exact 36D phase validation;
- deterministic fallback phase fingerprints;
- `ready=false` exclusion;
- proof that FIFO is not used as primary selection;
- coherent-cluster selection against an older FIFO outlier;
- queue-geometry selection across registered species;
- geometry-adaptive lane contraction/expansion;
- transition/noise proxy comparison against FIFO;
- persistence and worker-ABI regression;
- standalone wheel and compiled-runtime import/self-test gates.
