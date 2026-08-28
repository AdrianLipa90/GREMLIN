# GREMLIN / BELZEBUB NuFIT 6.1 Empirical Discriminant v2.5

Status: `EMPIRICAL_COMPATIBILITY_GATE / CLAIM_PROMOTION_FALSE`

## Purpose

v2.5 executes resolution route (3) from the canonical v2.4 neutrino framework holonomy firewall: use an external empirical discriminant while retaining both source branches.

The target relation comes from the TIR / NOEMA tetrahedron spectrum ratio

\[
r=[1,2,10].
\]

For masses proportional to these ratios,

\[
\frac{\Delta m^2_{31}}{\Delta m^2_{21}}
=
\frac{10^2-1^2}{2^2-1^2}
=33.
\]

This relation is evaluated against the latest NuFIT result available at implementation time: NuFIT 6.1 (2025), based on data available in November 2025, using the `IC24 with SK atmospheric data` Normal Ordering snapshot.

Source: `https://www.nu-fit.org/sites/default/files/v61.tbl-parameters.pdf`

Snapshot:

\[
\Delta m^2_{21}
=
7.537^{+0.094}_{-0.100}\times10^{-5}\,\mathrm{eV}^2,
\]

\[
\Delta m^2_{31}
=
2.511^{+0.021}_{-0.020}\times10^{-3}\,\mathrm{eV}^2.
\]

The corresponding best-fit ratio is

\[
\frac{\Delta m^2_{31}}{\Delta m^2_{21}}
\approx 33.3156.
\]

## Approximate diagonal pull

For a transparent first gate, asymmetric 1-sigma errors are symmetrized and treated as independent. This gives an approximate ratio pull of about `0.62 sigma` from the exact TIR value `33`.

The equivalent prediction

\[
\Delta m^2_{31}=33\Delta m^2_{21}
\]

gives

\[
\Delta m^2_{31,\,pred}\approx2.48721\times10^{-3}\,\mathrm{eV}^2,
\]

again about `0.63 sigma` from the NuFIT best-fit value under the same diagonal approximation.

This is a compatibility result, not an evidential promotion. NuFIT publishes correlated chi-square surfaces and v2.5 does not yet evaluate the exact `DMS/DMA` surface.

## Three-sigma rectangular compatibility

The exact ratio line maps the NuFIT 6.1 three-sigma `Delta m21^2` interval to a predicted `Delta m31^2` interval. That interval overlaps the published NuFIT 6.1 three-sigma `Delta m31^2` interval. Therefore the exact ratio `33` is not excluded by this conservative gate.

## Absolute-spectrum branch receipts

Using the same `Delta m21^2` best fit, the TIR tetrahedron branch gives

\[
(m_1,m_2,m_3)
\approx
(5.012,10.025,50.123)\,\mathrm{meV},
\]

with

\[
\sum m_\nu\approx65.160\,\mathrm{meV}.
\]

The graded-projection branch with

\[
\frac{m_2}{m_1}=\sqrt{7/6}
\]

and both NuFIT splittings supplied externally gives

\[
(m_1,m_2,m_3)
\approx
(21.265,22.969,54.435)\,\mathrm{meV},
\]

with

\[
\sum m_\nu\approx98.670\,\mathrm{meV}.
\]

The latter branch uses both measured splittings as inputs and is therefore not tested by the ratio-33 prediction in the same way.

## Cross-repository holonomy pins

The empirical gate records the latest relevant frontier pins used by the previous cross-repository audit:

- TIR phase-clock area scale: `b69ba6055c0535c666e12dbba069ffb87238eee6`
- IDT relational-lapse phase-rate gate: `11fcd5b798445265fa5f8cd4dc3386f3b0a463c4`
- RFC relational-lapse normal phase-rate bridge: `8611783d2471a3f6700d2c409b222f40b9752ec5`
- Secret-of-a-Half half-interface crosslink: `206e49e306b246c4b0f4d182b0d32d5511739408`
- GREMLIN canonical framework holonomy firewall v2.4: `76a2d6b46e485723eeaa0a97badd2dae6b9b3b14`

At this gate, IDT/RFC/SOH provide phase, lapse and interference consistency constraints; they do not alter the mass-splitting ratio prediction being tested.

## BELZEBUB firewall

The result is recorded as

`COMPATIBLE_NOT_DISCRIMINATING`.

The diagonal pull is explicitly approximate because the NuFIT covariance is not used. Claim promotion remains false.

The next required test is the exact one:

\[
\boxed{
\text{evaluate }\Delta m^2_{31}=33\Delta m^2_{21}
\text{ directly on the NuFIT 6.1 DMS/DMA correlated }\Delta\chi^2\text{ surface}
}
\]

Only that correlated likelihood test can replace the present approximate pull gate.
