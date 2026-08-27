# GREMLIN Dual-Channel Entanglement Probe v1.2

Status: CANDIDATE / RESEARCH_BINDING_ONLY

## Purpose

This layer compares the two v1.1 relational coupling-energy channels under one common quantum diagnostic. It preserves the full lineage

`Lambda_R -> effective source energy E_R -> connection path -> holonomy tau -> {J_C, J_D} -> ZZ evolution -> concurrence`.

The comparison produces a geometry-derived rate ordering while keeping physical channel attribution explicitly open.

## Inputs

The probe requires:

- a validated v0.8 relational Lambda energy receipt,
- a validated v0.9 connection-path holonomy receipt,
- a validated v0.9 QHTRI connection-derived lag receipt,
- a validated v1.1 relational coupling-energy partition.

Lineage equality between relation, loop, Lambda-energy commitment and coupling partition is mandatory.

## Diagnostic state

The fixed diagnostic input is

`|psi_0> = |+>|+> = (|00>+|01>+|10>+|11>)/2`.

It is a model diagnostic state used identically for both channels.

## Channel energies

v1.1 supplies

`C_h = cos^2(tau/2)`

`D_h = sin^2(tau/2) = 1-C_h`

`J_C = E_R C_h`

`J_D = E_R D_h`.

The partition satisfies

`J_C + J_D = E_R`.

## Shared Hamiltonian

Each channel is tested with the same candidate interaction law

`H_k = J_k (sigma_z tensor sigma_z)`

for `k in {C,D}`.

For the equal-superposition product diagnostic, concurrence under this evolution is controlled by

`C_ent,k(t) = |sin(2 J_k t / hbar)|`.

## Source-quarter-action probe

The common probe time is derived from the total source energy:

`t_Q = pi hbar / (4 |E_R|)`.

At this time the channel diagnostics are

`C_C(t_Q) = |sin((pi/2) C_h)|`

`C_D(t_Q) = |sin((pi/2) D_h)|`.

This time is a diagnostic normalization tied to the bound source energy.

## First maximal-entanglement time

For a non-zero candidate channel

`t_max,k = pi hbar / (4 |J_k|)`.

A zero-energy channel receives the status

`UNREACHABLE_UNDER_ZERO_CHANNEL_COUPLING`.

The geometry-derived rate ordering is therefore determined by the v1.1 weights. Binary64 equality around `C_h=D_h=1/2` uses an explicit tolerance recorded in the receipt.

Possible orderings are:

- `COHERENCE_CHANNEL_FASTER`,
- `TORSION_CHANNEL_FASTER`,
- `DEGENERATE_EQUAL_RATE`.

## Attribution firewall

The receipt records

`channel_selection_status = OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW`

and

`rate_ordering_is_channel_selection = false`.

Thus the rate comparison is preserved as a mathematical/model result while physical realization remains a separately testable claim.

The synchronization/entanglement firewall remains active:

`synchronization_entanglement_equivalence = false`.

## Symmetry checks

The implementation tests the following structure:

- `tau=0`: coherence channel carries the full v1.1 partition and reaches the first maximum while the torsion channel has zero coupling,
- `tau=pi`: the ordering reverses,
- `tau=pi/2`: the channels are degenerate within declared binary64 tolerance,
- mirror holonomies `tau` and `pi-tau` exchange the channel diagnostics.

## Authority

The v1.2 receipt has research-binding authority only. Canon status remains `CANDIDATE`. Promotion requires a physical attribution law or independent witness that selects or derives the realized interaction channel.
