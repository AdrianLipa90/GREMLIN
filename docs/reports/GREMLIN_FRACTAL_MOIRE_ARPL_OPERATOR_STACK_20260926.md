# GREMLIN Fractal-Moire / ARPL Operator Stack Audit 2026-09-26

Status: STACK_REFERENCE_PASS / HOSTED_CI_NOT_PRESENT / PHYSICAL_BINDING_OPEN

## 1. Scope

This audit joins the current candidate branches without promoting any of them
to main/canon.

Pinned candidate branches:

- Orbital-System-base:
  formalism/fractal-orbital-moire-hilbert-v0.5-20260926

- noema-phasenav-core:
  formalism/fractal-moire-hilbert-36d-bridge-v0.5-20260926

- On-Primes:
  integrate/arpl-fractal-orbital-bridge-v0.2-20260926-r2

All three are currently ahead of their selected parents with behind_by=0.

No main/master mutation is part of this audit.

## 2. Scale semantics now separated

The operator stack now distinguishes six non-equivalent cases.

### A. COMPRESSION_ONLY

Always-valid branch observable:

\[
\Delta_w
=
V_w^*\Delta V_w.
\]

No local unitarity is inferred.

### B. FIXED_BRANCH_UNITARY_INTERTWINER

Exact gate:

\[
RV_w=V_wR_w.
\]

Then

\[
V_w^*RV_w=R_w
\]

is unitary and

\[
V_w^*\Delta V_w
=
(I-R_w)^*(I-R_w).
\]

### C. BRANCH_PERMUTATION_UNITARY

Exact form:

\[
RV_i=V_{\sigma(i)}R_i.
\]

Global unitarity is preserved even though diagonal compression may vanish.

### D. CUNTZ_BLOCK_COCYCLE_UNITARY

For strong-separation Cuntz branches,

\[
\mathcal R=W^*RW
\]

is the exact unitary block matrix with

\[
\mathcal R_{ji}=V_j^*RV_i.
\]

The general law is

\[
RV_i
=
\sum_jV_j\mathcal R_{ji}.
\]

### E. OVERLAP_GRAM_COVARIANT

For overlapping branch embeddings,

\[
G=W^*W
\]

replaces the identity Gram.

Local orbital blocks descend to a unitary quotient action iff

\[
\boxed{
D^*GD=G.
}
\]

### F. UNITARY_DILATION

A separate global symmetry surface requiring an independently proved unitary
dilation/intertwiner.

An IFS does not imply this mode.

## 3. ARPL exact realization

ARPL supplies a concrete arithmetic source for two different operator layers.

### Refinement tower

\[
K_{h,N}\cong\mathbb Z/L_N\mathbb Z,
\qquad
L_{N+1}=b_NL_N.
\]

The uniform-Haar Hilbert spaces admit exact cross-level child isometries

\[
V_{N,c}^*V_{N,d}
=
\delta_{cd}I,
\]

\[
\sum_cV_{N,c}V_{N,c}^*
=
I.
\]

Thus the clock-refinement layer is a nonstationary Cuntz/Bratteli-style tower.

### Odometer carry cocycle

The exact one-step law is

\[
\boxed{
U_{N+1}V_{N,c}
=
V_{N,c}U_N(I-Q_N)
+
V_{N,c+1\bmod b_N}U_NQ_N.
}
\]

Independent replay over multiple L and b controls gave zero residual.

Therefore the ARPL odometer is not generically fixed-branch. It is a genuine
block/carry cocycle.

### Hit-cylinder overlap layer

ARPL independently supplies

\[
G_{pq}
=
m(C_p\cap C_q).
\]

After normalization,

\[
\widetilde G_{pq}
=
\frac{G_{pq}}{\sqrt{d_pd_q}}
\]

is exactly an overlap Gram matrix for normalized hit vectors.

Scalar local phases must satisfy

\[
e^{i(\theta_q-\theta_p)}
\widetilde G_{pq}
=
\widetilde G_{pq}.
\]

Hence nonzero overlap locks scalar phases together.

For the h=6 control set

\[
\{5,7,11,13,19\}
\]

the nonzero-overlap graph is connected, so one compatible scalar phase is
forced across the whole component.

This is a representation constraint, not a new prime-distribution theorem.

## 4. Exact no-go results retained

The current stack explicitly rejects:

- generic IFS refinement as a global unitary dilation;
- using D_w^{-1} for one-sided branch isometries;
- replacing V_w^* Delta V_w by a local-unitary mismatch without a covariance
  witness;
- inferring fixed-branch recursion from global unitarity;
- discarding off-diagonal Cuntz blocks in permutation/cocycle sectors;
- assuming local unitarity is sufficient under overlap;
- assigning independent scalar phases to connected maximally overlapping event
  channels;
- identifying a finite 36D vector with the full inverse-limit Hilbert state;
- treating ARPL prime phases as a physical Moire law without a source binding.

## 5. 36D contract state

The PhaseNav v0.5 contract can now represent:

- compression-only branch features;
- fixed-branch unitary intertwiners;
- branch permutations;
- general Cuntz block cocycles;
- the exact ARPL odometer carry subtype;
- overlap-Gram quotient covariance;
- separately proved global unitary dilations.

Every stronger interpretation requires explicit witness references and residual
checks.

The exact-36, information-loss and numerical-positivity firewalls remain
active.

## 6. Validation status

Reference/local independent checks passed for:

- Cuntz branch isometries;
- recursive fixed-branch covariance;
- prefix-swap permutation control;
- finite overlap Gram theorem;
- overlap null-vector no-go;
- Cuntz block reconstruction;
- ARPL refinement isometries;
- ARPL odometer carry;
- ARPL hit-cylinder overlap phase locking;
- 36D contract admission/failure surfaces.

GitHub combined-status queries for the current implementation heads returned no
hosted status checks.

Therefore:

HOSTED_CI = NOT_PRESENT.

No hosted-CI claim is made.

## 7. Current hard frontier

Mathematical representation is no longer blocked by ambiguity between scaling,
branching, overlap and orbital transport.

The remaining hard gates are now:

1. source-owned physical IFS / branch geometry;
2. physical orbital covariance or cocycle law;
3. source-owned mapping from ARPL arithmetic states into a physical PhaseNav
   36D state;
4. infinite-depth truncation/reconstruction theorem for the chosen 36D
   projection;
5. empirical calibration.

For pure mathematics, the next natural theorem is the infinite-depth operator
limit:

\[
\mathcal R^{(n)}
=
W_n^*RW_n
\]

and conditions under which the finite-depth block fields converge in an
operator topology or define a consistent inductive/projective system.

No physical interpretation is needed for that next gate.

canon_allowed = false.
