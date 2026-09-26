# GREMLIN Typed T36 -> Bivector36 Adapter Audit
Date: 2026-09-26
Status: TYPED_PIPELINE_PASS / GENERIC_LEGACY_BINDING_BLOCKED_BY_DESIGN

## Result

The previous open gate

    legacy PhaseNav phi36 -> BIVECTOR_OPERATOR_36

has been split into two mathematically distinct questions.

### Generic legacy T36

Current PNCS authority states that generic PhaseNav T36 coordinates are phase
angles in an explicitly named basis, while the physical/semantic identity of
the individual 36 axes remains unassigned.

Therefore:

    generic PNV_T36_PHASE_ANGLES_RADIANS_V1
      -> BIVECTOR_OPERATOR_36

has no canonical adapter in the current evidence state.

The implementation fails closed.

### Typed Moire T36

A new candidate basis is defined:

    PNV_MOIRE_RELATIVE_PHASE_MATRIX6_ROW_MAJOR_V1.

Its 36 angles are row-major wrapped entries of the Lie-coordinate matrix

    X(theta)=theta J_36

on Lambda^2(R^4).

For two typed records:

    X_BA=wrap(B-A)

and

    theta_hat=<X_BA,J_36>_F/<J_36,J_36>_F.

Admission requires an explicit off-axis residual tolerance.

After admission:

    rho_36(theta)=Lambda^2 R_xy(theta)

and

    [6-tr rho_36]/2
      =4 sin^2(theta/2)
      =(a/L_M)^2.

## Validation

Executable adapter replay:

    10/10 PASS.

Includes:
- generic basis rejection;
- exact typed roundtrip;
- relative-angle recovery;
- layer swap;
- off-axis rejection;
- branch-cut rejection;
- graphene physical-length check;
- measured-period forward binding;
- impossible geometry rejection;
- malformed-dimension rejection.

A live generic phi snapshot with 36 finite angles was also tested and rejected
before physical conversion because the basis semantics are not typed.

## Engineering consequence

The typed physical chain is closed.

The remaining legacy/live issue is no longer "find a numerical transform".
It is a provenance question:

    prove a source-owned basis conversion
    OR
    keep generic live phi unbound.

No dimension-only bridge is permitted.
