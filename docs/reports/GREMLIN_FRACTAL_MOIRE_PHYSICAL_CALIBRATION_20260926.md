# GREMLIN Fractal Moire Physical Calibration
Date: 2026-09-26
Status: CALIBRATION_PASS_WITH_OPEN_36D_PHYSICAL_BINDING

## Calibrated identity

For the scalar relational operator

    d(theta)=4 sin^2(theta/2)

and identical-lattice Moire geometry

    L_M=a/[2 sin(|theta|/2)],

the exact physical calibration is

    d=(a/L_M)^2.

In reciprocal space this is equivalently

    sqrt(d)=Delta K/K=a/L_M.

No free fitted parameter is introduced by this identity.

## External anchors

Graphene lattice constant used by the cited STM literature:

    a=0.246 nm.

Published geometry checks:
- Luican et al. 2011: L=0.65 +/- 0.05 nm, reported theta=21.8 +/- 1.7 deg;
  model inversion theta=21.8158 deg -> PASS.
- Luican et al. 2011: L=4.0 +/- 0.2 nm, reported theta=3.5 +/- 0.3 deg;
  model inversion theta=3.52425 deg -> PASS.
- Tilak et al. 2021: L=12.6 nm, reported theta=1.12 deg;
  model inversion theta=1.11865 deg -> PASS.

References:
- A. Luican et al., Physical Review Letters 106, 126802 (2011),
  DOI 10.1103/PhysRevLett.106.126802.
- N. Tilak et al., Nature Communications 12, 4180 (2021).

## 36D correction discovered during calibration

For

    C=(1/36) sum_j exp(i delta_j),

the correct observable split is

    D_raw   = 2 - 2 Re(C),
    D_shape = 2 - 2|C|,
    D_coh   = 2(|C|-Re(C)),

with

    D_raw = D_shape + D_coh.

The earlier projective residual D_shape is intentionally global-U(1)-blind and
therefore returns zero for a uniform common phase shift. It cannot by itself be
used as a uniform physical-twist observable.

This is a substantive calibration correction, not a numerical tuning.

## Validation

Independent local replay:

    10/10 checks PASS.

Includes:
- three published STM anchors;
- scalar forward/inverse mapping;
- residual-period exact identity;
- quotient blind-spot control;
- 36D decomposition;
- zero and layer-swap controls;
- a byte-matched live NOEMA decomposition identity.

## Remaining gate

Physical 36D calibration requires a typed orbital representation

    rho_36 : SO(2) -> End(V_36)

or generator J_36 with

    rho_36(theta)=exp(theta J_36).

Until this exists, live PhaseNav 36D coordinates cannot honestly be converted
to nm, reciprocal length, strain, energy, curvature or gravity.

ARPL remains an exact arithmetic phase adapter. No physical prime-force claim
is inferred from this calibration.
