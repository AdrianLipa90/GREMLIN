# GREMLIN / BELZEBUB Neutrino Absolute-Scale Cross-Check v2.2

Status: `CANDIDATE / CROSS-SOURCE INTERNAL CONSISTENCY TEST`

## Input structure

A later framework document states the structural neutrino ratio

\[
\frac{m_2}{m_1}=\sqrt{\frac76}
\]

and separately declares normal ordering with

\[
\sum_i m_i = 98\;\mathrm{meV}.
\]

v2.2 does not use the declared 98 meV sum to derive the masses. It combines only the structural ratio with the two mass-squared splittings already used by the GREMLIN three-flavor adapter.

## Absolute masses

Because

\[
\Delta m^2_{21}=m_2^2-m_1^2
=\left(\frac76-1\right)m_1^2,
\]

we obtain

\[
m_1^2=6\Delta m^2_{21},
\qquad
m_2^2=7\Delta m^2_{21},
\qquad
m_3^2=m_1^2+\Delta m^2_{31}.
\]

For the declared GREMLIN values `Delta_m21^2=7.42e-5 eV^2` and `Delta_m31^2=2.517e-3 eV^2`, the resulting masses are approximately

\[
(m_1,m_2,m_3)=(21.10,22.79,54.43)\;\mathrm{meV},
\]

with

\[
\sum_i m_i\approx98.316\;\mathrm{meV}.
\]

The 98 meV declaration is therefore an input-independent internal cross-check of this calculation. It is not treated as an independent dataset because both structural claims occur inside the same research programme.

## Remaining resonance-scale debt

The July mass-resonance source says only

\[
m_i^2=\mu_0(1-R_i),
\]

with `mu0` described as a mass-scale parameter. Once the absolute `m_i` are known,

\[
R_i=1-\frac{m_i^2}{\mu_0}.
\]

Different admissible values of `mu0` still produce different resonance triplets and different normalized resonant-Hamiltonian gaps while preserving the same absolute neutrino masses. v2.2 therefore does not identify `mu0`.

## BELZEBUB verdict

\[
\boxed{\text{Absolute neutrino mass scale: candidate closed within the declared framework.}}
\]

\[
\boxed{\text{Resonance normalization }\mu_0\text{: still open.}}
\]

The source-spectrum debt is reduced from `(mu0, absolute anchor, projector selection)` to

1. source-derived `mu0` normalization;
2. selection of the three symbolic projectors to be paired with the three neutrino mass projectors.

This is a structural reduction of the open problem, not a canon promotion.
