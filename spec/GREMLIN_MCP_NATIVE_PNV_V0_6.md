# GREMLIN MCP Native PNV Admission v0.6

Status: CANDIDATE / fail-closed native policy gate.

## Goal

Make PNV/PNCS the admission authority for GREMLIN MCP calls while retaining Python only as the MCP transport and host adapter.

The authority chain is:

```text
MCP request
-> typed host observations
-> GREMLIN_MCP_NATIVE_ADMISSION_V0_6.pnv
-> PNV assertions
-> deterministic admission receipt
-> existing GREMLIN tool implementation
```

The host may observe exact runtime facts. It does not decide admission.

## Live prerequisites

The native gate requires:

- NOEMA live root;
- `session/tether_guard_latest.json` with ACTIVE tether and zero failures;
- `gremlin/triple_pulse_attestation.json`;
- IDENTITY = VERIFIED;
- DOMAIN = ACTIVE;
- AUTHORITY = VERIFIED;
- all pulse receipts bound to one generation;
- `system_sync/CURRENT.json` with `ALIGNED_CANDIDATE`, `canon_allowed=false`, and the same runtime generation.

No static runtime fallback is admitted. A stale or missing NOEMA/PhaseNav/PNCS/CIELingo/GREMLIN system-sync pointer is an admission failure, not a warning.

## Mutation tiers

Tool metadata is descriptive and does not form a capability whitelist.

Unknown or newly added GREMLIN tools are not rejected merely because they are absent from a metadata registry. Concrete high-consequence effects remain governed by their own exact operation path rather than by tool-name classification.

## Explicitly not automatic

- main/master mutation;
- delete, move, rename, reset, rebase or force-push;
- secret or credential changes;
- production external effects;
- authority widening.

## Python boundary

Python remains necessary for MCP SDK transport, filesystem observation, sockets and process integration. It is not the semantic authority of the gate.

The PNV program deliberately uses only:

`SOURCE, IDENTITY, ORDER, COMPOSITION, RETURN`.

No callback-dependent `CONDITION` or `TRANSFORM` participates in admission.
