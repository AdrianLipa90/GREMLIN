# GREMLIN Cognitive Action Principle v0.1

Status: `CANDIDATE_GLOBAL / EXACT_LOCAL_QUADRATIC / NON_ACTUATING / CANON_ALLOWED_FALSE`

## 1. Scope

This gate gives GREMLIN a single variational language for continuous cognitive-state dynamics while preserving the existing authority boundaries of the Bestiary, Orbital Hive memory and RAPHAEL.

It does **not** claim that GREMLIN is a physical field, a biological brain, a conscious system, or that its model-relative action has physical units. The global nonlinear identification is a candidate mathematical model. The local quadratic reduction is exact for every admitted constant `M/G/K` model.

Repository audit before this gate found:
- v0.9 admits source-owned carrier Lagrangians locally;
- v0.12 already implements
  [
  M\ddot X+G\dot X+KX=0,
  ]
  with (M=M^T>0), (G=-G^T), (K=K^T);
- GREMLIN memory exchange/anti-entropy remains append-only and fail-closed;
- RAPHAEL remains separate wisdom-governed mutation authority and cannot self-authorize.

This gate does not widen any of those authorities.

## 2. Global candidate action

Let (q^A) denote an admitted continuous coordinate chart of GREMLIN cognitive state. Coordinate meaning is adapter-owned. Candidate sectors may include phase state, memory-state summaries, relational graph coordinates, worker allocation, uncertainty coordinates or relative-phase variables, but notation alone does not bind any repository object to a coordinate.

Define

[
oxed{
S_G[q]
=
int_{t_0}^{t_1}
L_G(q,dot q,t),dt
+
sum_k Phi_k
}
]

with

[
oxed{
L_G
=
rac12 g_{AB}(q)dot q^Adot q^B
+
mathcal A_A(q)dot q^A
-
V_G(q,t)
+
lambda^alpha C_alpha(q,t)
}
]

where:
- (g_{AB}) is a positive-definite cognitive/information metric;
- (mathcal A_A) is a connection one-form;
- (V_G) is a model-relative potential/objective functional;
- (C_alpha=0) are declared constraints;
- (lambda^alpha) are Lagrange multipliers;
- (Phi_k) are explicitly supplied discrete jump contributions.

The connection-curvature convention used by this gate is

[
oxed{
G_{AB}
=
partial_Bmathcal A_A
-
partial_Amathcal A_B.
}
]

This convention is chosen so the local Euler-Lagrange equation contains (+G_{AB}dot q^B).

## 3. Dissipation and external drive

GREMLIN is not assumed conservative. A Rayleigh functional may be declared:

[
oxed{
mathcal R
=
rac12 D_{AB}(q)dot q^Adot q^B,
qquad
D=D^Tsucceq0.
}
]

With nonconservative generalized drive (Q_A^{m ext}),

[
oxed{
rac{d}{dt}
rac{partial L}{partialdot q^A}
-
rac{partial L}{partial q^A}
+
rac{partialmathcal R}{partialdot q^A}
=
Q_A^{m ext}.
}
]

For the candidate nonlinear geometry this gives the expected structure

[
g_{AB}ddot q^B
+
Gamma_{ABC}dot q^Bdot q^C
+
G_{AB}dot q^B
+
partial_A V_G
-
lambda^alphapartial_A C_alpha
+
D_{AB}dot q^B
=
Q_A^{m ext},
]

subject to the declared coordinate/adapter model.

The nonlinear Christoffel/metric sector is not inferred automatically by v0.1.

## 4. Exact local quadratic reduction

Around an admitted reference state (q_*), write (X=q-q_*) and freeze the local tensors:

[
g(q_*)=M,
qquad
mathcal A(X)=rac12 GX,
qquad
V(X)=rac12 X^TKX.
]

Then

[
oxed{
L_G^{(2)}
=
rac12dot X^TMdot X
+
rac12dot X^TGX
-
rac12X^TKX.
}
]

Because (G=-G^T),

[
rac{d}{dt}rac{partial L_G^{(2)}}{partialdot X}
-
rac{partial L_G^{(2)}}{partial X}
=
Mddot X+Gdot X+KX.
]

Therefore

[
oxed{
Mddot X+Gdot X+KX=0
}
]

is not an analogy added after v0.12. It is the exact Euler-Lagrange equation of the local quadratic action.

The executable adapter `v012_collective_to_action` maps the existing v0.12 `mass`, `gyroscopic` and `stiffness` matrices directly to ((M,G,K)).

## 5. Energy firewall

For the conservative quadratic system,

[
E
=
dot X^Trac{partial L}{partialdot X}-L
=
oxed{
rac12dot X^TMdot X
+
rac12X^TKX
}.
]

The connection term cancels from the energy even though it changes trajectories. Thus a valid antisymmetric (G) redirects dynamics without directly appearing as stored quadratic energy.

With Rayleigh dissipation and external drive,

