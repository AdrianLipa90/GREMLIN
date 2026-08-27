# GREMLIN Lambda → Maximally Symmetric Spin Geometry v0.10

Status: **IMPLEMENTATION CANDIDATE** pending CI.

## Purpose

v0.10 closes the next provenance gap in the relational phase chain. The connection projection used by QHTRI is generated from a declared geometry law rather than supplied as an independent phase-lag input.

The implemented calibration chain is:

`Lambda_R -> effective source energy -> K_R -> metric -> tetrad -> torsion-free spin connection -> curvature-excess holonomy -> spin-1/2 U(1) projection -> QHTRI tau -> epsilon`.

## Declared Einstein calibration

For the local maximally symmetric calibration family,

`K_R = Lambda_R / 3`,

which is the four-dimensional maximally symmetric Einstein relation `R_mn = Lambda_R g_mn`, equivalently `R_4 = 4 Lambda_R` and sectional curvature `K_R = Lambda_R/3`.

The geometry adapter uses the two-dimensional constant-curvature section

`ds^2 = dr^2 + S_K(r)^2 dphi^2`,

with

- `S_K(r)=sin(sqrt(K) r)/sqrt(K)` for `K>0`;
- `S_0(r)=r`;
- `S_K(r)=sinh(sqrt(-K) r)/sqrt(-K)` for `K<0`.

This is a declared calibration ansatz and is content-bound in every receipt.

## Tetrad and connection

The orthonormal coframe is

`e^r = dr`,

`e^phi = S_K(r) dphi`.

The torsion-free Cartan equation

`de^a + omega^a_b wedge e^b = 0`

gives the polar-frame connection coefficient

`omega^(r phi) = -S_K'(r) dphi`.

The ordinary polar frame rotates even when `K=0`. v0.10 therefore binds and removes the flat polar gauge baseline `-dphi`. The curvature-excess connection is

`omega_curv = (1 - S_K'(r)) dphi`.

Consequently the physical vector holonomy around the circle is

`Phi_vector = 2*pi*(1-S_K') = K*A_disk`.

This is the constant-curvature Stokes/Gauss-Bonnet closure used as the geometric firewall.

## Spin-1/2 projection

For the spin-1/2 phase lane the projected connection is half the curvature-excess rotation:

`A_half = 1/2 * omega_curv`.

Along a circle of circumference `2*pi*S_K(r)`, the tangential projection is

`A_half_parallel = (1-S_K')/(2*S_K)` radians per metre,

and therefore

`tau_half = integral A_half_parallel ds = pi*(1-S_K') = Phi_vector/2`.

The flat limit is exactly `tau_half=0`.

## QHTRI closure

The derived spin-half connection is passed into the v0.9 path-integral layer. v0.9 then computes the path phase and the existing QHTRI relation

`epsilon = wrap_pi(n*theta_i - m*theta_j - tau_half)`.

The exact integer winding pair `(n,m)` remains the operator identity.

`manual_tau_present=false` is sealed through the v0.10 -> v0.9 -> v0.8 lineage.

## Energy and geometry meaning

v0.8 supplies the effective-source energy density associated with `Lambda_R` in SI units. v0.10 uses the declared maximally symmetric Einstein calibration to map that same bound `Lambda_R` into curvature. Thus the source-energy and geometry branches remain connected by one content-addressed lineage.

## Validation frontier

v0.10 establishes a reproducible geometry-to-phase calibration lane. A general relational field `Lambda_R(x)` requires a dynamic field equation, boundary/initial conditions, and a metric solver before the maximally symmetric calibration can be replaced by a general geometry solution.

Quantum entanglement remains at `OPEN_REQUIRES_JOINT_QUANTUM_WITNESS`. Promotion requires an explicitly constructed joint quantum state and a non-separability witness.

## Tests

The v0.10 suite checks:

- exact flat limit and removal of the polar-frame gauge rotation;
- `K=Lambda_R/3`;
- `R_4=4 Lambda_R` and `R_2=2K`;
- positive- and negative-curvature section functions;
- Stokes curvature-area holonomy closure;
- spin-half factor `1/2`;
- cosmological-scale numerical evaluation on cosmic radii;
- positive-curvature antipode guard;
- tetrad/connection commitment tamper detection;
- connection projection -> path integral -> QHTRI tau closure;
- preservation of exact winding identity;
- joint-quantum-witness firewall.
