# GREMLIN Relational Coupling Energy v1.1

Status: IMPLEMENTED CANDIDATE — CI verdict required.

## Purpose

v1.1 closes the energy-scale gap between the bound relational Lambda source energy and the phase/holonomy layer without adding a new continuous free scale.

The bound inputs are:

```text
E_R   <- relational Lambda effective-source energy receipt
Tau   <- closed-path connection integral / holonomy receipt
```

The phase partition uses the existing half-angle structure:

```math
C_h=\cos^2\left(\frac{\tau}{2}\right),
\qquad
D_h=1-C_h=\sin^2\left(\frac{\tau}{2}\right).
```

The source energy is partitioned into two candidate channels:

```math
J_C=E_R C_h,
\qquad
J_D=E_R-J_C.
```

Analytically,

```math
J_C+J_D=E_R.
```

The implementation records the binary64 reconstruction and residual explicitly.

## Channel meaning

The receipt names two candidate channels:

```text
COHERENCE_CHANNEL
TORSION_CHANNEL
```

At trivial holonomy,

```math
\tau=0
\Rightarrow
C_h=1,
D_h=0,
```

so the partition places the bound source energy in the coherence channel.

At half-turn holonomy,

```math
\tau=\pi
\Rightarrow
C_h=0,
D_h=1,
```

so the partition places the bound source energy in the torsion channel.

At

```math
\tau=\frac{\pi}{2},
```

the channels are balanced.

## Relation to the v1.0 quantum witness

v1.0 introduced a joint-state witness and a declared two-body coupling Hamiltonian

```math
H_{rel}=J_{rel}(\sigma_z\otimes\sigma_z).
```

v1.1 supplies two dimensionally valid candidate energies, `J_C` and `J_D`, derived from the already-bound relational source energy and holonomy phase.

The current frontier is discrete rather than continuous:

```text
channel_selection_status = OPEN
entangling_channel_attribution_status = OPEN
```

A later adapter may test each channel as `J_rel` while preserving lineage and comparing predicted observables.

## Parameter accounting

Given the bound source-energy receipt and the bound holonomy receipt, the v1.1 partition introduces no additional continuous scale:

```text
parameter_free_given_bound_source_energy_and_holonomy = true
```

The support volume and relational Lambda value are already explicit upstream inputs in the v0.8 energy receipt. The geometry adapter and path discretization are already explicit upstream inputs in v0.9.

## Signed energy

The partition preserves the sign of the upstream effective source energy. This allows the same receipt format to represent positive or negative relational Lambda candidates while retaining exact provenance.

## Validation targets

The v1.1 tests cover:

- zero-holonomy coherence-channel limit;
- pi-holonomy torsion-channel limit;
- balanced pi/2 partition;
- source-energy reconstruction;
- full-turn phase periodicity;
- explicit open channel-selection frontier;
- rejection of mismatched Lambda-energy/path lineage;
- tamper rejection for channel energy;
- signed partition for negative Lambda candidates.

## Next derivation target

The next layer should run both candidate channel energies through the v1.0 joint-state evolution under identical initial conditions and compare:

```math
C_{ent}^{(C)}(t),
\qquad
C_{ent}^{(D)}(t).
```

A physical channel assignment should then be promoted only from a declared observational or derivational criterion, with the criterion and evidence bound into the receipt.