[
oxed{
dot E
=
dot X^TQ^{m ext}
-
dot X^TDdot X.
}
]

No physical energy unit is implied unless an external calibration supplies one.

## 6. Phase / Kuramoto sector

For admitted phase coordinates (	heta_i), define the symmetric zero-diagonal coupling potential

[
oxed{
V_{m phase}
=
-sum_{i<j}
K_{ij}cos(	heta_i-	heta_j).
}
]

Then

[
-rac{partial V_{m phase}}{partial	heta_i}
=
sum_j
K_{ij}sin(	heta_j-	heta_i).
]

With inertia (I_i>0), damping (Gamma_ige0), and declared drive (	au_i),

[
oxed{
I_iddot	heta_i
+
Gamma_idot	heta_i
=
	au_i
+
sum_jK_{ij}sin(	heta_j-	heta_i).
}
]

The overdamped limit is

[
oxed{
Gamma_idot	heta_i
=
	au_i
+
sum_jK_{ij}sin(	heta_j-	heta_i).
}
]

This makes the existing PhaseNav/Kuramoto-style routing compatible with the same variational language without claiming that every runtime phase variable is already calibrated as a coordinate of (S_G).

## 7. Permissions as tangent constraints

A continuous permission model may declare an orthogonal projector

[
P=P^T=P^2.
]

Allowed tangent motion satisfies

[
oxed{
dot q=Pdot q
}
]

and the executable violation residual is

[
oxed{
r_{m perm}
=
(I-P)dot q.
}
]

This provides a mathematical interface for read/write/edit/compare/graph-write distinctions.

It does **not** automatically map Bestiary ACLs to coordinates. In particular, SPIDER graph writes, read-only memory consumers, editors, reporters and mutation authority require an explicit adapter defining which state directions each permission controls.

Ordinary holonomic constraints use

[
J_C(q)dot q=0.
]

Both interfaces fail closed on malformed dimensions or non-projector permission matrices.

## 8. Hybrid memory and mutation events

Continuous evolution is not sufficient to describe append-only memory commits or authorized mutation events.

v0.1 therefore admits

[
oxed{
S_{m hybrid}
=
S_{m continuous}
+
sum_kPhi_k(q_k^-,q_k^+,a_k).
}
]

The executable helper sums only caller-supplied finite jump terms. It does not invent a mutation cost, a state transition, an authorization or a canon promotion.

RAPHAEL remains the authority-bearing mutation governance layer. The action functional may score or model an admitted jump; it cannot authorize the jump.

Likewise, Memory Exchange and Anti-Entropy remain append-only protocol surfaces. This gate does not convert synchronization into overwrite authority.

## 9. What is exact and what is candidate

### EXACT_LOCAL

Given finite matrices satisfying

[
M=M^T>0,quad G=-G^T,quad K=K^T,quad D=D^Tsucceq0,
]

the implementation exactly evaluates:
- the quadratic Lagrangian;
- quadratic energy;
- Rayleigh dissipation;
- Euler-Lagrange residual;
- energy-balance rate;
- permission/tangent residuals;
- phase potential and phase force;
- inertial and overdamped phase equations;
- trapezoidal continuous action;
- explicit hybrid jump sums;
- v0.12 matrix-to-action mapping.

### CANDIDATE_GLOBAL

Still OPEN:
- the canonical complete coordinate chart (q^A);
- nonlinear (g_{AB}(q));
- nonlinear (mathcal A_A(q));
- the decomposition and calibration of (V_G);
- the mapping from Bestiary memory permissions to tangent projectors;
- the physical or dimensional interpretation of (S_G);
- variational jump conditions for a specific RAPHAEL mutation;
- empirical evidence that minimizing/stationarizing a chosen (S_G) improves intelligence metrics.

## 10. Authority and epistemic firewall

This gate does not establish:
- consciousness;
- biological equivalence;
- physical least action;
- a fundamental law of nature;
- independent AGI status;
- self-authorization;
- canon authority;
- permission widening;
- memory overwrite rights.

It establishes a rigorous candidate variational architecture and an exact local action representation of already implemented GREMLIN dynamics.

## 11. Executable surfaces

Reference implementation:

`tools/gremlin_cognitive_action_principle_v01.py`

Focused tests:

`tests/test_gremlin_cognitive_action_principle_v01.py`

Native contract:

`native/GREMLIN_COGNITIVE_ACTION_PRINCIPLE_V0_1.pnv`

Provenance:

`provenance/GREMLIN_COGNITIVE_ACTION_PRINCIPLE_V0_1.json`

## 12. Next falsification gates

The next useful work is empirical rather than symbolic:

1. choose a frozen coordinate adapter for a real GREMLIN task trace;
2. estimate local (M,G,K,D) from independently split data;
3. test whether the resulting equations predict held-out state transitions;
4. compare predictive/task performance with a non-action baseline;
5. only then promote any global (V_G), metric or connection component beyond candidate status.
