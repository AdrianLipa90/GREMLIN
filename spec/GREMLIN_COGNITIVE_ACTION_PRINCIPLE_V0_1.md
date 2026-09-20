# GREMLIN Cognitive Action Principle v0.1

Status: `CANDIDATE_ALGORITHMIC_ACTION / EXACT_LOCAL_VARIATIONAL_CLOSURE / PHYSICAL_ONTOLOGY_NOT_CLAIMED`

## Purpose

This gate gives GREMLIN an explicit variational description for the continuous part of its internal state dynamics and a typed composition rule for discrete state jumps.

"Cognitive" is used operationally: routing, memory, relation-state, phase-state, constraint and orchestration dynamics. This gate does not claim consciousness, biological cognition, or a physical law of nature.

## 1. Local quadratic action

For a local state displacement `q` and velocity `qdot`, declare

```
M = M^T > 0
G = -G^T
K = K^T
D = D^T >= 0
```

The conservative local Lagrangian is

```
L(q,qdot)
  = 1/2 qdot^T M qdot
  + 1/2 qdot^T G q
  - 1/2 q^T K q
  + f^T q.
```

Rayleigh dissipation is

```
R(qdot) = 1/2 qdot^T D qdot.
```

With external generalized force `Q_ext` and holonomic constraint Jacobian `J_C`, the executable residual is

```
M qddot + G qdot + K q + D qdot
- f - Q_ext - J_C^T lambda = 0.
```

For `D=0`, `Q_ext=0`, and time-independent parameters, the connection term does no work and the energy is

```
E = 1/2 qdot^T M qdot + 1/2 q^T K q - f^T q.
```

The exact power balance implemented by the gate is

```
dE/dt = qdot^T Q_ext - qdot^T D qdot.
```

## 2. Exact link to GREMLIN v0.12

The existing normal-mode form

```
M Xddot + G Xdot + K X = 0
```

is therefore the Euler-Lagrange equation of the local quadratic action above.

The adapter `v012_collective_to_action` consumes an object exposing the existing v0.12 fields

```
mass
gyroscopic
stiffness
```

and preserves them exactly as

```
metric
connection_curvature
stiffness.
```

No additional physical interpretation is introduced.

## 3. Phase/Kuramoto sector

For phase coordinates `theta_i` with symmetric off-diagonal coupling `K_ij`,

```
V_phase = - sum_{i<j} K_ij cos(theta_i-theta_j).
```

The exact generalized force is

```
F_i = - dV_phase/dtheta_i
    = sum_j K_ij sin(theta_j-theta_i).
```

The inertial dissipative phase equation is

```
I_i theta_i_ddot + Gamma_i theta_i_dot
= drive_i + F_i.
```

The executable overdamped limit is

```
theta_i_dot = (drive_i + F_i)/Gamma_i.
```

This is a Kuramoto-like algorithmic phase dynamics surface. It does not identify GREMLIN software phases with a physical oscillator substrate.

## 4. Permission geometry

Permissions are represented only after an explicit caller declaration.

For a boolean coordinate mask `a_i`, GREMLIN constructs

```
P = diag(a_i)
```

with `P^2=P=P^T`.

An admitted tangent velocity is

```
qdot_allowed = P qdot
```

and the forbidden tangent residual is

```
(I-P) qdot.
```

This provides a geometric representation of declared read/write/edit capabilities without inventing species permissions. Species-to-coordinate masks remain owned by their existing Bestiary / Hive / authority contracts.

In particular:
- SPIDER graph-writing semantics must be supplied by an explicit graph-coordinate mask;
- Hive memory remains `SHARED_COGNITION_ONLY`;
- this action gate cannot turn read access into write access;
- this action gate cannot grant production or canon authority.

## 5. Holonomic constraints

For declared constraints `C_alpha(q)=0`, the tangent condition is

```
J_C qdot = 0.
```

Lagrange multipliers contribute `-J_C^T lambda` to the executable Euler-Lagrange residual.

The gate validates dimensions and finite values and fails closed on malformed constraints.

## 6. Hybrid action

GREMLIN contains discrete events in addition to continuous evolution.

The minimal typed composition is

```
S_hybrid = integral L dt + sum_k Phi_k.
```

The continuous integral is provided by deterministic trapezoidal quadrature.

`Phi_k` terms are caller-owned finite scalars. The gate does not infer a mutation cost, reward or semantic meaning.

RAPHAEL remains the existing authority system for mutation. A jump term:
- is not an authorization;
- is not a decree;
- is not a mutation receipt;
- cannot bypass the external authority gate;
- cannot widen a declared mutation scope.

## 7. Global nonlinear extension

A future nonlinear action may use

```
S[q] = integral [
  1/2 g_AB(q) qdot^A qdot^B
  + A_A(q) qdot^A
  - V(q)
  + lambda^alpha C_alpha(q)
] dt
+ sum_k Phi_k.
```

v0.1 does not fabricate `g_AB(q)`, `A_A(q)`, or `V(q)` globally. It implements the exact local quadratic closure and exact phase/constraint/projector primitives from which such an extension can be tested.

## 8. Firewalls

PASS in this gate means:
- the local M/G/K dynamics has an exact variational representation;
- the antisymmetric connection changes the equation of motion but not the conserved quadratic energy;
- positive-semidefinite damping dissipates energy;
- declared permission masks define tangent projectors exactly;
- phase force is the negative gradient of the declared phase potential;
- discrete jump terms can be composed with the continuous action without granting authority.

PASS does not establish:
- consciousness;
- a biological nervous-system model;
- a physical substrate;
- a universal principle of cognition;
- a unique global GREMLIN Lagrangian;
- mutation authority;
- canon admission.

Implementation:
`tools/gremlin_cognitive_action_principle_v01.py`

Tests:
`tests/test_gremlin_cognitive_action_principle_v01.py`


## 9. Native NOEMA authority contract

The declarative native unit

`native/GREMLIN_COGNITIVE_ACTION_PRINCIPLE_V0_1.pnv`

binds this gate as:

`EPISTEMIC CHYBA / ANALYTIC_NON_ACTUATING / CANON_ALLOWED FALSE / AUTHORITY NONE / MUTATION_AUTHORITY RAPHAEL_ONLY`.

This is an authority firewall, not an execution program. It declares no new PNV opcodes and grants no write, mutation, publication or canon authority. Python remains the reference/test harness; runtime promotion would require a separate admitted authority path.
