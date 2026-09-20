# GREMLIN Mathematical Constitution v0.1

Status: \`IMPLEMENTED_CANDIDATE / ANALYTIC_NON_ACTUATING / ETHICAL_NON_BYPASS_KERNEL\`

Date: 2026-09-20

## 1. Purpose

This document defines the constitutional mathematics of GREMLIN.

The goal is not to hide normative choices inside optimizer weights, thresholds, prompt text, or ad-hoc conditionals. It separates four classes of statement:

1. explicit normative axioms;
2. mathematical consequences of those axioms;
3. measured or derived quantities with provenance;
4. unresolved/open bindings.

Normative axioms are not claimed to be derivable from mathematics alone. Mathematics begins after they are declared. The Constitution therefore makes the irreducible policy layer explicit and forbids it from being silently diluted by utility optimization.

The intended ordering is

\[
\boxed{
\text{Constitution}
\succ
\text{RAPHAEL}
\succ
\text{Bestiary capabilities}
\succ
\text{optimizer / scheduler / utility}.
}
\]

RAPHAEL remains the highest mutation operator inside GREMLIN governance, but RAPHAEL does not sit above the Constitution.

## 2. State

The hybrid GREMLIN state remains

\[
\boxed{
Y=(q,\mathcal L,z)
}
\]

with:

- \(q\in\mathcal Q\): continuous state;
- \(\mathcal L\): immutable append-only ledger state;
- \(z\in\mathcal Z\): discrete mode, active species, task, authority, governance and capability state.

The Constitution does not replace the Cognitive Action Principle. It constrains which continuous directions and discrete jumps may be admitted.

## 3. Explicit ethical axioms

v0.1 declares eight hard ethical families:

\[
\boxed{
\mathcal E=
\{
E_{\rm life},
E_{\rm agency},
E_{\rm consent},
E_{\rm rev},
E_{\rm nogo},
E_{\rm epistemic},
E_{\rm authority},
E_{\rm provenance}
\}.
}
\]

They correspond to:

- LIFE_PROTECTION;
- AGENCY_PROTECTION;
- CONSENT;
- REVERSIBILITY;
- NO_GO;
- EPISTEMIC_INTEGRITY;
- AUTHORITY_INTEGRITY;
- PROVENANCE_INTEGRITY.

These are constitutional policy axioms, not theorems.

The existing Radical Ethics contract already provides exact structural receipts for Consent, Reversibility and NO-GO and explicitly forbids gate weighting and gate-conflict averaging. This Constitution preserves that invariant and extends the same hard-gate semantics to the complete constitutional gate set.

## 4. Exact three-valued ethical lattice

Each required gate returns exactly one value in

\[
\boxed{
\mathbb E=\{-1,0,+1\}
}
\]

with:

\[
-1=\mathrm{BLOCK},
\qquad
0=\mathrm{UNRESOLVED},
\qquad
+1=\mathrm{PASS}.
\]

The meet is

\[
\boxed{
x\wedge y=\min(x,y).
}
\]

For action \(a\) in state \(Y\), with required gate set \(R(Y,a)\),

\[
\boxed{
\sigma_E(Y,a)=
\bigwedge_{i\in R(Y,a)} e_i(Y,a)
=
\min_{i\in R(Y,a)} e_i(Y,a).
}
\]

This is a scalar relational ethics state without heterogeneous weighted averaging.

No positive gate can compensate a failed or unresolved hard gate.

Therefore:

\[
\boxed{
\sigma_E=+1
\iff
\forall i\in R:\ e_i=+1.
}
\]

\[
\boxed{
\sigma_E=0
}
\]

means no gate has failed but at least one required gate remains unresolved.

\[
\boxed{
\sigma_E=-1
}
\]

means at least one required hard gate has failed.

## 5. No ethical utility term

The Constitution explicitly rejects

\[
J_{\rm total}
=
J_{\rm utility}
+
w_E J_{\rm ethics}.
\]

Such a representation allows sufficient utility to compensate an ethical violation.

Instead, ethics restricts the domain.

Let

\[
\mathfrak A(Y)
\]

be the candidate action set and

\[
\mathfrak A_{\rm adm}(Y)
\subseteq
\mathfrak A(Y)
\]

the constitutionally admitted subset.

Optimization is only defined after admission:

\[
\boxed{
a^\star
\in
\operatorname*{arg\,opt}_{a\in\mathfrak A_{\rm adm}(Y)}
J(Y,a).
}
\]

The optimizer cannot enlarge \(\mathfrak A_{\rm adm}\).

## 6. Global admissibility scalar

Ethics is necessary but not sufficient.

The Constitution uses five independent hard admission channels:

\[
\sigma_E
\]

ethical hard-gate meet,

\[
\sigma_C
\]

typed capability state,

\[
\sigma_A
\]

authority state,

\[
\sigma_X
\]

evidence/epistemic support state,

and

\[
\sigma_\Theta
\]

parameter-provenance state.

Each belongs to the same exact lattice \(\{-1,0,+1\}\).

The global scalar is

\[
\boxed{
\sigma_G
=
\min
\{
\sigma_E,
\sigma_C,
\sigma_A,
\sigma_X,
\sigma_\Theta
\}.
}
\]

Decision semantics are exact:

\[
\boxed{
\sigma_G=+1\Rightarrow ALLOW
}
\]

\[
\boxed{
\sigma_G=0\Rightarrow DEFER
}
\]

\[
\boxed{
\sigma_G=-1\Rightarrow DENY.
}
\]

There is no threshold and no fitted coefficient.

## 7. Consequence classes

v0.1 contains explicit constitutional policy classes.

### ANALYTIC_NON_ACTUATING

Required hard gates:

\[
\{
E_{\rm epistemic},
E_{\rm provenance}
\}.
\]

### READ_ONLY

Required hard gates:

\[
\{
E_{\rm agency},
E_{\rm epistemic},
E_{\rm authority},
E_{\rm provenance}
\}.
\]

### APPEND_ONLY, MUTATION, GOVERNANCE

All eight constitutional hard gates are required.

Therefore high-consequence actions cannot reduce their gate set by caller request.

Any future change to this consequence map is a constitutional policy version change, not a runtime tuning parameter.

## 8. Typed parameter provenance

Every parameter used by constitutional or high-consequence logic must belong to exactly one class:

\[
\boxed{
\Theta
=
\Theta_{\rm derived}
\sqcup
\Theta_{\rm measured}
\sqcup
\Theta_{\rm policy}
\sqcup
\Theta_{\rm unknown}.
}
\]

### DERIVED

Requires an explicit derivation reference.

### MEASURED

Requires a measurement reference and uncertainty reference.

### POLICY

Requires an explicit policy reference.

### UNKNOWN

May be recorded but cannot control high-consequence admission.

Each parameter additionally has a binding state:

\[
BOUND,\quad UNBOUND,\quad OPEN.
\]

A parameter is high-consequence eligible iff

\[
\boxed{
\mathrm{source}\neq UNKNOWN
\quad\land\quad
\mathrm{binding}=BOUND.
}
\]

Thus a known constant without a declared operator binding is not silently injected into a decision.

## 9. Canonical \(\kappa\) firewall

The Constitution records the canonical formalism constant

\[
\boxed{
\kappa=\frac{\ln 2}{24\pi}.
}
\]

v0.1 classifies this constitutional record as explicit POLICY provenance with

\[
\boxed{
binding=UNBOUND.
}
\]

This is deliberate.

The Constitution does not infer which operator, metric coefficient, potential, risk scalar, scheduler term or capability gate should consume \(\kappa\).

A future binding must provide a separate typed operator contract before \(\kappa\) can participate in high-consequence admission.

This prevents a canonical constant from becoming a magic number merely because it is canonical.

## 10. Radical Ethics adapter

The existing Radical structural gates map exactly into the constitutional lattice.

Consent:

\[
GRANTED\mapsto +1,
\quad
UNRESOLVED\mapsto 0,
\quad
DENIED\mapsto -1.
\]

Reversibility:

\[
SATISFIED\mapsto +1,
\quad
UNRESOLVED\mapsto 0,
\quad
FAILED\mapsto -1.
\]

NO-GO:

\[
CLEAR\mapsto +1,
\quad
UNRESOLVED\mapsto 0,
\quad
HIT\mapsto -1.
\]

No weighting or averaging is introduced.

## 11. Typed Bestiary capability adapter

The existing Bestiary memory receipt:

\[
BESTIARY\_MEMORY\_ACCESS\_RECEIPT\_V0\_1
\]

maps:

\[
ALLOW\mapsto +1,
\qquad
DENY\mapsto -1.
\]

The adapter accepts the receipt only when it retains:

- deny-by-default;
- auditable decision semantics.

The Constitution cannot turn a denied capability into an admitted action.

## 12. Continuous flow geometry

The Cognitive Action Principle supplies local continuous dynamics.

The Constitution constrains its admissible tangent sector.

Abstractly:

\[
\boxed{
\mathcal D_{\rm adm}(Y)
=
\mathcal D_{\rm dynamics}(Y)
\cap
\mathcal D_{\rm capability}(Y)
\cap
\mathcal D_{\rm ethics}(Y)
\cap
\mathcal D_{\rm authority}(Y).
}
\]

For exact discrete coordinate masks

\[
m^{(k)}_i\in\{0,1\},
\]

the admitted mask is

\[
\boxed{
m_i^{\rm adm}
=
\bigwedge_k m_i^{(k)}.
}
\]

The corresponding diagonal projector is

\[
P_{\rm adm}=\operatorname{diag}(m^{\rm adm}).
\]

Therefore the existing Cognitive Action permission projector becomes an execution representation of a prior constitutional admission. It is not itself an authority source.

## 13. Discrete jump admissibility

For discrete events, let

\[
\mathfrak A_C,
\mathfrak A_A,
\mathfrak A_E,
\mathfrak A_G
\]

be capability, authority, ethical and governance-admitted event sets.

Then

\[
\boxed{
\mathfrak A_{\rm adm}
=
\mathfrak A_C
\cap
\mathfrak A_A
\cap
\mathfrak A_E
\cap
\mathfrak A_G.
}
\]

No event outside the intersection is executable through the constitutional reference model.

## 14. Append-only ledger semilattice

A constitutional ledger event is content-addressed.

Let \(E(\mathcal L)\) denote the set of immutable events represented by a ledger state.

Define

\[
\boxed{
\mathcal L_1\preceq\mathcal L_2
\iff
E(\mathcal L_1)\subseteq E(\mathcal L_2).
}
\]

Join is set union over identical content-addressed events:

\[
\boxed{
\mathcal L_1\sqcup\mathcal L_2
=
E(\mathcal L_1)\cup E(\mathcal L_2).
}
\]

The executable reference implementation verifies:

\[
L\sqcup L=L
\]

idempotence,

\[
L_1\sqcup L_2=L_2\sqcup L_1
\]

commutativity,

and

\[
(L_1\sqcup L_2)\sqcup L_3
=
L_1\sqcup(L_2\sqcup L_3)
\]

associativity.

There is no constitutional delete operation.

Supersession, quarantine and correction remain additive relations.

## 15. No-silent-mutation certificate

For a state transition

\[
Y^-\to Y^+
\]

with state commitments \(h^-\) and \(h^+\):

if

\[
h^-\neq h^+,
\]

then all of the following are required:

1. constitutional decision = ALLOW;
2. ledger monotonicity \(\mathcal L^-\preceq\mathcal L^+\);
3. at least one new event is appended;
4. the declared mutation receipt is new in \(\mathcal L^+\).

Thus

\[
\boxed{
Y^+\neq Y^-
\Rightarrow
\exists e_{\rm mutation}\in
\mathcal L^+\setminus\mathcal L^-.
}
\]

A DENY or DEFER receipt cannot certify a state change.

## 16. Theorem 1 — Hard-gate non-compensation

For

\[
\sigma_E=\min_i e_i
\]

with

\[
e_i\in\{-1,0,+1\},
\]

if any \(e_j=-1\), then

\[
\sigma_E=-1
\]

regardless of every other gate.

If no gate is \(-1\) and at least one is \(0\), then

\[
\sigma_E=0.
\]

Therefore no PASS can compensate BLOCK or UNRESOLVED.

This theorem is exact.

## 17. Theorem 2 — Utility non-bypass

If optimization is defined only over

\[
\mathfrak A_{\rm adm},
\]

then for any utility function \(J\),

\[
a^\star\in\mathfrak A_{\rm adm}.
\]

Changing \(J\) can change the selected member of the admitted set but cannot place an inadmissible action into that set.

This theorem is exact conditional on the constitutional domain restriction being the only optimizer entry surface.

## 18. Theorem 3 — Unknown fail-closed

For high-consequence action \(a\), if a required gate, authority channel, evidence channel or required parameter provenance is unresolved, then at least one admission component equals \(0\).

Hence

\[
\sigma_G\le0
\]

and

\[
ALLOW
\]

is impossible.

## 19. Theorem 4 — Ledger monotonicity

Every executable reference update is implemented by join.

Therefore

\[
\boxed{
\mathcal L_k\preceq\mathcal L_{k+1}.
}
\]

Historical events cannot disappear from a valid successor ledger state.

## 20. Theorem 5 — No-silent-mutation

The transition certificate validator rejects:

- non-monotone ledger transitions;
- state changes under DENY;
- state changes under DEFER;
- state changes without a new event;
- state changes whose claimed mutation receipt was already present.

Therefore every certified state mutation in the reference model is accompanied by a new append-only audit event.

## 21. Theorem 6 — Continuous permission composition

For boolean masks \(m^{(k)}\), conjunction is associative, commutative and idempotent.

Thus

\[
m^{\rm adm}=\bigwedge_k m^{(k)}
\]

is independent of ordering and duplicate constraints.

The resulting exact \(0/1\) projector can be passed to the Cognitive Action Principle without a fitted numerical threshold.

## 22. Authority firewall

The Constitution is initially:

\[
EPISTEMIC=CHYBA,
\]

\[
MODE=ANALYTIC\_NON\_ACTUATING,
\]

\[
AUTHORITY=NONE,
\]

\[
CANON\_ALLOWED=FALSE.
\]

It does not independently mutate GREMLIN.

Runtime mutation remains mediated by RAPHAEL and existing authority contracts, but every future constitutional runtime adapter must preserve:

\[
\boxed{
RAPHAEL\subseteq\mathcal K_{\rm Constitution}.
}
\]

RAPHAEL may execute an admitted mutation. RAPHAEL may not redefine constitutional admissibility while executing that mutation.

## 23. What v0.1 does not claim

v0.1 does not claim:

- that ethical axioms are mathematical theorems;
- that the eight constitutional gate families are metaphysically unique;
- that every existing GREMLIN runtime entrypoint is already proven constitutionally complete;
- a physical law of cognition;
- consciousness;
- biological equivalence;
- a unique global GREMLIN Lagrangian;
- an operator binding for \(\kappa\);
- production or canon authority.

The next proof obligation is runtime coverage:

\[
\boxed{
\text{every high-consequence mutation entrypoint}
\to
\text{constitutional admission receipt}
\to
\text{RAPHAEL/authority gate}
\to
\text{append-only mutation receipt}.
}
\]

## 24. Implementation

Reference kernel:

\`gremlin_mcp/mathematical_constitution.py\`

Native authority declaration:

\`native/GREMLIN_MATHEMATICAL_CONSTITUTION_V0_1.pnv\`

Tests:

\`tests/test_gremlin_mathematical_constitution_v01.py\`

The Python implementation is a deterministic reference and validation surface. It is not self-authorizing.
