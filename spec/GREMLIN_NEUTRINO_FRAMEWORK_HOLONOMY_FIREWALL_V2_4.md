# GREMLIN / BELZEBUB Neutrino Framework Holonomy Firewall v2.4

Status: `CANDIDATE / CROSS-FRAMEWORK CONFLICT AUDIT`

## Why this firewall exists

Two source branches currently assign incompatible structural neutrino mass ratios.

The graded-projection branch states

\[
\frac{m_2}{m_1}=\sqrt{\frac76}.
\]

The TIR/Metatime NOEMA tetrahedron branch states the neutrino signature

\[
r=[1,2,10],
\]

so in that branch

\[
\frac{m_2}{m_1}=2.
\]

These cannot both be exact descriptions of the same ordered mass spectrum.

## Branch A — graded projection

Using `(m2/m1)^2=7/6` with the declared GREMLIN mass-squared splittings gives

\[
m_1^2=6\Delta m^2_{21},\qquad
m_2^2=7\Delta m^2_{21},\qquad
m_3^2=m_1^2+\Delta m^2_{31}.
\]

For the v2.2 inputs this gives approximately

\[
(m_1,m_2,m_3)=(21.10,22.79,54.43)\,\mathrm{meV}
\]

and

\[
\sum m_\nu\approx98.316\,\mathrm{meV}.
\]

v2.4 preserves this as an internally consistent candidate **inside that branch**.

## Branch B — TIR / NOEMA tetrahedron

The Metatime monograph gives

\[
r=[1,2,10]
\]

and separately displays

\[
(m_1,m_2,m_3)=(5.01,10.02,50.1)\,\mathrm{meV},
\]

with sum about `65.13 meV`.

As a ratio-only control, normalizing `[1,2,10]` to the same `Delta m21^2` used by GREMLIN yields

\[
m_1=\sqrt{\Delta m^2_{21}/3},\quad m_2=2m_1,\quad m_3=10m_1,
\]

and therefore the exact branch prediction

\[
\Delta m^2_{31}=33\,\Delta m^2_{21}.
\]

For `Delta m21^2=7.42e-5 eV^2`, this is `2.4486e-3 eV^2`, about 2.72% below the v2.2 `2.517e-3 eV^2` input.

## Holonomy verdict

The conflict is structural, not a rounding difference:

\[
2\ne\sqrt{7/6}.
\]

Therefore no single absolute neutrino spectrum may be promoted across both research branches without a declared relation between them.

v2.2 is not revoked. Its correct scope is retained as

`VALID_ONLY_WITHIN_GRADED_PROJECTION_BRANCH_NOT_PROMOTED_ACROSS_TIR`.

The tetrahedron spectrum is likewise retained as its own candidate branch.

## Relation to the v2.3 bridge

The complex-overlap construction

\[
J_m=U_{\rm PMNS}^\dagger C_\nu
\]

remains mathematically valid and does not depend on choosing either absolute mass spectrum merely to define the frame map. However, any future source-spectrum intertwining `M^2 J = J M_I` must remain explicitly branch-qualified until the spectrum conflict is resolved.

## Resolution routes

A shared promotion requires at least one of:

1. an explicit transformation, limit, or scale-dependent relation deriving one ratio law from the other;
2. a provenance-bearing supersession/authority rule;
3. an empirical discriminant, with both branches retained until the discriminating test is resolved.

## BELZEBUB verdict

\[
\boxed{\text{HARD FRAMEWORK BRANCH CONFLICT — no shared absolute neutrino-scale canon promotion}.}
\]
