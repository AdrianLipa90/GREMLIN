# GREMLIN Oriented Relational Coupling v1.3

Status: CANDIDATE / RESEARCH_BINDING_ONLY

## Purpose

v1.3 restores the signed orientation information carried by the holonomy phase after the v1.1 energy partition and v1.2 dual-channel diagnostic.

The preserved lineage is

`Lambda_R -> E_R -> connection -> tau -> {C_h,D_h,J_C,J_D} -> oriented U(1) coupling amplitude`.

## Holonomy unit

The bound holonomy is represented as

`h_R = exp(i tau) = cos(tau) + i sin(tau)`.

The real component retains the channel imbalance and the imaginary component retains the orientation sign of the internal rotation.

## Channel imbalance identity

From v1.1,

`C_h = cos^2(tau/2)`

`D_h = sin^2(tau/2)`.

Therefore

`C_h - D_h = cos(tau)`.

With

`J_C = E_R C_h`

and

`J_D = E_R D_h`,

the energy imbalance satisfies

`J_C - J_D = E_R cos(tau)`.

The implementation records the binary64 residuals and validates these identities within explicit numerical tolerance.

## Oriented coupling amplitude

The candidate complex relational coupling amplitude is

`J_complex = E_R exp(i tau)`.

Its projections are

`Re(J_complex) = E_R cos(tau) = J_C - J_D`

and

`Im(J_complex) = E_R sin(tau)`.

The second projection is the signed rotational quadrature.

Magnitude closure is

`|J_complex| = |E_R|`.

Thus the phase changes orientation and projection while the magnitude remains bound to the relational source-energy scale.

## Orientation classification

The sign of `sin(tau)` defines the receipt orientation class:

- `POSITIVE_HOLONOMY_ORIENTATION`,
- `NEGATIVE_HOLONOMY_ORIENTATION`,
- `AXIAL_OR_ZERO_HOLONOMY_ORIENTATION` within the declared binary64 orientation tolerance.

The pair `tau` and `-tau` preserves the real projection and reverses the rotational quadrature.

## Physical attribution frontier

The oriented amplitude is a relational coupling candidate with explicit provenance. The next operator layer must provide a Hermitian embedding before an evolution claim is assessed.

The receipt therefore carries:

`channel_selection_status = OPEN_REQUIRES_PHYSICAL_ATTRIBUTION_LAW`

`hermitian_operator_embedding_status = OPEN_REQUIRES_EXPLICIT_OPERATOR_PAIRING`

`entanglement_attribution_status = OPEN_REQUIRES_HERMITIAN_EVOLUTION_WITNESS`.

## Authority

The layer has research-binding authority only and canon status `CANDIDATE`. The complete complex amplitude and its orientation are available to subsequent KAKU/RADICAL/PNV operator construction while promotion remains evidence-gated.
