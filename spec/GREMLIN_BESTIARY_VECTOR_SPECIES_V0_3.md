# GREMLIN BESTIARY VECTOR SPECIES v0.3

Status: CANDIDATE.

v0.2 proved that mass-orbit-frequency scheduling reduces queue depth and improves live throughput, but the frozen five-worker scalar benchmark has an ideal ceiling below the >=10x promotion gate. v0.3 therefore changes the execution unit from one candidate to a bounded same-operator vector lane.

Pipeline:

```text
RAW
 -> HUMMINGBIRD capture
 -> OCTOPUS semantic route mask
 -> mass/orbit/frequency scheduler
 -> group by specialist operator
 -> bounded vector lanes / structure-of-arrays
 -> resident specialist execution
 -> BELZEBUB heavy synthesis batches
 -> GREMLIN aggregate
```

The lane planner uses the existing orbital cadence. Fast inner-orbit species keep smaller latency-oriented batches; slower/heavier outer species receive wider lanes to amortize dispatch/serialization overhead.

Reference planner: `tools/gremlin_bestiary_vector_species_v03.py`.
Native contract: `native/GREMLIN_BESTIARY_VECTOR_SPECIES_V0_3.pnv`.

Current focused validation: 5/5 PASS covering orbital lane ordering, route-count conservation, bounded batch coverage, dispatch compression and fail-closed unknown species handling.

This layer does not yet claim a >=10x live wall-clock result. The next empirical gate is an exact-output replay of the frozen v0.2 RAW workload on `/dev/shm/ciel_noema`, comparing individual dispatch, orbital item batches and species-resident vector batches under the same hardware budget.
