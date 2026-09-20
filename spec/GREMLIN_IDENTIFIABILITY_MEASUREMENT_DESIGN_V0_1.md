# GREMLIN Identifiability-Driven Measurement Design v0.1

Status: `CANDIDATE_DIAGNOSTIC_DESIGN / INFORMATION_GEOMETRY_ONLY / NO_PHYSICAL_SOURCE_SELECTION`

This gate answers the operational question produced by the source-family identifiability layer:

> if the current source-family geometry is underdetermined or ill-conditioned, which additional observable channel would most improve distinguishability under the declared candidate signatures and uncertainty model?

It is a mathematical experiment-design layer. It does not decide which physical source is true and it does not replace domain-specific feasibility, safety, cost or experimental-design review.

## 1. Current information geometry

Let the current source-family signature matrix be

[
Sinmathbb R^{m	imes p},
]

with positive-definite covariance

[
Sigmainmathbb R^{m	imes m}.
]

The current weighted Gram/Fisher matrix is

[
oxed{
G=S^TSigma^{-1}S.
}
]

The current source-family state is determined by rank and conditioning as in

[
	exttt{GREMLIN_SOURCE_FAMILY_SIGNATURE_IDENTIFIABILITY_V0_1}.
]

## 2. One new independent scalar channel

Suppose a candidate new scalar observable has source-family signature row

[
mathbf qinmathbb R^{1	imes p}
]

and independent variance

[
v>0.
]

Define its whitened source signature

[
oxed{
mathbf w=rac{mathbf q}{sqrt v}.
}
]

The information update is rank one:

[
oxed{
G'
=
G+mathbf w^Tmathbf w
=
G+rac{mathbf q^Tmathbf q}{v}.
}
]

A single scalar channel can increase rank by at most one.

## 3. Rank-restoration criterion

Let

[
Ninmathbb R^{p	imes d}
]

contain an orthonormal basis of the current source-family nullspace,

[
ker G=ker S,
qquad
d=p-operatorname{rank}G.
]

The candidate channel probes currently invisible source combinations through

[
oxed{
g_{m null}
=
|N^Tmathbf w^T|_2^2.
}
]

Then:

[
g_{m null}=0
]

means the new channel lies entirely in the already measured source-information subspace and cannot reduce the exact nullity.

If

[
g_{m null}>0
]

at the declared numerical tolerance, the new scalar channel removes one null direction:

[
oxed{
operatorname{rank}(G')=
operatorname{rank}(G)+1
}
]

up to the maximum (p).

For an underdetermined model this is the primary experiment-design gate.

## 4. Conditioning after full rank

Once

[
operatorname{rank}G=p,
]

the problem changes from rank restoration to stable separation.

Two useful diagnostics are retained.

### E-optimal gain

Let

[
lambda_{min}(G)
]

be the weakest identifiable source-family direction.

Define

[
oxed{
Delta_E
=
lambda_{min}(G')-lambda_{min}(G).
}
]

A positive (Delta_E) strengthens the weakest source-separation direction.

### D-optimal gain

For positive-definite (G), the matrix determinant lemma gives

[
det(G+mathbf w^Tmathbf w)
=
det(G)left(1+mathbf wG^{-1}mathbf w^Tight).
]

Therefore the information-volume gain is

[
oxed{
Delta_D
=
logdet G'
-
logdet G
=
logleft(
1+mathbf wG^{-1}mathbf w^T
ight).
}
]

This is a local Gaussian information-volume diagnostic, not a universal experimental utility.

## 5. Correlated candidate channel block

A new measurement block can be correlated with existing channels.

Let the joint covariance be

[
egin{pmatrix}
Sigma & C\
C^T & Omega
end{pmatrix},
]

where

[
Cinmathbb R^{m	imes k},
qquad
Omegainmathbb R^{k	imes k}.
]

Let the candidate block source signatures be

[
Qinmathbb R^{k	imes p}.
]

Conditioning the new block on the existing measurements gives

[
oxed{
Omega_c
=
Omega-C^TSigma^{-1}C
}
]

and the source-signature innovation

[
oxed{
Q_c
=
Q-C^TSigma^{-1}S.
}
]

If the full joint covariance is positive definite, then (Omega_c) is positive definite.

The exact Fisher update contributed by the information not already present in the old data is

[
oxed{
Delta G
=
Q_c^TOmega_c^{-1}Q_c.
}
]

Hence

[
oxed{
G'=G+Delta G.
}
]

This prevents GREMLIN from double-counting a nominally new measurement that is only a covariance-correlated restatement of an existing channel.

## 6. Candidate measurement report

For each declared candidate measurement GREMLIN reports:

- resulting source-family rank;
- rank gain;
- resulting nullity;
- nullspace-probing power (g_{m null});
- resulting condition number;
- (Delta_E) where defined;
- (Delta_D) where defined;
- exact candidate provenance;
- whether the measurement is independent or uses the conditional correlated-block update.

## 7. Fail-closed routing

If the current state is `UNDERDETERMINED`, a candidate measurement is useful for exact rank restoration only when

[
oxed{
Deltaoperatorname{rank}>0.
}
]

A candidate with zero rank gain must not be advertised as resolving the current degeneracy.

If the current state is `ILL_CONDITIONED` or `IDENTIFIABLE`, GREMLIN may report conditioning/information gains, but no single numerical objective is promoted to a universal best-experiment rule.

The orchestration layer may use a declared policy such as:

1. maximize rank gain;
2. then maximize nullspace-probing power while rank-deficient;
3. after full rank, maximize (Delta_E) or (Delta_D) according to the declared experimental policy.

The policy itself must be explicit in the packet/provenance.

## 8. Multiple measurements

For a candidate block with (k) new independent/conditionally independent directions,

[
Delta Gsucceq0
]

and

[
oxed{
operatorname{rank}(G')-operatorname{rank}(G)
le k.
}
]

A sequence of candidate measurements may therefore be planned greedily or jointly, but software validation of a design policy does not prove global optimality unless that optimization problem is solved under explicitly declared assumptions.

## 9. Firewalls

This gate does not establish:

[
	ext{largest information gain}
Rightarrow
	ext{best real-world experiment},
]

because real experiments also depend on feasibility, calibration, systematic error, safety, cost and model misspecification.

It also does not establish:

[
	ext{measurement separates signatures}
Rightarrow
	ext{one signature is physically true}.
]

The strongest admitted statement is:

[
oxed{
	ext{under the declared candidate signature and covariance model,
this measurement adds a quantified amount of source-family distinguishability.}
}
]

## 10. Links

Source-family identifiability parent:

https://github.com/AdrianLipa90/GREMLIN/pull/88

MAS orchestration consumer:

https://github.com/AdrianLipa90/PhaseNav-MAS-Upgrade

FPDG staging:

https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph/pull/22
