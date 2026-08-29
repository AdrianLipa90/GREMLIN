# GREMLIN

GREMLIN is the root system. OCTOPUS and BELZEBUB are writable subordinate tools with independent local `CURRENT` heads, while GREMLIN binds verified tool heads into one aggregate `SUPER_CURRENT`.

## Native authority

Authoritative runtime declarations live in `native/*.pnv` and use the existing PhaseNav Natural Coding operator vocabulary. Python is retained only as a reference/test harness.

```text
GREMLIN
├── SUPER_CURRENT
├── Triple Pulse Boot: IDENTITY -> DOMAIN -> AUTHORITY
├── REQUEST -> COUPLING -> ADMISSION
├── Natural Queue + scalar tau modulation
├── OCTOPUS
│   └── CURRENT + own content-addressed write namespace
└── BELZEBUB
    └── CURRENT + own content-addressed defensive write namespace
```

Operational runtime surface: `/dev/shm/ciel_noema`.

Persistent-memory protocol:

- GREMLIN: `OBJECT -> RECEIPT -> SUPER_CURRENT`
- OCTOPUS: `OBJECT -> RECEIPT -> CURRENT`
- BELZEBUB: `OBJECT -> RECEIPT -> CURRENT`
- event-driven; no tick requirement
- no last-writer-wins
- missing/corrupt lineage fails closed

Boot protocol:

1. `IDENTITY` pulse — verify current identity.
2. `DOMAIN` pulse — verify current live runtime generation.
3. `AUTHORITY` pulse — verify admission authority.
4. `REQUEST`.
5. `COUPLING` to the current live generation.
6. `ADMISSION` only after 3/3 pulse receipts bind the same generation.

Native witness: `native/GREMLIN_TRIPLE_PULSE_BOOT_V0_5.pnv`.

## PhaseNav prototype pipeline

An audited relation candidate can be compiled into PhaseNav character IR, converted into a deterministic reference prototype and checked by the experiment harness:

```text
SURVIVED_AUDIT
  -> PHASENAV_IR_CANDIDATE
  -> UNTRUSTED_PROTOTYPE
  -> VALIDATED_PROTOTYPE
```

`VALIDATED_PROTOTYPE` currently carries `validation_scope=REFERENCE_CONFORMANCE_ONLY`.

## Standalone MCP adapter v0.1

GREMLIN can also run as a standalone Model Context Protocol server for research integration. This path does not require NOEMA or `/dev/shm/ciel_noema` for discovery, Bestiary inspection, scheduler planning, or the existing Python reference prototype pipeline.

Install from the repository root:

```text
python -m pip install -e .
```

Run over stdio:

```text
gremlin-mcp
```

Or expose a local Streamable HTTP endpoint:

```text
gremlin-mcp --transport streamable-http --host 127.0.0.1 --port 8766
```

Default HTTP MCP endpoint: `http://127.0.0.1:8766/mcp`.

Exposed MCP tools:

- `gremlin_status`
- `gremlin_bestiary`
- `gremlin_species`
- `gremlin_plan`
- `gremlin_prototype`

The MCP adapter is fail-closed with respect to native authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Full specification: `spec/GREMLIN_MCP_SERVER_V0_1.md`.

## Visual research client v0.1

The local visual client exposes the prototype pipeline as a three-pane workspace:

```text
Problem & candidate | PhaseNav operator graph | Prototype / BELZEBUB / Tests / Receipt
```

Run from the repository root:

```text
python client/gremlin_web_server_v01.py
```

Open `http://127.0.0.1:8765` and use **Load example** followed by **Compile & test**.

The browser surface has zero external frontend dependencies. The local API delegates to the same `run_client_request()` implementation used by the CLI and test harness.

Visual-client authority state:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

Full specification: `spec/GREMLIN_VISUAL_CLIENT_V0_1.md`.

Motto: `Verbis utor, informationem in existentiam converto.`

BELZEBUB quarantines untrusted code as data, performs semantic defensive analysis, and emits repair/immunity candidates. Quarantined content has no execution authority.

## License

GREMLIN is distributed under the **CIEL Research Non-Commercial License v2.0** (`LicenseRef-CIEL-Research-NonCommercial-2.0`). The license permits non-commercial research execution, reproducibility, benchmarking, profiling, vectorization, security review, and project-native agent/orchestration experiments while reserving commercial use, production deployment, hosted services, AI/ML development use, and model extraction for separate written authorization.

See [`LICENSE`](LICENSE) for the canonical terms.
