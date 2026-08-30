# GREMLIN MCP setup

For supported clients, use **GREMLIN Control Center → Setup / AI Providers → Connect & Test**. Manual editing is a fallback, not the normal installation path.

## Normal setup

1. Activate the signed GREMLIN entitlement in Control Center.
2. Open **AI Providers**.
3. GREMLIN detects supported clients for the current operating system.
4. Choose **Connect & Test**.
5. A successful setup ends with the Control Center readiness state **READY**.

GREMLIN uses local `stdio` MCP by default. No listening network port is required for the normal desktop integration.

## Provider integration modes

GREMLIN prefers the provider's own MCP command interface when the client exposes one. Current native-CLI integrations include Codex, OpenCode, Claude Code, Gemini CLI, and VS Code/Copilot. Cursor, Windsurf, and Windows Claude Desktop use a backed-up, atomic MCP configuration merge.

For file-based integrations GREMLIN performs:

`read → validate → backup → merge → atomic replace → re-read → verify`

Removal also creates a backup before modifying the client configuration.

## Custom MCP client

For an unsupported client that uses a standard JSON `mcpServers` object, open **AI Providers → Advanced: Custom MCP client** and supply the configuration file path. GREMLIN will inspect and update that file through the same backup/atomic-write path.

## Diagnostics

Control Center exposes a customer-facing readiness check and the lower-level Doctor report. The readiness result is either:

- `READY` — signed license valid, GREMLIN runtime available, and at least one AI client connected; or
- `ACTION_REQUIRED` — the UI lists the remaining action.

CLI equivalents for support are:

```text
gremlinctl license status --json
gremlinctl integrations providers --json
gremlinctl ready --json
gremlinctl doctor --json
```

Customers normally do not need these commands; they exist for diagnostics and support.
