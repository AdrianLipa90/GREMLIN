# GREMLIN on a clean ChatGPT account

This path is intentionally independent of prior chat history, ChatGPT Memory, NOEMA Library state, and any previously connected GREMLIN instance.

## 1. Install GREMLIN locally

Install the GREMLIN package/product as normal. The ChatGPT clean-account CLI is:

```text
gremlin-chatgpt-clean --json
```

On a truly blank setup, `BLOCKED:...` is expected. Follow the returned `next_action`.

## 2. Use ChatGPT on the web

Custom MCP/plugin onboarding must be performed from a supported ChatGPT web surface. Do not treat the mobile app as equivalent for this setup.

Record:

```text
GREMLIN_CHATGPT_SURFACE=web
```

## 3. Enable developer mode

Enable developer mode for the target clean account/workspace, then record:

```text
GREMLIN_CHATGPT_DEVELOPER_MODE=true
```

GREMLIN never copies this state from another account.

## 4. Choose one MCP transport

### Remote HTTPS

Deploy GREMLIN as a remotely reachable HTTPS MCP endpoint ending in `/mcp`, then set:

```text
GREMLIN_CHATGPT_REMOTE_MCP_URL=https://your-host.example/mcp
```

Direct localhost, loopback, private-IP and HTTP URLs are rejected.

### Secure MCP Tunnel

Keep GREMLIN local and use the existing tunnel path:

```text
GREMLIN_OPENAI_TUNNEL_ID=tunnel_...
CONTROL_PLANE_API_KEY=...
gremlin-openai-tunnel --setup --json
```

The clean-account bootstrap accepts this route only when the Secure MCP Tunnel admission plan is READY.

## 5. Register GREMLIN in ChatGPT

Create the GREMLIN app/plugin from ChatGPT developer mode using the admitted endpoint/transport.

After successful creation, record:

```text
GREMLIN_CHATGPT_APP_CREATED=true
```

## 6. Scan tools

Run ChatGPT's tool scan for GREMLIN.

Only after the scan succeeds set:

```text
GREMLIN_CHATGPT_TOOL_SCAN_STATUS=PASS
```

Do not set PASS merely because the local MCP process starts.

## 7. Record the actual account capability

Record what the clean account actually exposes:

```text
GREMLIN_CHATGPT_CAPABILITY_MODE=read
```

or:

```text
GREMLIN_CHATGPT_CAPABILITY_MODE=full
```

GREMLIN does not infer this from another account or from stale plan assumptions.

## 8. Final gate

Run:

```text
gremlin-chatgpt-clean --json
```

Success is exactly:

```text
"status": "READY"
```

Any other state remains:

```text
BLOCKED:<GATE>
```

with the first required corrective action.
