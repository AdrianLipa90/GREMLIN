# GREMLIN ChatGPT Clean Install v1

**Schema:** `GREMLIN_CHATGPT_CLEAN_INSTALL_V1`  
**Status:** implementation candidate  
**Date:** 2026-09-28  
**Authority:** packaging and transport admission only; no canon promotion or production actuation authority

## Goal

A GREMLIN package created by this path must be usable from a ChatGPT account with no prior GREMLIN conversation, ChatGPT Memory, Library state, NOEMA state, local MCP configuration, or local GREMLIN process.

This path is deliberately separate from the desktop/stdio installer.

## Architecture

```text
GREMLIN runtime
    |
stable remote HTTPS Streamable HTTP MCP endpoint
    |
portable Agent Plugin package
    |-- plugin.json
    |-- mcp.json
    '-- skills/gremlin/SKILL.md
    |
ChatGPT plugin registration / installation
    |
Scan Tools + permission review + tool discovery
    |
HOST-VERIFIED INSTALL
```

The generated package never points at localhost, RFC1918/private IP space, `.local`, a non-HTTPS endpoint, or an endpoint URL carrying query parameters or embedded credentials.

## Admission model

```text
CLEAN_ACCOUNT
  -> PORTABLE_PLUGIN
  -> REMOTE_MCP
  -> PACKAGE_SELF_INSPECTION
  -> PACKAGE_READY
  -> CHATGPT_HOST_ADMISSION [external]
  -> HOST-VERIFIED INSTALL
```

The repository can deterministically verify package construction and the static remote-endpoint contract.

The repository cannot truthfully mark the ChatGPT host gate as PASS on its own. Account/workspace eligibility, Developer Mode, plugin registration, authentication, Scan Tools, permission review, and successful tool discovery are host-side facts.

Therefore `PACKAGE_READY` MUST NOT be renamed or interpreted as `READY` for the complete installation.

## Current OpenAI transport contract

The portable package follows the current Agent Plugins layout:

```text
plugin.json
mcp.json
skills/gremlin/SKILL.md
```

`mcp.json` declares:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "gremlin": {
      "type": "streamable-http",
      "url": "https://example.invalid/mcp"
    }
  }
}
```

The concrete endpoint must be a real remotely reachable HTTPS MCP endpoint ending in `/mcp`.

GREMLIN also retains the separate Secure MCP Tunnel integration in `gremlin_mcp/openai_tunnel.py`. Tunnel-backed ChatGPT registration is a distinct host-binding path; v1 of this portable ZIP builder does not fabricate a tunnel URL or a ChatGPT registration ID.

## CLI

Inspect the packaging plan:

```text
gremlin-chatgpt-package --plan \
  --endpoint https://gremlin.example/mcp \
  --json
```

Build a portable ZIP:

```text
gremlin-chatgpt-package --build \
  --endpoint https://gremlin.example/mcp \
  --output GREMLIN-ChatGPT-Plugin-v1.zip \
  --json
```

A successful build returns:

```text
PACKAGE_READY
NEXT_REQUIRED_GATE: CHATGPT_HOST_ADMISSION
```

Inspect an existing artifact:

```text
gremlin-chatgpt-package --inspect GREMLIN-ChatGPT-Plugin-v1.zip --json
```

Without a remote endpoint the builder fails closed with:

```text
BLOCKED
REMOTE_ENDPOINT_REQUIRED
```

## Clean-account invariants

The package MUST NOT require:

- prior ChatGPT conversation history;
- ChatGPT Memory;
- ChatGPT Library files;
- `/dev/shm/ciel_noema`;
- local `stdio` reachability from the ChatGPT account;
- localhost, link-local, private-network, or `.local` endpoints;
- a previously installed GREMLIN client configuration;
- credentials embedded in an MCP URL;
- a query-token URL masquerading as an installation mechanism.

NOEMA/PhaseNav may exist behind a deployed GREMLIN service. They are server-side implementation details, not prerequisites stored in the clean ChatGPT account.

## Portable package contract

The ZIP is intentionally minimal and exact:

```text
plugin.json
mcp.json
skills/gremlin/SKILL.md
```

Self-inspection rejects:

- missing or unexpected archive paths;
- duplicate or traversal-style archive paths;
- wrong Agent Plugins schema;
- wrong MCP schema;
- non-`streamable-http` transport;
- invalid/non-HTTPS/private MCP endpoints;
- a GREMLIN skill that reintroduces localhost or `/dev/shm` account dependencies.

The bundled GREMLIN skill requires the model to:

1. call `gremlin_status` when available;
2. fail closed if GREMLIN is unavailable;
3. preserve receipts and candidate/authority distinctions;
4. prefer OCTOPUS routing for automatic decomposition;
5. never replace a missing GREMLIN connection with a prompt-only simulation.

## ChatGPT host gate

After `PACKAGE_READY`, an eligible ChatGPT host still has to perform the real host-side work:

1. enable the relevant Developer Mode / plugin installation capability for the account or workspace;
2. register or install the GREMLIN MCP/plugin;
3. run Scan Tools or the equivalent host discovery step;
4. review the exposed tool set and requested permissions;
5. open a fresh chat/session and verify that GREMLIN tools are actually discoverable and callable.

A successful ZIP build is not evidence that any of these steps passed.

## Validation target

The clean-account release test is successful only when the same GREMLIN build can be taken to a genuinely fresh eligible ChatGPT account and the account reaches the host-verified state without relying on prior conversation state, Memory, Library, or a pre-existing GREMLIN connection.

This manual/host E2E result should be recorded separately from unit/package tests.

## Evidence

Reference implementation: `gremlin_mcp/chatgpt_clean_install.py`.

Tests: `tests/test_chatgpt_clean_install_v1.py`.

The v1 tests cover:

- missing endpoint fail-closed behavior;
- rejection of HTTP, localhost, private IPs, wrong paths, and query-token URLs;
- accepted public HTTPS `/mcp` endpoint;
- current portable MCP schema and `streamable-http` transport;
- self-contained ZIP generation and self-inspection;
- explicit external ChatGPT host gate;
- wrong transport rejection;
- overwrite refusal.

## External references used for this contract

Verified against current OpenAI documentation on 2026-09-28:

- OpenAI Plugins: Package your plugin.
- OpenAI Plugins: Build an MCP server.
- OpenAI Plugins: Connect and test your plugin.
- OpenAI API: Secure MCP Tunnel.

These host requirements can change; exact-head GREMLIN validation must not substitute historical documentation for a fresh host-side install test.


## Unified preflight

The operator does not need to guess which ChatGPT transport path is viable.

```text
gremlin-chatgpt-install-check --json
```

checks both supported paths without exposing secrets:

```text
REMOTE_HTTPS_MCP
SECURE_MCP_TUNNEL
```

An optional remote endpoint may be supplied:

```text
gremlin-chatgpt-install-check \
  --endpoint https://gremlin.example/mcp \
  --json
```

Possible top-level states are:

- `PACKAGE_READY` — the portable remote-MCP package path is statically ready;
- `TUNNEL_PREREQUISITES_READY` — the Secure MCP Tunnel prerequisites are present, but tunnel `init` + `doctor` and ChatGPT host admission still have to pass;
- `BLOCKED` — neither route is ready, with per-route blocker details.

The remote path has deterministic precedence when both paths are available. Neither of the first two states implies `CHATGPT_HOST_ADMISSION=PASS`.

Reference implementation: `gremlin_mcp/chatgpt_install_preflight.py`.

Tests: `tests/test_chatgpt_install_preflight_v1.py`.
