# GREMLIN Visual Research Client v0.1

Status: IMPLEMENTED CLIENT CANDIDATE

## Purpose

The visual client exposes the existing GREMLIN prototype pipeline as one local research workspace:

```text
Problem / audited candidate
        ↓
GREMLIN + BELZEBUB
        ↓
PhaseNav T^36 / Z^36 IR
        ↓
UNTRUSTED_PROTOTYPE
        ↓
reference experiment
        ↓
experiment receipt
```

The UI presents three coordinated panes.

### Pane 1 — Problem & candidate

The left pane contains:

- a human research-problem note,
- the explicit `GREMLIN_RELATION_CANDIDATE_V0_1` JSON,
- reference sample count,
- example loading,
- compile-and-test action.

The problem note is presentation context in v0.1. Executable compilation continues to use explicit phase-native relation records.

### Pane 2 — PhaseNav operator graph

The centre pane materializes the returned `GREMLIN_PHASENAV_IR_V0_1` as SVG.

For every sparse character term it renders:

```text
active T^36 lanes
      ↓
KCHI character term
      ↓
source relation reference
```

Each active lane shows its exact integer `ell` coefficient. The pane also shows operator identity, term count, IR commitment and complete client-response commitment.

### Pane 3 — Prototype & evidence

The right pane contains four views:

```text
Prototype
BELZEBUB
Tests
Receipt
```

`Prototype` displays the deterministic Python reference source and prototype commitment.

`BELZEBUB` displays candidate audit state and compiler epistemic state.

`Tests` displays the reference-conformance checks and numerical error bounds.

`Receipt` displays the complete experiment receipt.

## Local API

`client/gremlin_web_server_v01.py` serves the static client and a bounded local JSON API.

```text
GET  /api/health
GET  /api/example
POST /api/prototype
```

`POST /api/prototype` delegates directly to the existing `run_client_request()` pipeline and wraps the result with visual-client authority metadata.

The server binds to `127.0.0.1:8765` by default.

Request bodies are capped at 1 MiB. Static resources are served through an exact path whitelist.

## Browser surface

The browser client is zero-dependency HTML/CSS/JavaScript.

Returned artifact text is inserted using DOM `textContent`. The graph uses `createElementNS` to construct SVG nodes. External frontend scripts, runtime package CDNs and HTML injection are absent from the v0.1 surface.

## Authority state

The visual API carries:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

The client therefore exposes the research compilation and reference-validation path while retaining the existing explicit admission and canon boundaries.

## Run

From the repository root:

```text
python client/gremlin_web_server_v01.py
```

Then open:

```text
http://127.0.0.1:8765
```

The bundled example can be loaded and executed directly from the left pane.
