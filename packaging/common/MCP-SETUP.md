# GREMLIN MCP setup

For supported clients, use **GREMLIN Control Center → Setup / AI Providers → Connect & Test**. Manual editing is a fallback, not the normal installation path.

## Normal setup

1. Activate the signed GREMLIN entitlement in Control Center.
2. Open **AI Providers**.
3. GREMLIN detects supported clients for the current operating system.
4. Choose **Connect & Test**.
5. A successful setup ends with the Control Center readiness state **READY**.
6. Use **Launch Workspace** for the licensed loopback-only visual surface, or work through the connected MCP client.

GREMLIN uses local `stdio` MCP by default. No listening network port is required for the normal desktop integration.

## ChatGPT clean-account setup

ChatGPT is a separate deployment surface. Do not treat a local `stdio` registration as a ChatGPT installation.

### Portable remote-MCP package path

For a fresh ChatGPT account:

1. deploy GREMLIN behind a stable remotely reachable HTTPS Streamable HTTP MCP endpoint ending in `/mcp`;
2. run `gremlin-chatgpt-package --plan --endpoint https://HOST/mcp --json`;
3. build with `gremlin-chatgpt-package --build --endpoint https://HOST/mcp --output GREMLIN-ChatGPT-Plugin-v1.zip --json`;
4. inspect the ZIP with `gremlin-chatgpt-package --inspect GREMLIN-ChatGPT-Plugin-v1.zip --json`;
5. register/install the plugin through the supported ChatGPT plugin/developer surface;
6. complete host-side authentication, permission review, and Scan Tools/tool discovery;
7. report end-to-end READY only after the ChatGPT host actually exposes and successfully calls GREMLIN tools.

The ZIP builder returns `PACKAGE_READY`, not end-to-end `READY`.

### Secure MCP Tunnel path

`gremlin-openai-tunnel` remains a separate transport integration for keeping a local/private GREMLIN server off the public Internet. ChatGPT host registration for a Secure MCP Tunnel is performed through the OpenAI tunnel/app surface. The portable ZIP builder does not invent a tunnel URL or a ChatGPT registration ID.

The clean-account contract is intentionally independent of prior conversations, ChatGPT Memory, Library files, NOEMA session files, and local MCP client configuration.

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
gremlinctl support report --json
gremlinctl support report --write --json
```

Customers normally do not need these commands; they exist for diagnostics and support. The persisted support report is commitment-bound and deliberately excludes customer secrets, configuration contents and provider command output.
