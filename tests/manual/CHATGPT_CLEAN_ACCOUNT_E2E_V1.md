# GREMLIN ChatGPT Clean-Account E2E v1

Status: REQUIRED MANUAL / HOST TEST

This test is intentionally performed on a ChatGPT account or workspace with no prior GREMLIN installation. It is not replaceable by unit tests, repository state, conversation memory, or a successful local MCP handshake.

## Preconditions

- Use an eligible ChatGPT surface with plugin/developer capabilities available.
- Do not reuse an account that already has GREMLIN registered.
- Do not copy ChatGPT Memory, Library files, prior GREMLIN chats, or local MCP configuration into the account.
- Have one real remote GREMLIN HTTPS Streamable HTTP MCP endpoint ending in `/mcp`.
- Do not put credentials or access tokens in the endpoint URL.

Record the GREMLIN commit SHA and the exact package SHA-256 used for the run.

## Build gate

Run:

```text
gremlin-chatgpt-package --plan --endpoint https://HOST/mcp --json
```

Expected:

```text
status = PACKAGE_READY
host_gate.status = EXTERNAL_REQUIRED
```

Then run:

```text
gremlin-chatgpt-package --build \
  --endpoint https://HOST/mcp \
  --output GREMLIN-ChatGPT-Plugin-v1.zip \
  --json
```

Expected:

- status is `PACKAGE_READY`, never end-to-end `READY`;
- `next_required_gate = CHATGPT_HOST_ADMISSION`;
- ZIP self-inspection reports PASS;
- ZIP contains exactly:
  - `plugin.json`
  - `mcp.json`
  - `skills/gremlin/SKILL.md`

Inspect again independently:

```text
gremlin-chatgpt-package --inspect GREMLIN-ChatGPT-Plugin-v1.zip --json
```

Expected: `PASS`.

## Fresh-account host gate

On the clean ChatGPT account/workspace:

1. Enable the currently supported Developer Mode / plugin authoring surface.
2. Register the GREMLIN remote MCP endpoint or install the generated portable package using the current supported host flow.
3. Run Scan Tools or the current equivalent discovery operation.
4. Review the discovered tool list and permissions.
5. Reject the run if GREMLIN tools are absent, stale, silently substituted, or if the host reports an MCP/schema/authentication error.

Do not import prior GREMLIN conversation history as a workaround.

## Functional probe

Open a new chat/session after installation.

Request a bounded GREMLIN status/inspection operation.

Required evidence:

- ChatGPT makes an actual GREMLIN MCP tool call;
- `gremlin_status` is discoverable when exposed by the deployed server;
- the response contains live server data rather than a prompt-only reconstruction;
- no dependency on ChatGPT Memory or Library is required;
- no dependency on `localhost`, RFC1918/private IP space, `.local`, or `/dev/shm/ciel_noema` exists on the ChatGPT side.

Then request a bounded routing operation.

Required evidence:

- an actual GREMLIN route tool is invoked;
- returned route/receipt data originates from the MCP server;
- candidate/authority distinctions remain intact.

## Negative controls

Repeat or simulate these failure cases and require loud failure:

- no remote endpoint;
- HTTP instead of HTTPS;
- localhost;
- private IP;
- wrong path not ending in `/mcp`;
- query-token URL;
- MCP server unavailable;
- authentication denied;
- plugin registered but tools not scanned/refreshed.

None of these may be reported as READY.

## Verdict

PASS requires all of the following:

```text
PACKAGE_SELF_INSPECTION = PASS
CHATGPT_HOST_ADMISSION = PASS
GREMLIN_TOOL_DISCOVERY = PASS
GREMLIN_LIVE_STATUS_CALL = PASS
GREMLIN_LIVE_ROUTE_CALL = PASS
CLEAN_ACCOUNT_INDEPENDENCE = PASS
NEGATIVE_CONTROLS_FAIL_LOUD = PASS
```

Any missing item yields FAIL or BLOCKED, not partial READY.

## Receipt template

```json
{
  "schema": "GREMLIN_CHATGPT_CLEAN_ACCOUNT_E2E_V1",
  "date_utc": "",
  "gremlin_commit": "",
  "package_sha256": "",
  "chatgpt_surface": "",
  "package_self_inspection": "PASS|FAIL",
  "chatgpt_host_admission": "PASS|FAIL|BLOCKED",
  "tool_discovery": "PASS|FAIL|BLOCKED",
  "live_status_call": "PASS|FAIL|BLOCKED",
  "live_route_call": "PASS|FAIL|BLOCKED",
  "clean_account_independence": "PASS|FAIL|BLOCKED",
  "negative_controls_fail_loud": "PASS|FAIL|BLOCKED",
  "verdict": "PASS|FAIL|BLOCKED",
  "notes": ""
}
```
