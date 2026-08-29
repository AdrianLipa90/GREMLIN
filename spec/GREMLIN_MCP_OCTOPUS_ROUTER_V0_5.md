# GREMLIN MCP OCTOPUS Semantic Router v0.5

Status: reference standalone MCP implementation.

## Purpose

OCTOPUS converts one finite JSON research payload into a bounded specialist route mask for the GREMLIN Bestiary.

```text
payload
  -> OCTOPUS semantic evidence scan
  -> ranked specialist scores
  -> bounded route mask
  -> optional auto-fanout
```

The implementation in `gremlin_mcp/router.py` is deterministic, dependency-free and auditable. It does not use an opaque language model or embeddings. Every positive score is accompanied by evidence identifying the matched semantic cue or structural payload key.

This realizes the existing native topology declaration:

```text
OP OCTOPUS.ROUTE TRANSFORM HUMMINGBIRD.CAPTURE semantic_route_mask
OP OCTOPUS.FANOUT COMPOSITION OCTOPUS.ROUTE bounded_parallel_fanout
```

for the standalone MCP reference path. It does not grant native 36D execution authority.

## Specialist targets

OCTOPUS may route to:

- `SPIDER` — relations, graphs, dependencies, isomorphisms and topology;
- `RAVEN` — memory, history, prior/similar structures;
- `HOUND` — contradictions, anomalies, errors, tests and falsification targets;
- `MOLE` — derivations, equations, proofs and deep local calculation;
- `OWL` — evidence, provenance, claims and epistemic audit;
- `ANT` — bounded enumeration, combinations and search surfaces;
- `MANTIS` — duplicate, redundant and dead-branch pruning.

BELZEBUB remains a downstream synthesis role and is not selected by OCTOPUS specialist routing.

## Route decision

`gremlin_route(payload, max_species=4, min_score=2.0, relative_cutoff=0.45)` returns:

- deterministic per-species scores;
- evidence for every score contribution;
- a bounded `route_mask`;
- the effective threshold;
- payload structural statistics;
- a BLAKE2b-256 `route_commitment`;
- fail-closed authority state.

The selection threshold is:

```text
threshold = max(min_score, top_score * relative_cutoff)
```

Only positive scores at or above the threshold can enter the route mask, up to `max_species`.

## Fail-closed no-route behavior

When no lexical or structural evidence reaches the threshold:

```text
status = NO_CONFIDENT_ROUTE
route_mask = []
```

`gremlin_auto_fanout` then returns:

```text
status = NO_CONFIDENT_ROUTE_NOT_QUEUED
```

and queues no worker task. The router does not silently invent a generic specialist.

## Auto-fanout lineage

`gremlin_auto_fanout` binds the route decision to downstream worker tasks:

```text
payload
  -> route_commitment
  -> route_mask
  -> fanout route_context
  -> task commitment
```

Every automatically queued specialist task carries:

```json
{
  "route_context": {
    "router_schema": "GREMLIN_MCP_OCTOPUS_ROUTER_V0_5",
    "router_version": "0.5.0",
    "route_commitment": "...",
    "route_mask": ["..."]
  }
}
```

This makes the routing decision part of task lineage instead of an untracked pre-processing step.

## MCP tools

Two tools are added:

- `gremlin_route` — inspect the OCTOPUS decision without queueing work;
- `gremlin_auto_fanout` — route and queue only when positive evidence exists.

The existing `gremlin_fanout` remains available for an explicit caller-supplied route mask.

## Authority boundary

Every OCTOPUS v0.5 result preserves:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

The standalone semantic router produces scheduling decisions and candidate lineage only.

## Validation requirements

CI must verify at minimum:

1. deterministic route commitments for identical inputs;
2. graph/dependency payloads route to SPIDER;
3. derivation/equation payloads route to MOLE;
4. multi-domain inputs can route to multiple specialists;
5. no-evidence payloads queue nothing;
6. auto-fanout embeds the route commitment into worker task lineage;
7. MCP discovery exposes both OCTOPUS tools.
