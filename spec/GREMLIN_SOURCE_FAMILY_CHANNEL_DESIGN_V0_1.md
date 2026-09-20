# GREMLIN Source-Family Channel Design v0.1

Status: `CANDIDATE_EXPERIMENT_DESIGN_GATE / NULLSPACE_AWARE / NO_SOURCE_SELECTION`

This gate answers the next question after source-family identifiability:

> if the currently available observables do not separate the declared source families, which additional measurement channels are capable of breaking the degeneracy?

It does not claim experimental feasibility and it does not select a physical source.

## 1. Parent geometry

Let the current fit use the whitened source-signature matrix

[
A=L^{-1}S,
qquad
Sigma=LL^T,
]

with

[
Ainmathbb R^{m	imes p}.
]

Let

[
r=operatorname{rank}(A),
qquad
q=p-r.
]

The source-family nullspace has dimension

[
oxed{q=dimker A.}
]

## 2. One candidate measurement channel

A new scalar measurement channel has a declared source-family response row

[
mathbf c^Tinmathbb R^{1	imes p}
]

and positive uncertainty scale (sigma_c).

For a channel declared independent of the existing covariance block, define the whitened response

[
oxed{
mathbf w^T=rac{mathbf c^T}{sigma_c}.
}
]

The augmented design matrix is

[
widetilde A=
egin{bmatrix}
A\
mathbf w^T
end{bmatrix}.
]

A single scalar channel can increase rank by at most one:

[
oxed{
0le
operatorname{rank}(widetilde A)-operatorname{rank}(A)
le1.
}
]

## 3. Exact nullspace-breaking theorem

Let (V_0inmathbb R^{p	imes q}) have orthonormal columns spanning (ker A).

Then

[
oxed{
operatorname{rank}(widetilde A)=r+1
iff
mathbf w^T V_0
eq 0.
}
]

Equivalently, the new channel increases source-family rank iff its whitened source-response row has a non-zero projection onto the current nullspace.

A channel satisfying

[
mathbf w^T V_0=0
]

is **nullspace-blind**: it may improve precision inside the already resolved subspace, but it cannot remove the current exact degeneracy.

## 4. Multiple candidate channels

For (k) independent candidate channels stack the whitened rows into

[
Winmathbb R^{k	imes p},
]

and define

[
A_+=
egin{bmatrix}
A\
W
end{bmatrix}.
]

The total possible rank lift is

[
oxed{
operatorname{rank}(A_+)-r
=
operatorname{rank}(W V_0).
}
]

Therefore the current exact nullspace is completely removed iff

[
oxed{
operatorname{rank}(W V_0)=q.
}
]

This also gives the lower bound

[
oxed{
kge q
}
]

for scalar independent channels needed to remove a (q)-dimensional nullspace.

The lower bound is necessary, not sufficient: redundant new channels can fail to span the nullspace.

## 5. Conditioning after rank closure

When the current design is already full rank, or after enough channels close the exact nullspace, the next issue is conditioning.

For augmented singular values

[
	ildesigma_{max}gecdotsge	ildesigma_{min}>0,
]

define

[
kappa_2(A_+)
=
rac{	ildesigma_{max}}{	ildesigma_{min}}.
]

A channel may therefore be useful even when it adds no rank if it increases the smallest singular value or lowers the condition number.

The configured conditioning threshold remains a numerical policy parameter, not a physical constant.

## 6. Candidate-channel diagnostics

For each declared candidate channel GREMLIN reports:

- current rank;
- augmented rank;
- rank gain;
- nullspace projection norm;
- smallest singular value before/after;
- condition number before/after;
- whether the channel is:
  - `RANK_LIFTING`;
  - `NULLSPACE_BLIND`;
  - `CONDITION_IMPROVING`;
  - `NO_GEOMETRIC_GAIN`.

These labels describe the declared signature geometry only.

## 7. Greedy planning

GREMLIN may construct a deterministic greedy measurement plan.

At each step it chooses a remaining candidate channel by:

1. maximum rank gain;
2. then maximum augmented smallest singular value;
3. then minimum augmented condition number;
4. then lexicographic channel name as a deterministic tie-break.

This is a reproducible heuristic, not a proof of globally optimal experimental design.

The plan stops when:

- full rank is reached and the configured conditioning gate passes;
- no remaining channel improves rank/conditioning;
- or the configured channel budget is exhausted.

## 8. Provenance and independence gate

Every candidate channel must declare:

- channel name;
- source-family response vector and normalization;
- uncertainty scale;
- provenance;
- whether independence from the existing covariance block is assumed.

Version 0.1 admits only channels explicitly declared independent of the existing block.

Correlated new measurements require a future augmented-covariance extension and must fail closed here.

## 9. Routing semantics

If the current source-family state is `UNDERDETERMINED`:

- at least one rank-lifting candidate:
  [
  	exttt{PROPOSE_RANK_LIFTING_MEASUREMENT}
  ]
- no rank-lifting candidates:
  [
  	exttt{NO_AVAILABLE_CHANNEL_BREAKS_DEGENERACY}
  ]

If the state is `ILL_CONDITIONED`:

- a conditioning-improving candidate:
  [
  	exttt{PROPOSE_CONDITIONING_MEASUREMENT}
  ]

If the state is already `IDENTIFIABLE`, the channel-design result is optional precision planning only.

## 10. Firewalls

This gate does not establish:

[
	ext{recommended measurement}Rightarrow	ext{physical feasibility},
]

[
	ext{rank lift}Rightarrow	ext{true source},
]

[
	ext{condition improvement}Rightarrow	ext{physical source proof},
]

or any source-specific physical binding.

The exact admitted statement is:

[
oxed{
	ext{the declared candidate measurement does or does not add independent
source-family geometry under the declared covariance model.}
}
]

## 11. Parent and downstream links

Parent source-family identifiability:

https://github.com/AdrianLipa90/GREMLIN/pull/88

MAS source-family orchestration:

https://github.com/AdrianLipa90/PhaseNav-MAS-Upgrade/pull/12

FPDG staging authority:

https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph/pull/22
