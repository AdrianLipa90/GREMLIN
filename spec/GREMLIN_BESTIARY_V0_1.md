# GREMLIN BESTIARY v0.1

Status: CANDIDATE / deterministic topology threshold crossed; live 5-CPU promotion threshold not met.

## Goal

Increase idea-ingest and research throughput by separating capture, routing, specialist analysis and synthesis. The target for candidate promotion is >=10x throughput relative to a monolithic generalist path on the same deterministic workload.

## Topology

```text
RAW
 -> HUMMINGBIRD  fast append-only capture
 -> OCTOPUS      route mask + bounded fanout
 -> {SPIDER      relation/isomorphism scan
     RAVEN       memory/similarity scan
     HOUND       contradiction/anomaly scan
     MOLE        deep local derivation
     OWL         epistemic audit
     ANT         bounded combinatorial search
     MANTIS      duplicate/dead-branch pruning}
 -> BELZEBUB     defensive candidate synthesis
 -> GREMLIN      aggregate verified heads
```

HUMMINGBIRD does not interpret. Specialist outputs remain candidates. GREMLIN remains root aggregate authority. Canon promotion is outside this topology.

## Deterministic topology benchmark

`tools/gremlin_bestiary_bench_v01.py` generates 10,000 deterministic input items with seed 616.

For every item, the monolithic baseline performs all seven specialist transforms serially. The Bestiary router selects 3-5 relevant specialist queues and executes them concurrently, followed by BELZEBUB synthesis.

Service costs are deterministic virtual units. This benchmark measures scheduling/topology throughput; it is not a live wall-clock or hardware benchmark.

| Topology | MOLE workers | BELZEBUB workers | Speedup |
|---|---:|---:|---:|
| one worker per species | 1 | 1 | 6.7135x |
| duplicate synthesis only | 1 | 2 | 9.9704x |
| duplicate deep-dig + synthesis | 2 | 2 | 13.2240x |

Default candidate topology crosses the predeclared >=10x virtual-service threshold at ~13.2240x.

## Live same-runtime replay

`tools/gremlin_bestiary_live_bench_v02.py` replays one frozen RAW workload through three paths on `/dev/shm/ciel_noema`:

1. legacy monolithic serial generalist;
2. resource-matched generalist with the same process-worker budget as Bestiary;
3. Bestiary with OCTOPUS routing to only the 3-5 declared relevant specialist transforms.

Run recorded in `provenance/GREMLIN_BESTIARY_LIVE_WALLCLOCK_V0_2.json`:

```text
items                      = 2000
seed                       = 616
visible CPU count          = 5
workers                    = 5
frozen RAW sha256          = 7156342a021d71bf8b710042cc7cc69724d344d20bc79972766f8d18a4538584

legacy serial              = 212.5227 items/s
resource-matched generalist= 578.5577 items/s
Bestiary                   = 948.0248 items/s

Bestiary / legacy serial   = 4.4608x
Bestiary / matched         = 1.6386x

lineage integrity          = PASS
output equivalence         = PASS
dropped objects            = 0
duplicate input IDs        = 0
```

End-to-end p50/p95 latency:

```text
legacy serial              = 4612.13 / 8974.18 ms
resource-matched generalist= 1798.28 / 3296.73 ms
Bestiary                   = 1062.61 / 1989.70 ms
```

The live >=10x promotion gate is therefore **not met** on the current 5-CPU runtime. The measured operational gain versus the legacy serial path is ~4.46x; routing/specialization alone gives ~1.64x against an equally parallel generalist.

This result preserves the architecture as a candidate but blocks promotion on the current evidence. Further work should target bounded queueing, lower process/serialization overhead, native PhaseNav execution, and specialist batching/vectorization before repeating the same frozen-workload gate.
