# GREMLIN Authority Direction Repair — 2026-10-07

Status: **TARGETED PASS / MAIN UNTOUCHED / CANONICAL ONECLICK REFRESH NOT PROMOTED**

## Root cause

The native GREMLIN contract predates the standalone MCP adapter and grants bounded internal execution/write authority. The standalone MCP v0.1 adapter later encoded default request admission as global-looking fields:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Those values were subsequently propagated across live system surfaces and could be interpreted as GREMLIN lacking capability rather than an unadmitted AI/MCP request lacking permission.

## Repaired invariant

```text
OPERATOR > GREMLIN > AI_CLIENT

GREMLIN_SUPERVISION               ACTIVE
GREMLIN_INTERNAL_EXECUTION        ACTIVE
GREMLIN_INTERNAL_WRITE            ACTIVE_BOUNDED
EXTERNAL_MUTATION_CAPABILITY      AVAILABLE_CONDITIONAL
CANON_PROMOTION_CAPABILITY        AVAILABLE_CONDITIONAL

AI_SELF_AUTHORIZATION             FALSE
AI_OVERRIDE_GREMLIN               FALSE
MCP_SELF_GRANTS_AUTHORITY         FALSE
```

External effect admission remains exact and fail-closed through RAPHAEL, the Mathematical Constitution, ACTIVE tether/same-generation attestation and operator admission.

## Provenance

- repair base main: `1b46b425e6170612e67a96dac21ca7aa6c24e6ac`
- first MCP contract with ambiguous global denial: `d3e17e7121793eb7b8376e4a120e3f5cdc9d82d5`
- first MCP core implementation: `b7928b5cfa43575c6c04f6b4d8fa08be24780879`
- native authority reference: `c029eb8a48514080afaf320ba9b6c1aa53fe2111`

## Validation

- exact-branch static audit: PASS
- local `compileall`: PASS
- local authority/gateway/RAPHAEL/worker/web/Hive tests: **67/67 PASS**
- MCP discovery test: NOT RUN because the local runner lacks the Python `mcp` package
- full-repository pytest: NOT CLAIMED

A pre-existing continuation-routing defect was independently reproduced on the clean 2026-10-06 Library snapshot and repaired on this branch.

## Local GREMLIN receipt

The live local GREMLIN host itself wrote the authority-direction overlay using `gremlin_local_patch`.

Receipt:

`702df93b0fa4ac2b04a19a5b2c081c4fe53c358af22e7aaaf405c317a2cfddf0`

Generation:

`5289fedcae85ebfcfc69d538f6b519033781074a48574d11e7768d5f89d40a7f`

## Canonical one-click boundary

The current canonical one-click bundle contains the old adapter metadata in these embedded source files:

- `payload/adapter/gremlin_mcp_stdio.py`
- `payload/autoboot/noema_tether_autoboot_latest.py`
- `payload/pncs/GREMLIN_SCOPED_AUTOREPAIR_AUTHORITY_V0_1.pnv`

The PNV operations themselves are request-scoped; the problem is the global-looking metadata/serialization. The canonical bundle has **not** been silently overwritten. A source-refresh/promotion of the one-click bundle is required to make the repaired semantics permanent across fresh boots.
