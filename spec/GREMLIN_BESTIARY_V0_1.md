# GREMLIN BESTIARY v0.1

Status: CANDIDATE / benchmarked in deterministic virtual-service topology only.

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

## Benchmark model

`tools/gremlin_bestiary_bench_v01.py` generates 10,000 deterministic input items with seed 616.

For every item, the monolithic baseline performs all seven specialist transforms serially. The Bestiary router selects 3-5 relevant specialist queues and executes them concurrently, followed by BELZEBUB synthesis.

Service costs are deterministic virtual units. The benchmark measures scheduling/topology throughput; it is not a live wall-clock or hardware benchmark.

### Results

| Topology | MOLE workers | BELZEBUB workers | Speedup |
|---|---:|---:|---:|
| one worker per species | 1 | 1 | 6.7135x |
| duplicate synthesis only | 1 | 2 | 9.9704x |
| duplicate deep-dig + synthesis | 2 | 2 | 13.2240x |

Default candidate topology therefore crosses the predeclared >=10x threshold:

```text
HUMMINGBIRD 1
OCTOPUS     1
SPIDER      1
RAVEN       1
HOUND       1
MOLE        2
OWL         1
ANT         1
MANTIS      1
BELZEBUB    2
```

Deterministic benchmark values for 10,000 items / seed 616:

```text
baseline_serial_service_units  ~= 87344.1756
bestiary_makespan_service_units ~= 6604.9702
throughput_speedup              ~= 13.2240x
candidate_threshold              = 10.0x
candidate                        = true
```

## Why the result can exceed worker-count scaling

The topology combines two effects: parallel service and avoided generalist work. OCTOPUS routes each item only to relevant specialists instead of forcing every item through every transform. The benchmark reports the combined topology gain and separately exposes worker counts.

## Next gate

A live candidate requires replaying one frozen RAW workload through both paths on the same runtime generation and hardware budget:

```text
MONOLITHIC GREMLIN replay
vs
BESTIARY replay
```

Required measurements: accepted items/s, p50/p95 end-to-end latency, total CPU time, peak RSS, queue depth, dropped/duplicated object count, lineage integrity and output-equivalence class. Promotion requires >=10x accepted-item throughput without lineage loss or weaker fail-closed behavior.
