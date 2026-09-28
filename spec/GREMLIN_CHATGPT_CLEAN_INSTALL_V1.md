# GREMLIN ChatGPT Clean-Account Bootstrap v1

**Schema:** `GREMLIN_CHATGPT_CLEAN_INSTALL_V1`  
**Status:** implementation candidate  
**Authority:** installation/readiness only; no canon promotion and no production actuation authority  
**OpenAI documentation rechecked:** 2026-09-28

## 1. Problem

GREMLIN previously had a local MCP installer and a Secure MCP Tunnel candidate, but no explicit clean-account ChatGPT admission contract. A fresh ChatGPT account could therefore inherit undocumented assumptions from an already-configured development environment.

This specification makes those assumptions explicit and fail-closed.

A clean account is defined as having no required dependency on:

- prior ChatGPT conversation history;
- ChatGPT Memory;
- NOEMA Library state;
- an existing GREMLIN account/session;
- previously registered GREMLIN tools.

## 2. Product boundary

ChatGPT does not directly connect to a local MCP server. GREMLIN must reach ChatGPT through one of two admitted transports:

```text
A. REMOTE HTTPS
GREMLIN MCP -> deployed HTTPS /mcp endpoint -> ChatGPT app/plugin

B. SECURE MCP TUNNEL
GREMLIN local stdio MCP -> tunnel-client -> OpenAI Secure MCP Tunnel -> ChatGPT app/plugin
```

The bootstrap does not create ChatGPT account permissions and does not silently infer them from another account.

Reference documentation:

- https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- https://developers.openai.com/plugins/build/app-quickstart

## 3. Admission state machine

```text
SURFACE
  -> DEVELOPER_MODE
  -> TRANSPORT
  -> APP_REGISTRATION
  -> TOOL_SCAN
  -> CAPABILITY_MODE
  -> READY
```

Every failed gate produces exactly one primary result:

```text
BLOCKED:<GATE_NAME>
```

and a concrete `next_action`.

### SURFACE

The operator must explicitly confirm the ChatGPT web surface.

The bootstrap does not claim that mobile ChatGPT can perform custom MCP/plugin onboarding.

### DEVELOPER_MODE

Developer mode must be explicitly confirmed for the clean account/workspace.

### TRANSPORT

Exactly one usable route must exist:

1. a structurally valid public `https://.../mcp` endpoint; or
2. a Secure MCP Tunnel plan whose existing GREMLIN tunnel gates pass.

Direct localhost, loopback, private-IP and plain HTTP endpoints fail closed.

### APP_REGISTRATION

The operator must explicitly confirm that GREMLIN has been created/registered in ChatGPT developer mode.

### TOOL_SCAN

`READY` is forbidden until the ChatGPT tool scan is explicitly recorded as `PASS`.

This prevents a successful local MCP process from being misreported as a successful ChatGPT installation.

### CAPABILITY_MODE

The actual account capability must be recorded as:

- `read`; or
- `full`.

The bootstrap intentionally does not infer capability from the user's previous account, plan history, prior sessions, or stale documentation.

## 4. CLI

Installed entry point:

```text
gremlin-chatgpt-clean
```

Blank clean-account probe:

```text
gremlin-chatgpt-clean --json
```

A blank environment is expected to return a blocker, not `READY`.

Remote HTTPS example:

```text
GREMLIN_CHATGPT_SURFACE=web
GREMLIN_CHATGPT_DEVELOPER_MODE=true
GREMLIN_CHATGPT_REMOTE_MCP_URL=https://example.invalid/mcp
GREMLIN_CHATGPT_APP_CREATED=true
GREMLIN_CHATGPT_TOOL_SCAN_STATUS=PASS
GREMLIN_CHATGPT_CAPABILITY_MODE=read
gremlin-chatgpt-clean --json
```

Secure MCP Tunnel reuses the existing variables:

```text
GREMLIN_OPENAI_TUNNEL_ID=tunnel_...
CONTROL_PLANE_API_KEY=...
```

and the existing `gremlin-openai-tunnel` admission model.

## 5. Security properties

- Runtime/control-plane secret values are never serialized by this bootstrap.
- Credentials embedded in a URL are rejected.
- HTTP endpoints are rejected.
- Local/private direct endpoints are rejected.
- A successful local GREMLIN process is not equivalent to successful ChatGPT installation.
- Tool scan PASS is mandatory for READY.
- Account capability is explicit rather than inferred.
- No NOEMA/Library dependency is permitted for clean-account admission.

## 6. Test contract

`tests/test_chatgpt_clean_install_v1.py` covers:

1. blank account fails closed;
2. hidden prior-state dependencies are false;
3. remote HTTPS path can reach READY;
4. READY is impossible before tool scan PASS;
5. localhost, private IP and HTTP are rejected;
6. `/mcp` path is required;
7. Secure MCP Tunnel can satisfy transport;
8. control-plane key is not emitted;
9. mobile surface fails closed;
10. capability is not inferred from another account.

The implementation was first exercised in an isolated local harness. Exact repository-head validation remains a separate evidence gate.
