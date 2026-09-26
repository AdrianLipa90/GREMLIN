# GREMLIN Fractal Moire Physical Calibration
Date: 2026-09-26
Status: CALIBRATION_PASS / TYPED_BIVECTOR36_SO2_BINDING_PASS / GENERIC_PHASENAV36_BINDING_OPEN

## Calibrated scalar identity

For the scalar relational operator

    d(theta)=4 sin^2(theta/2)

and identical-lattice Moire geometry

    L_M=a/[2 sin(|theta|/2)],

the exact physical calibration is

    d=(a/L_M)^2.

In reciprocal space:

    sqrt(d)=Delta K/K=a/L_M.

No free fitted coefficient is introduced.

## External anchors

Graphene lattice constant:

    a=0.246 nm.

Published geometry checks:
- Luican et al. 2011: L=0.65 +/- 0.05 nm, theta=21.8 +/- 1.7 deg;
  inversion gives 21.8158 deg -> PASS.
- Luican et al. 2011: L=4.0 +/- 0.2 nm, theta=3.5 +/- 0.3 deg;
  inversion gives 3.52425 deg -> PASS.
- Tilak et al. 2021: L=12.6 nm, theta=1.12 deg;
  inversion gives 1.11865 deg -> PASS.

References:
- A. Luican et al., Physical Review Letters 106, 126802 (2011),
  DOI 10.1103/PhysRevLett.106.126802.
- N. Tilak et al., Nature Communications 12, 4180 (2021).

## Generic phase-coordinate 36D correction

For

    C=(1/36) sum_j exp(i delta_j),

the correct observable split is

    D_raw   = 2 - 2 Re(C),
    D_shape = 2 - 2|C|,
    D_coh   = 2(|C|-Re(C)),

with

    D_raw = D_shape + D_coh.

D_shape is intentionally global-U(1)-blind. It cannot by itself be used as a
uniform physical-twist observable.

Independent replay for scalar/generic-36D calibration:

    10/10 PASS.

## Typed BIVECTOR_OPERATOR_36 physical binding

A physically typed 36D orbital carrier has now been constructed in
noema-phasenav-core:

    rho_36(theta)=Lambda^2 R_xy(theta),

where R_xy is the ordinary physical SO(2) rotation embedded in (t,x,y,z), and
rho_36 is a 6x6 operator, represented by exactly 36 real coefficients.

Its generator is

    J_36=d/dtheta rho_36(theta)|_0,

with nonzero entries

    J[01,02]=-1,
    J[02,01]=+1,
    J[23,31]=-1,
    J[31,23]=+1.

Exact trace law:

    tr rho_36(theta)=2+4cos(theta).

Therefore

    D_biv36
      =[6-tr rho_36(theta)]/2
      =4sin^2(theta/2)
      =(a/L_M)^2.

The inverse is

    |theta|=arccos([tr rho_36-2]/4).

Independent replay:

    6/6 PASS

covering the trace identity, SO(2) group law, residual equality, graphene
length anchor, inverse map and J_36 generator structure.

## Current boundary

CLOSED:
- scalar physical Moire geometry calibration;
- generic 36D residual decomposition;
- explicit physical SO(2) axis for typed BIVECTOR_OPERATOR_36;
- exact physical twist <-> typed 36D trace <-> Moire length chain.

OPEN:
- identification of arbitrary legacy PhaseNav phi/aux_phi with
  BIVECTOR_OPERATOR_36;
- a validated adapter from generic PhaseNav 36D state to the typed bivector
  operator carrier;
- curvature/gravity interpretation;
- physical prime-force interpretation.

ARPL remains an exact arithmetic phase adapter. No physical prime-force claim
is inferred from this calibration.
