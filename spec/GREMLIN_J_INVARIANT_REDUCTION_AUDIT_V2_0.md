# GREMLIN / BELZEBUB J-Invariant Reduction Audit v2.0

Status: `CANDIDATE / STRUCTURAL IDENTIFIABILITY AUDIT`

## Question

v1.9 leaves

\[
J:H_I\to H_m\cong\mathbb C^3,
\qquad J\in U(3),
\]

underdetermined. v2.0 asks which existing invariant can reduce that freedom without introducing a new arbitrary continuous parameter.

## Stabilizer method

If two admissible intertwiners `J1` and `J2` preserve the same paired source/target observables, then

\[
K=J_2J_1^\dagger
\]

lies in their joint commutant. Identifiability is therefore controlled by the stabilizer of the paired invariant set.

For a Hermitian operator with eigenspace multiplicities `m_k`, the unitary stabilizer has real dimension

\[
\dim\operatorname{Stab}=\sum_k m_k^2.
\]

The baseline `U(3)` ambiguity has dimension 9.

## Candidate audit

### Nondegenerate neutrino mass spectrum

With

\[
M^2=\operatorname{diag}(0,\Delta m^2_{21},\Delta m^2_{31})
\]

and three distinct eigenvalues, the target-side commutant is

\[
U(1)^3.
\]

This reduction is **conditional**. A target-side spectrum alone does not constrain an arbitrary map from an unrelated source Hilbert space. One must also bind a source-side Hermitian operator `M_I` and require the intertwining contract

\[
M^2J=JM_I.
\]

Only after that contract is source-grounded does the nondegenerate spectrum reduce the ambiguity between valid intertwiners from `U(3)` to `U(1)^3`, or two relative phases after quotienting the common global phase. The current sources do not yet supply the required three-mode `M_I`/neutrino spectral matching.

### Symbolic resonant Hamiltonian

The July source already contains a spectral source-side operator class,

\[
H_{s,T}=\sum_n\omega_n|S_n\rangle\langle S_n|,
\qquad
\omega_n\propto\log\frac1{R(S_n,I)}.
\]

This is structurally relevant because it can supply source eigenprojectors. However, a three-mode slice and a source-derived spectral matching to the neutrino mass spectrum have not been derived. It is therefore a candidate source-side `M_I` class, not yet the missing intertwiner constraint.

### Relational Lambda holonomy v0.8

The current GREMLIN object is explicitly a `U1_PHASE_PROJECTION`. A scalar phase commutes with all of `U(3)` and gives no additional reduction.

### Neutrinotime Berry/metatime implementation

The source defines a metatime operator on the neutrino Hilbert space, which is structurally the right kind of object. However, the numerical pseudocode builds a 2x2 `T_op`, uses only `trace(T_op)` to construct a scalar `gamma`, and multiplies the full three-flavor propagator by `exp(i gamma)`. This is a common global phase and disappears from flavor probabilities.

Therefore the current implementation cannot select `J` and cannot by itself change flavor probabilities.

### Temporal chirality

`Neutrinotime14` supplies a pseudoscalar chirality diagnostic and Berry phase, but does not bind a non-scalar Hermitian 3x3 chirality operator to the neutrino mass basis. Even a binary chirality split with multiplicities `(2,1)` would leave `U(2)xU(1)`, of dimension 5.

### Resonance `R(S,I)`

The current source supplies scalar overlaps and scalar mass/resonance relations. Those data do not determine a complex linear three-component map `J`.

### Corrected EFT source routes

The corrected fermionic-intention EFT identifies non-conserved axial, scalar, boundary/topological, and mass/mixing-sector routes as nontrivial source classes. These are physically relevant mechanism classes, but the source does not yet provide the required source-bound 3x3 matrix in neutrino mass space.

## Conditional identifiability theorem

Assume first that a source-side `M_I` has been bound, has a matched nondegenerate spectrum, and `J` satisfies `M^2J=JM_I`. The ambiguity between such valid intertwiners is then

\[
D=\operatorname{diag}(e^{i\theta_1},e^{i\theta_2},e^{i\theta_3}).
\]

Now introduce a second paired, source-bound Hermitian operator `A_T` in the same mass basis. If the graph formed by the nonzero off-diagonal entries of `A_T` is connected, then

\[
D A_T D^\dagger=A_T
\]

forces equal phases on every connected edge. Connectivity therefore yields

\[
\theta_1=\theta_2=\theta_3,
\]

so the residual group is only global `U(1)`. Projectively, the ambiguity is zero-dimensional.

For three modes, only two connected off-diagonal edges are minimally required. A path support such as

\[
A_T\sim
\begin{pmatrix}
* & \times & 0\\
\times & * & \times\\
0 & \times & *
\end{pmatrix}
\]

is sufficient structurally.

## BELZEBUB verdict

Current state:

\[
\boxed{J\in U(3)\quad\text{still unresolved}.}
\]

Conditional chain:

\[
\boxed{
U(3)\xrightarrow{M_I\leftrightarrow M^2}U(1)^3,
\qquad
U(1)^3\xrightarrow{A_I\leftrightarrow A_T\;\text{connected}}U(1)_{\rm global}
}
\]

Both arrows are conditional theorems. The current state remains `U(3)` unresolved because the source-side `M_I` has not yet been bound. The July symbolic resonant Hamiltonian is structurally a plausible source-operator class, but its three-mode slice and spectral matching to the neutrino mass sector are not derived. After that first binding exists, a connected noncommuting second invariant would remove the remaining relative-phase ambiguity projectively.

The strongest next target is therefore a **paired source/target operator construction**, not another scalar phase. `Neutrinotime` already names an operator `T_hat(lambda)` on the neutrino Hilbert space, but its current numerical realization collapses to global `U(1)` and must be repaired before it can serve as the target side of the second intertwining constraint.
