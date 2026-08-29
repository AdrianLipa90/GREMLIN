# GREMLIN Semantic Orbital Radial-Angular Factorization v0.5

Status: `CANDIDATE_ONLY / CHYBA / CURRENT_LIVE_FACTOR_SEPARATION_PASS`

## Purpose

This gate tests whether the current PhaseNav semantic mass coordinate and the live sevenfold orbital orientation behave as separate radial and angular coordinates.

It consumes:

- PNCS semantic-mass contract `PNV_SEMANTIC_MASS_V1` from PNCS head `7a54596c1794be29e0b85f5c363213cc81eb87d7`;
- GREMLIN C7 semantic-orbital bridge v0.1;
- GREMLIN RFC source-density winding bridge v0.4;
- the current live PhaseNav `NAME_MASS` and `ORBIT_VECTORS` ledgers on `/dev/shm/ciel_noema`.

The result is scoped to the current live realization set. It is not a universality claim for future PhaseNav realizations.

## 1. Exact PNCS semantic-mass source

PNCS `mass_v19.py` defines

\[
\kappa=\frac{\ln2}{24\pi},
\qquad
L_3=7,
\qquad
L_4=2,
\qquad
L_5=5,
\]

\[
\alpha_M=
\frac{1}{(L_3L_4)^2-L_3^2-L_4L_5+L_4^2\kappa},
\]

and

\[
R_k=
\left|
\frac1{36}\sum_{j=1}^{36}e^{i\theta_{k,j}}
\right|.
\]

The semantic-mass realization is

\[
\boxed{
m_k^{sem}
=\operatorname{round}\!\left[
\kappa(1+\alpha_M k)+\frac27R_k,
10
\right].
}
\]

The frozen runtime source digest is

`0b4df86cd01db313ea46ebac0eceee9cf6df0673391edd1a3fb2667c30464a32`.

The mass coordinate is an exact realization/integrity binding. Semantic naming authority remains the explicit content binding.

## 2. Constant-order-parameter theorem

Before final decimal rounding, if

\[
R_{k+1}=R_k,
\]

then exactly

\[
\boxed{
m_{k+1}-m_k=\kappa\alpha_M.}
\]

Numerically,

\[
\boxed{
\kappa\alpha_M
=6.708527814787997\times10^{-5}.
}
\]

The current 115-row live `NAME_MASS` ledger serializes one unique value

\[
R=0.228524
\]

for every card. Reconstructing the pre-serialization order parameter from the stored masses gives a range only

\[
0.22852419618110542
\le R_k\le
0.22852419655185932
\]

with population standard deviation approximately

\[
1.016\times10^{-10}.
\]

Thus the current realization set is extremely close to the constant-`R` branch at the stored precision.

## 3. Live radial progression

For the 115 current cards, the observed consecutive semantic-mass step has mean

\[
6.708527807017555\times10^{-5}
\]

and differs from `kappa*alpha_M` by only

\[
-7.77044\times10^{-14}.
\]

The maximum absolute residual from the arithmetic progression anchored at the first live mass is

\[
7.07539\times10^{-11}.
\]

The Pearson correlation between semantic mass and the explicit positive phase/card index is effectively unity at stored precision.

## 4. Independent C7 orientation coordinate

The orbital vectors are classified relative to live reference card `001` by the sevenfold shift

\[
\delta_7=\frac{2\pi}{7}.
\]

Current occupancy is

```text
n=0 : 39 cards
n=1 : 38 cards
n=2 : 19 cards
n=3 : 19 cards
n=4 : 0 cards
n=5 : 0 cards
n=6 : 0 cards
```

with maximum C7 lattice residual

\[
7.963\times10^{-9}\ \mathrm{rad}.
\]

On this live set,

\[
\operatorname{corr}(m_{sem},n_{C7})
=-0.023299453378\ldots
\]

while a linear model that already contains the phase index assigns the C7 index a coefficient only

\[
\boxed{2.69247\times10^{-12}.}
\]

This supports current-live factor separation between the radial semantic-mass progression and the C7 angular class.

## 5. Candidate product coordinate

On this scoped surface the semantic orbital may therefore be represented as the candidate pair

\[
\boxed{
\mathfrak O_k
=\bigl(m_k^{sem},\,e^{i\phi_{n,w}}\bigr)
}
\]

or equivalently by

\[
\boxed{z_k=m_k^{sem}e^{i\phi_{n,w}}.}
\]

Here the first coordinate carries the exact PNCS semantic-mass realization, while the second carries C7 orientation and winding/holonomy from the semantic-orbital bridge.

The statement is a factorized representation of the current live realization data. It does not assert statistical independence for every future mass model or PhaseNav basis.

## 6. Physical-mass firewall

`PNV_SEMANTIC_MASS_V1` supplies a dimensionless semantic realization coordinate. RF-S13 supplies a typed per-carrier energy

\[
\epsilon_\Psi=B\omega(\tilde\phi+\kappa).
\]

This gate does not identify

\[
m_{sem}=\epsilon_\Psi/c^2.
\]

A physical mass-energy crosswalk requires an independently sourced conversion scale or equivalent action/energy normalization and a universality test across admitted carriers.

## 7. Live receipt

`/dev/shm/ciel_noema/session/gremlin_semantic_orbital_radial_angular_factorization_live_v0_5.json`

File SHA-256:

`40026d74f66b640f45620e09b768344d2a3a18b1014e22288d237dc0082435f9`

## Authority

`runtime_execution_authority=false`

`canon_write_authority=false`

`promotion_state=CANDIDATE_ONLY`
