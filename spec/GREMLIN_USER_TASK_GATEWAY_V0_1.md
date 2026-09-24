# GREMLIN User Task Gateway v0.1

Status: candidate. Authority: cognitive routing only.

## Purpose

Provide one primary GREMLIN entrypoint for ordinary user tasks:

`user task -> SGT semantic graph -> OCTOPUS inclusion -> PhaseNav T^36 scheduling -> Bestiary worker payload`

The gateway is intended to be the first GREMLIN call for a user task. It does not replace the host model, connector authorization, or external action boundary.

## Invariants

1. OCTOPUS owns semantic specialist inclusion.
2. PhaseNav may reorder an admitted route for scheduling locality but cannot add or remove semantic specialists.
3. Explicit validation policy may append HOUND/MANTIS for test/audit work.
4. Repository/write/send/deploy style tasks remain plan-only until the host obtains the normal explicit authorization.
5. Raw context documents are compiled into the semantic graph and represented to workers by graph tokens plus content commitments; raw context is not duplicated into the worker payload.
6. Live NOEMA state is a witness only in v0.1. It does not override semantic routing.
7. No canon promotion or production execution authority is granted.
8. Routing metadata must not become semantic evidence. Counters and bookkeeping fields stay outside the OCTOPUS cue surface, preventing self-routing contamination.

## Modes

- `DIRECT`: the task passed through the gateway but no specialist route was justified.
- `GREMLIN_ROUTED`: one or more specialists are admitted.

The MCP wrapper supports `dispatch_mode=PLAN` and `dispatch_mode=QUEUE`. QUEUE mutates only GREMLIN's local worker queue; it does not perform external side effects.

## Claim boundary

This is a native GREMLIN/PhaseNav task-routing surface, not a modification of the underlying OpenAI model router. PhaseNav coordinates scheduling; semantic route membership remains evidence-based.
