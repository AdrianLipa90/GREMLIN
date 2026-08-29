# GREMLIN BESTIARY v0.1/v0.2

Status: CANDIDATE / deterministic topology threshold crossed; live 5-CPU >=10x promotion threshold not met.

## Goal

Increase idea-ingest and research throughput by separating capture, routing, specialist analysis and synthesis. The target for candidate promotion is >=10x throughput relative to a monolithic generalist path on the same frozen workload.

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
     ANT         bounded combinatorial scan
     MANTIS      duplicate/dead-branch pruning}
 -> BELZEBUB     defensive candidate synthesis
 -> GREMLIN      aggregate verified heads
```

HUMMINGBIRD does not interpret. Specialist outputs remain candidates. GREMLIN remains root aggregate authority. Canon promotion is outside this topology.

## Deterministic topology benchmark

`tools/gremlin_bestiary_bench_v01.py` generates 10,000 deterministic input items with seed 616. The monolithic baseline performs all seven specialist transforms serially; OCTOPUS routes each item only to 3-5 declared relevant specialist transforms.

| Topology | MOLE workers | BELZEBUB workers | Speedup |
|---|---:|---:|---:|
| one worker per species | 1 | 1 | 6.7135x |
| duplicate synthesis only | 1 | 2 | 9.9704x |
| duplicate deep-dig + synthesis | 2 | 2 | 13.2240x |

Default candidate topology crosses the predeclared >=10x virtual-service threshold at ~13.2240x. This remains a topology/model result only.

## Live same-runtime replay v0.1

`tools/gremlin_bestiary_live_bench_v02.py` replayed one frozen RAW workload through legacy serial, a resource-matched 5-worker generalist, and the routed Bestiary on `/dev/shm/ciel_noema`.

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
```

Receipt: `provenance/GREMLIN_BESTIARY_LIVE_WALLCLOCK_V0_2.json`.

## v0.2 mass-orbit-frequency scheduler

The next scheduler assigns every Bestiary species a scheduler mass `m`, orbital radius `r`, and cadence band:

```text
omega = omega0 * tau / sqrt(m * r^3)
omega0 = 2*pi*7.83
```

This relation is an internal scheduling relation. It controls service cadence/batching and does not assert an astronomical dynamics law.

HUMMINGBIRD is Mercury-like: low mass, inner orbit, very high cadence. BELZEBUB is Jupiter-like: high mass, outer orbit, low cadence and large synthesis batches. OCTOPUS keeps semantic routing, while the orbital layer controls when/how much work is admitted to resident workers.

Native authority declaration: `native/GREMLIN_BESTIARY_MASS_ORBIT_SCHEDULER_V0_2.pnv`.
Reference scheduler: `tools/gremlin_bestiary_orbital_scheduler_v02.py`.
Live harness: `tools/gremlin_bestiary_orbital_live_v03.py`.

## Live orbital replay

A fresh tether guard returned `ACTIVE` with no failures. The exact frozen v0.1 workload hash was replayed again on the visible 5-CPU runtime.

```text
legacy serial                 = 213.5149 items/s
resource-matched generalist   = 564.9639 items/s
Bestiary individual dispatch  = 921.8725 items/s
Bestiary orbital/batched      = 1020.6460 items/s

orbital / legacy              = 4.7802x
orbital / matched generalist  = 1.8066x
orbital / old Bestiary        = 1.1071x

orbital chunk size            = 54
orbital batches               = 38
old Bestiary queue depth      = 2000
orbital queue depth           = 38
old Bestiary CPU              = 8.6717 s
orbital CPU                   = 7.5586 s
old Bestiary p95              = 2088.87 ms
orbital p95                   = 1921.92 ms

lineage integrity             = PASS
output equivalence            = PASS
dropped objects               = 0
output mismatches              = 0
```

Receipt: `provenance/GREMLIN_BESTIARY_ORBITAL_LIVE_V0_3.json`.

The mass-orbit scheduler therefore improved the already-routed live Bestiary by ~10.7%, while reducing scheduler queue depth from 2000 to 38 and CPU consumption by ~12.8% on this replay.

## Five-CPU scalar ceiling

For the frozen scalar cost model, the serial path performs 8600 work units/item. The routed path has expected specialist cost

```text
(23/6) * (7300/7) + 1300 ~= 5297.62 work units/item.
```

With five workers, the ideal zero-overhead scalar ceiling is therefore

```text
5 * 8600 / 5297.62 ~= 8.1169x.
```

So the predeclared live >=10x gate cannot be reached on this 5-worker benchmark merely by improving scalar scheduling. Crossing 10x requires an additional execution gain such as native PhaseNav execution, SIMD/vector batching, lower-cost specialist transforms, or a larger verified hardware parallelism budget.

The architecture remains CANDIDATE. The next gate should preserve the same frozen workload and test orbital scheduling with native/vector specialist batches while retaining lineage and output-equivalence checks.
