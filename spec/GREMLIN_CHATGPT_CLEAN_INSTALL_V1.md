# GREMLIN ChatGPT Clean Install v1

**Schema:** `GREMLIN_CHATGPT_CLEAN_INSTALL_V1`  
**Status:** implementation candidate  
**Date:** 2026-09-28  
**Authority:** packaging and transport admission only; no canon promotion or production actuation authority

## Goal

A GREMLIN plugin package created by this path must be installable on a ChatGPT account that has no prior GREMLIN conversation, Memory, Library state, NOEMA state, local MCP configuration, or local GREMLIN process.

The clean-account path is therefore deliberately separate from the desktop/stdio installer.

## Architecture

```text
GREMLIN runtime
    |
public HTTPS remote MCP OR OpenAI Secure MCP Tunnel endpoint
    |
portable Agent Plugin package
    |-- plugin.json
    |-- mcp.json
    '-- skills/gremlin/SKILL.md
    |
ChatGPT plugin install / publish surface
    |
Scan Tools / host admission
    |
READY
```

The generated package never points at localhost, RFC1918/private IP space, `.local`, or a non-HTTPS endpoint.

## Admission

```text
CLEAN_ACCOUNT
  -> PORTABLE_PLUGIN
  -> REMOTE_MCP
  -> PACKAGE_SELF_INSPECTION
  -> HOST_SCAN_TOOLS
  -> READY
```

The repository can deterministically verify the first four gates. Host-side account permissions, authentication, Scan Tools, publication, and user confirmation remain external gates and must not be reported as PASS until the host actually confirms them.

## CLI

Build a portable ZIP only after a remotely reachable MCP endpoint exists:

```text
gremlin-chatgpt-package --build \
  --endpoint https://gremlin.example/mcp \
  --output GREMLIN-ChatGPT-Plugin-v1.zip \
  --json
```

Inspect a generated ZIP:

```text
gremlin-chatgpt-package --inspect GREMLIN-ChatGPT-Plugin-v1.zip --json
```

Without an endpoint the builder fails closed with:

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
- a local `stdio` MCP process;
- localhost or private-network reachability;
- a previously installed GREMLIN client configuration.

NOEMA/PhaseNav may still exist behind the deployed GREMLIN service. They are server-side implementation details, not prerequisites stored in the new ChatGPT account.

## Portable plugin contract

The package uses the current portable Agent Plugins root manifest:

```text
plugin.json
mcp.json
skills/gremlin/SKILL.md
```

The MCP declaration uses HTTP transport and an HTTPS URL ending in `/mcp`.

The bundled GREMLIN skill requires the model to:

1. probe `gremlin_status` when available;
2. fail closed if GREMLIN is unavailable;
3. preserve receipts and candidate/authority distinctions;
4. prefer OCTOPUS routing for automatic decomposition;
5. never replace a missing GREMLIN connection with a prompt-only simulation.

## External host boundary

Building the ZIP does not install it into a ChatGPT account and does not create a remote MCP deployment.

The remaining deployment requirement is a stable remotely reachable GREMLIN MCP endpoint or a supported Secure MCP Tunnel endpoint. After that endpoint exists, the package can be generated without account-specific conversational state.

## Evidence

Reference implementation: `gremlin_mcp/chatgpt_clean_install.py`.

Tests: `tests/test_chatgpt_clean_install_v1.py`.

The v1 test suite covers missing endpoint, HTTP rejection, localhost/private-address rejection, wrong MCP path rejection, accepted public HTTPS endpoint, self-contained ZIP generation/self-inspection, and overwrite refusal.
