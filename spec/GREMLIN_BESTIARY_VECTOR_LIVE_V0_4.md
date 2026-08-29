# GREMLIN Bestiary vector-species live replay v0.4

Status: CANDIDATE / live replay complete; >=10x promotion gate not met.

The merged v0.3 species-lane planner was replayed on the same frozen 2,000-item workload used by Bestiary v0.2.

Frozen RAW SHA-256:

`7156342a021d71bf8b710042cc7cc69724d344d20bc79972766f8d18a4538584`

Runtime surface: `/dev/shm/ciel_noema`.

Visible CPU budget: 5 workers.

## Paths

1. legacy serial generalist;
2. resource-matched 5-worker generalist;
3. routed per-item Bestiary;
4. orbital item batching;
5. species-resident vector-lane batching.

Species vector execution groups identical operators before dispatch. Lane width is derived from the existing mass/orbit/frequency profile: fast inner-orbit species retain smaller latency-oriented lanes while slower/heavier outer-orbit species accumulate wider lanes. BELZEBUB is batched separately after all routed specialist outputs are complete.

## Live result

```text
legacy serial                 229.4080 items/s
resource-matched generalist   620.8588 items/s
routed per-item Bestiary     1054.8850 items/s
orbital item batching        1049.3343 items/s
species vector lanes         1129.0755 items/s

vector / legacy                 4.9217x
vector / matched generalist     1.8186x
vector / old Bestiary           1.0703x
vector / orbital item batch     1.0760x
```

Dispatch compression for routed specialist work was ~32.2563x. Species dispatch count was 238 instead of per-route per-item dispatch. BELZEBUB used 16 batches at lane width 128.

Integrity:

```text
dropped objects             0
duplicate input IDs         0
output mismatches           0
lineage integrity           PASS
output equivalence          PASS
```

The species-lane architecture therefore improves the live v0.3 execution path while preserving exact output equivalence, but the measured throughput remains below the predeclared 10x promotion threshold.

## Bottleneck identified

The frozen replay kernel intentionally uses repeated scalar BLAKE2b transforms as deterministic stand-ins for specialist work. Batching reduces dispatch and serialization overhead, but it does not make those sequential per-item hash chains SIMD-vectorizable while preserving exact output equivalence. The remaining runtime is therefore dominated by unchanged scalar transform cost.

The next gate should benchmark the same orbital/species scheduler against an actually vectorizable PhaseNav operator kernel, with scalar and vector forms computing the same numerical operator and checked within a predeclared tolerance. That separates scheduler gain from executable vector-kernel gain without changing semantic workload after observing results.

Harness: `tools/gremlin_bestiary_vector_live_v04.py`.
Receipt: `provenance/GREMLIN_BESTIARY_VECTOR_LIVE_V0_4.json`.
