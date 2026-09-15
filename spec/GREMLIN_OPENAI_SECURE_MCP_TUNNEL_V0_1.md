# GREMLIN × OpenAI Secure MCP Tunnel v0.1

**Schema:** `GREMLIN_OPENAI_SECURE_MCP_TUNNEL_V0_1`  
**Status:** integration candidate  
**Authority:** transport only; no canon promotion, no production actuation authority  
**Verified against OpenAI Secure MCP Tunnel documentation:** 2026-09-15

## 1. Goal

Expose the existing private GREMLIN MCP server to supported OpenAI products without opening a public inbound listener.

The intended topology is:

```text
ChatGPT / supported OpenAI surface
        |
OpenAI-hosted Secure MCP Tunnel endpoint
        |
 outbound-only HTTPS control plane
        |
    tunnel-client
        |
 local stdio
        |
 GREMLIN MCP
```

GREMLIN remains a private local process. `tunnel-client` owns the remote transport path and forwards MCP JSON-RPC to GREMLIN over stdio.

## 2. Why stdio is the canonical path

GREMLIN already supports stdio natively. Secure MCP Tunnel can launch a local MCP command directly, so no public HTTP listener, TLS termination, DNS-rebinding exception, or public reverse proxy is required for this profile.

The default child command is:

```text
python -m gremlin_mcp.server_with_hive --transport stdio
```

The concrete Python executable is resolved from the running GREMLIN environment.

## 3. Admission gates

The bootstrap is fail-closed and uses deterministic logical admission gates:

```text
IDENTITY -> TUNNEL_ID -> RUNTIME_KEY -> MCP_STDIO -> PERSISTENCE -> DOCTOR -> READY
```

These are software admission gates. No physical QPU, quantum-gate execution, or quantum-computing claim is made.

### IDENTITY

`tunnel-client` must resolve to an executable.

### TUNNEL_ID

`GREMLIN_OPENAI_TUNNEL_ID` (or `OPENAI_TUNNEL_ID`) must contain a structurally valid `tunnel_...` identifier.

### RUNTIME_KEY

`CONTROL_PLANE_API_KEY` must be present. Its value is never emitted in the plan or receipts.

### MCP_STDIO

GREMLIN is launched privately over stdio. This gate does not authorize public network exposure.

### PERSISTENCE

If explicit paths are absent, the bootstrap supplies durable defaults for:

```text
GREMLIN_MCP_STATE_PATH
GREMLIN_HIVE_STATE_PATH
```

under the user's local state directory.

### DOCTOR

`READY` is impossible until `tunnel-client init` and `tunnel-client doctor --explain` both return zero.

## 4. CLI

After installing GREMLIN with the branch containing this integration:

```text
gremlin-openai-tunnel --json
```

shows the gate state without printing secrets.

Initialize the tunnel profile and validate it:

```text
gremlin-openai-tunnel --setup --json
```

Run the validated profile:

```text
gremlin-openai-tunnel --run
```

The bootstrap uses subprocess argument vectors and does not invoke a shell.

## 5. Required external account state

The repository cannot create the OpenAI-hosted tunnel object by itself. The operator must have:

1. a `tunnel_id` from OpenAI Platform tunnel settings;
2. a runtime Platform API key usable by `tunnel-client`;
3. the appropriate tunnel permissions for the target Platform organization/workspace;
4. ChatGPT developer-mode access on a supported product surface when the tunnel is used from ChatGPT.

The tunnel and ChatGPT developer-mode permissions are separate controls.

## 6. Security properties

- No inbound public listener is required.
- The control-plane API key is read from the environment and is not serialized into GREMLIN receipts.
- No secret is placed on a command line by this bootstrap.
- Failure of any required admission gate yields `BLOCKED`.
- Failure of `tunnel-client init` or `doctor` yields `FAIL` and prevents `READY`.
- Tunnel transport does not promote GREMLIN candidates to canon.
- Existing GREMLIN authority remains fail-closed.

## 7. ChatGPT product note

As of the verification date, ChatGPT connects to custom MCP applications through supported developer-mode surfaces and does not directly connect to a local MCP server. Secure MCP Tunnel is the supported private-network path when the MCP server should remain non-public.

Tool availability in a published ChatGPT app may be snapshotted by the product; server-side tool changes can require an explicit refresh/review in ChatGPT.

## 8. Non-goals

This profile does not:

- expose GREMLIN directly to the public Internet;
- add a new GREMLIN authority class;
- grant production write authority;
- grant canon authority;
- claim physical quantum execution;
- replace Q28, NOEMA, PhaseNav, or existing GREMLIN admission rules.
