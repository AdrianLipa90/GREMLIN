# GREMLIN PhaseNav MCP VCS Capability v0.1

Status: CANDIDATE_ONLY / NO_CANON_PROMOTION / NO_MAIN_MUTATION

## Purpose

Provide the missing bounded VCS capability surface required by the PhaseNav execution contract without introducing shell, Git CLI, subprocess, os.system, Makefile hooks, or generic command execution.

The capability is intended to be exposed through MCP and consumed by PhaseNav/CIEL only after a valid `PHASENAV_ACTION_PACKET_V1` and GREMLIN triple-pulse attestation.

## Required preflight

Every mutating request MUST carry:

- `PHASENAV_ACTION_PACKET_V1`;
- `gate_receipt` proving explicit operator authorization;
- `tether_status = ACTIVE`;
- `gremlin_attestation` proving identity, domain and authority receipts from the same generation;
- `shell_used = false`;
- `copy_only = true` for first migration unless an explicitly authorized later policy says otherwise.

Missing or inconsistent preflight data MUST fail closed.

## Bounded VCS operations

The MCP surface is intentionally finite:

1. `vcs_checkpoint_prepare`
   - bind repository, base ref, expected head and action packet;
   - return deterministic checkpoint commitment;
   - no repository mutation.
2. `vcs_branch_prepare`
   - derive a candidate branch name from the authorized action packet;
   - no main mutation.
3. `vcs_write_prepare`
   - accept only explicit path/content tuples;
   - reject delete/move/rename in COPY_ONLY mode;
   - return content commitments before mutation.
4. `vcs_commit_prepare`
   - bind exact prepared writes to one logical-step commit message.
5. `vcs_tag_prepare`
   - prepare the checkpoint tag required before a logical mutation.
6. `vcs_bundle_prepare`
   - prepare a portable bundle descriptor/manifest commitment; implementation authority is delegated only to an authorized native VCS adapter.
7. `vcs_test_receipt_bind`
   - bind external/native test evidence to the logical step.
8. `vcs_execution_receipt_build`
   - build `PHASENAV_EXECUTION_RECEIPT_V1` with `shell_used=false`, exact before/after heads, checkpoint/tag/bundle commitments and test evidence.

This candidate does not expose unrestricted repository mutation and does not itself grant production authority.

## GREMLIN role

GREMLIN is the audit/navigation and attestation layer. It does not replace CIELingo semantic processing, NOEMA authority, or PhaseNav path selection. Its role here is to validate and bind:

`operator authorization -> tether -> triple pulse -> action packet -> bounded VCS operation -> execution receipt`.

The existing GREMLIN triple-pulse contract remains normative for GREMLIN admission:

- identity receipt required;
- domain receipt required;
- authority receipt required;
- same-generation binding required;
- tether guard required;
- fail closed.

## Authority firewall

This capability MUST NOT:

- write directly to `main` by default;
- promote candidate to canon;
- infer authorization from branch ownership;
- create arbitrary shell commands;
- invoke Git CLI, subprocess, os.system or shell wrappers;
- weaken PhaseNav `AGENT.md`;
- claim a checkpoint/tag/bundle exists before an authorized native adapter returns evidence.

Prepared operations are proposals until corresponding native adapter evidence is bound into the final execution receipt.

## Bootstrap status

This v0.1 is deliberately designed to remove the current bootstrap gap: GREMLIN can validate and serialize the exact bounded operation package that a PhaseNav-native VCS adapter must execute. Wiring that adapter into the PhaseNav repository still requires a contract-compliant PhaseNav-native mutation path.
