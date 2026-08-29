# GREMLIN MCP Server v0.1

Status: CANDIDATE / standalone MCP adapter.

## Goal

Expose the existing GREMLIN Bestiary and reference prototype pipeline through the Model Context Protocol without requiring NOEMA, `/dev/shm/ciel_noema`, or native PhaseNav authority for discovery, scheduling, and reference experimentation.

The MCP adapter is intentionally fail-closed with respect to production authority:

```text
production_runtime_write = false
execution_admitted       = false
canon_allowed            = false
```

It is therefore an integration surface, not a replacement for the native authority path.

## Topology exposed to MCP clients

```text
RAW
 -> HUMMINGBIRD  fast append-only capture
 -> OCTOPUS      route mask + bounded semantic fanout
 -> {SPIDER      relation/dependency/isomorphism scan
     RAVEN       memory/similarity scan
     HOUND       contradiction/anomaly/test-target scan
     MOLE        deep local derivation
     OWL         epistemic audit
     ANT         bounded combinatorial scan
     MANTIS      duplicate/dead-branch pruning}
 -> BELZEBUB     defensive candidate synthesis
 -> GREMLIN      aggregate verified heads / research candidates
```

Scheduler profiles use the existing mass-orbit relation:

```text
omega = omega0 * tau / sqrt(m * r^3)
omega0 = 2*pi*7.83
```

Vector lane plans reuse `tools/gremlin_bestiary_vector_species_v03.py`; the MCP layer does not duplicate scheduler semantics.

## MCP tools

### `gremlin_status`

Returns adapter version, topology, supported transports and authority state.

### `gremlin_bestiary`

Returns every Bestiary role plus scheduler mass, radius, cadence `omega`, and service period where a scheduler profile exists.

### `gremlin_species`

Returns one named Bestiary role and its scheduler profile.

### `gremlin_plan`

Input:

```json
{
  "route_counts": {
    "SPIDER": 64,
    "HOUND": 32,
    "OWL": 16,
    "BELZEBUB": 64
  },
  "vector_width": 8
}
```

Returns deterministic lane widths, batch counts, cadence ordering and dispatch compression using the existing GREMLIN scheduler.

### `gremlin_prototype`

Delegates to `tools/gremlin_client_protocol_v01.py` and preserves its existing candidate -> PhaseNav IR -> untrusted reference prototype -> experiment receipt pipeline.

The tool cannot request production execution admission or canon promotion.

## Installation

From the repository root:

```text
python -m pip install -e .
```

The package pins the current MCP Python SDK major line:

```text
mcp>=2,<3
```

## stdio transport

Default:

```text
gremlin-mcp
```

Equivalent explicit invocation:

```text
gremlin-mcp --transport stdio
```

Example MCP host entry:

```json
{
  "mcpServers": {
    "gremlin": {
      "command": "gremlin-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

## Streamable HTTP transport

Local endpoint:

```text
gremlin-mcp --transport streamable-http --host 127.0.0.1 --port 8766
```

Default MCP URL:

```text
http://127.0.0.1:8766/mcp
```

Network exposure, authentication, TLS, reverse-proxy policy and commercial/production deployment are deliberately outside v0.1. The default documented HTTP binding is loopback only.

## Standalone boundary

The following operations are standalone in v0.1:

- MCP discovery and handshake;
- Bestiary topology inspection;
- species scheduler inspection;
- deterministic mass-orbit/vector lane planning;
- existing Python reference prototype pipeline.

Native 36D authority remains on the established NOEMA/PhaseNav execution path and is not silently emulated by this MCP server.

## CI gate

`tests/test_gremlin_mcp_v01.py` verifies:

- fail-closed standalone status;
- complete Bestiary manifest;
- deterministic vector lane planning;
- an in-process MCP v2 handshake;
- discovery of all five GREMLIN MCP tools;
- successful invocation of `gremlin_status` through an MCP client.

Workflow: `.github/workflows/gremlin-mcp-v01.yml`.
