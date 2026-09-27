# GREMLIN Spatial SO(3) Bivector36 Calibration Audit
Date: 2026-09-26
Status: TYPED_SPATIAL_SO3_PASS

## Result

The physical orbital carrier has been generalized from the planar SO(2)
subgroup to full spatial SO(3).

For R in SO(3):

    rho_36(R)=Lambda^2 diag(1,R)=diag(R,R)

in the basis

    (01,02,03,23,31,12).

Lie algebra:

    J_36(omega)=diag([omega]_x,[omega]_x),

with the standard so(3) commutators.

Invariant:

    tr rho_36=2+4cos(theta),

    [6-tr rho_36]/2=4sin^2(theta/2).

A typed log-phase source basis

    PNV_SPATIAL_SO3_LOG_PHASE_MATRIX6_ROW_MAJOR_V1

encodes the full three-component principal rotation vector. Generic legacy T36
is not retyped.

Independent replay:

    8/8 PASS.

## Structural consequence

The 36-coefficient physical orbital layer now has a precise interpretation:
not 36 independent directions, but a 6x6 representation of spatial rotation
on bivectors, decomposing into two equivalent 3D rotation blocks.

The prior physical Moire calibration is the special case where the rotation
axis is the common normal of the two planar layers.

## Next mathematical frontier

The next larger carrier is not another arbitrary 36D remapping. It is the
controlled extension from SO(3) rotations to:
- strain/shear via GL(3) or GL(4);
- Lorentz/coframe sector via the already explored exterior-square GL(4)
  machinery;
- fractal scale action coupled as a separate commuting/noncommuting generator
  with explicitly tested algebra.

No such extension is promoted by this receipt.
