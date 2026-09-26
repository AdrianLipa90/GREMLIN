# GREMLIN GL(3) Deformation / Moire Calibration Audit
Date: 2026-09-26
Status: TYPED_GL3_GEOMETRY_PASS

## Core result

The physical 36-coefficient carrier extends from rotations to arbitrary
invertible affine spatial deformation:

    rho_36(F)
      =Lambda^2 diag(1,F)
      =diag(F,det(F)F^{-T}).

This is exact in the declared bivector basis.

The representation is self-checking:
- upper 3x3 block = F;
- lower 3x3 block = cof(F);
- off blocks = 0.

## Planar Moire result

For layer deformation F_2 relative to direct lattice A:

    Delta B=(F_2^{-T}-I)(2pi A^{-T}),

    A_M=2pi(Delta B)^{-T}.

Therefore twist, lattice mismatch, anisotropic strain and shear are one
geometric mismatch problem rather than separate ad-hoc formulas.

Special cases:
- rotation -> L_M=a/[2sin(|theta|/2)];
- isotropic scale s -> L_M=|s/(s-1)|a for primitive lengths.

Independent replay:

    7/7 PASS.

## Current frontier

The geometry layer is now closed through affine GL(3).

What remains beyond it is genuinely dynamical:
- constitutive/elastic energy;
- spatially varying F(x);
- defects and dislocations;
- full GL(4)/coframe dynamics;
- curvature/evolution equations.

Those should be added as separate typed layers, not folded into the geometric
carrier.
