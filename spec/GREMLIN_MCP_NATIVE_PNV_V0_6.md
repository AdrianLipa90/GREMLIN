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

`READ_ONLY` and `LOW_RISK_AUTO` may pass automatically.

`LOW_RISK_AUTO` is restricted to the already-classified GREMLIN local worker/state mutation tools. These tools do not receive canon, repository-main, delete/move/rename, force-push, secret, or production-effect authority.

Unknown tools and any future key mutation surface are classified as `KEY_MUTATION_REVIEW` and fail closed until separately admitted.

## Explicitly not automatic

- main/master mutation;
- canon promotion;
- delete, move, rename, reset, rebase or force-push;
- secret or credential changes;
- production external effects;
- authority widening.

## Python boundary

Python remains necessary for MCP SDK transport, filesystem observation, sockets and process integration. It is not the semantic authority of the gate.

The PNV program deliberately uses only:

`SOURCE, IDENTITY, ORDER, COMPOSITION, RETURN`.

No callback-dependent `CONDITION` or `TRANSFORM` participates in admission.
