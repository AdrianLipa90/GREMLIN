# GREMLIN / BELZEBUB NuFIT 6.1 Flavor Discriminant Map v2.7

Status: `VACUUM_FLAVOR_DISCRIMINANT_IDENTIFIED / MATTER_AND_DETECTOR_GATES_OPEN / CLAIM_PROMOTION_FALSE`

## Question

v2.6 established that the exact TIR tetrahedron relation

\[
\Delta m^2_{31}=33\Delta m^2_{21}
\]

is compatible with both official NuFIT 6.1 Normal-Ordering `DMS/DMA` marginalized surfaces.

v2.7 asks a different, experimentally operational question:

> If the PMNS mixing coordinates are held at the same NuFIT 6.1 profile minima, where in `L/E` does replacing the free NuFIT mass-splitting ratio by the profiled exact TIR ratio 33 produce the largest flavor-probability and flavor-information separation?

The purpose is sensitivity mapping, not claim promotion.

## Inputs

All coordinates are extracted directly from the same hash-pinned official NuFIT 6.1 xz tables used by v2.6.

The PMNS coordinates are read from the minima of the published `T13/T12` and `T23/DMA/DCP` projections. The unconstrained mass splittings are read from the minimum of `DMS/DMA`. The TIR-constrained spectrum is the minimum of the exact ratio-33 line on that same `DMS/DMA` surface.

This isolates the mass-splitting-ratio effect while holding PMNS mixing coordinates fixed within each NuFIT atmospheric treatment.

## Evolution

The comparison uses standard three-flavor vacuum PMNS evolution,

\[
A_{\alpha\to\beta}(L/E)
=
\sum_i U_{\beta i}
\exp\!\left[-i\,2(1.267)\,\Delta m^2_{i1}\frac{L}{E}\right]
U^*_{\alpha i},
\]

with

\[
P_{\alpha\to\beta}=|A_{\alpha\to\beta}|^2.
\]

The uniform-input flavor channel is also evaluated through

\[
I(S_{\rm in};S_{\rm out}).
\]

PMNS unitarity and probability conservation are executable gates.

## Resolution robustness

Three scans are recorded:

1. ideal vacuum, `0 <= L/E <= 2000 km/GeV`;
2. the same range with a Gaussian-like 10% fractional `L/E` smearing diagnostic;
3. ideal vacuum extended to `10000 km/GeV` as a mathematical sensitivity map.

The 10% smearing scan is the primary robustness coordinate. It is not a detector model.

## Executed NuFIT 6.1 results

GitHub Actions run `33135135002`, job `98733297822`, after two explicit pre-result firewall failures were fixed without changing the physical equations:

- binary64 exact-equality test corrected to scale-aware comparison;
- direct-script import path replaced by module invocation.

Final regression: `307 passed in 1.02s`; official data replay: success.

### TBoff-NO / IC23 without tabulated SK atmospheric likelihood

Profile coordinates extracted from official tables:

\[
\sin^2\theta_{12}=0.308,
\quad
\sin^2\theta_{13}=0.0225,
\quad
\sin^2\theta_{23}=0.470,
\quad
\delta_{CP}=-155^\circ.
\]

Free surface minimum:

\[
\Delta m^2_{21}=7.53356\times10^{-5}\,\mathrm{eV}^2,
\qquad
\Delta m^2_{31}=2.52000\times10^{-3}\,\mathrm{eV}^2,
\]

with ratio approximately `33.45034`.

The profiled TIR ratio-33 point is

\[
\Delta m^2_{21}=7.60612\times10^{-5}\,\mathrm{eV}^2,
\qquad
\Delta m^2_{31}=2.51002\times10^{-3}\,\mathrm{eV}^2,
\]

with `Delta chi^2 = 0.9902209322` on the published DMS/DMA surface.

Ideal scan through `2000 km/GeV`:

\[
\boxed{
\max |\Delta P|=0.02349596
\text{ in }\nu_\mu\to\nu_\mu
\text{ at }L/E\approx1783\,\mathrm{km/GeV}.}
\]

With the 10% `L/E` smearing diagnostic:

\[
\boxed{
\max |\Delta P|=0.01298329
\text{ in }\nu_\mu\to\nu_\mu
\text{ at }L/E\approx1749\,\mathrm{km/GeV}.}
\]

The largest smeared mutual-information separation is approximately `+0.01286385 bit` at `L/E ~= 1126 km/GeV`.

### TByes-NO / IC24 with tabulated SK atmospheric likelihood

Profile coordinates:

\[
\sin^2\theta_{12}=0.308,
\quad
\sin^2\theta_{13}=0.0225,
\quad
\sin^2\theta_{23}=0.470,
\quad
\delta_{CP}=-150^\circ.
\]

Free surface minimum:

\[
\Delta m^2_{21}=7.53356\times10^{-5}\,\mathrm{eV}^2,
\qquad
\Delta m^2_{31}=2.51000\times10^{-3}\,\mathrm{eV}^2,
\]

with ratio approximately `33.31760`.

The profiled TIR point is

\[
\Delta m^2_{21}=7.59062\times10^{-5}\,\mathrm{eV}^2,
\qquad
\Delta m^2_{31}=2.504905\times10^{-3}\,\mathrm{eV}^2,
\]

with `Delta chi^2 = 0.4409750618`.

Ideal scan through `2000 km/GeV`:

\[
\boxed{
\max |\Delta P|=0.01241247
\text{ in }\nu_\mu\to\nu_\mu
\text{ at }L/E\approx1788.5\,\mathrm{km/GeV}.}
\]

With 10% smearing:

\[
\boxed{
\max |\Delta P|=0.00687078
\text{ in }\nu_\mu\to\nu_\mu
\text{ at }L/E\approx1754\,\mathrm{km/GeV}.}
\]

The largest smeared mutual-information separation is approximately `+0.00656913 bit` at `L/E ~= 1129 km/GeV`.

## Stable target

Both atmospheric treatments independently select the same robust probability channel and nearly the same `L/E` coordinate:

\[
\boxed{
\nu_\mu\to\nu_\mu,
\qquad
L/E\approx(1.75\pm0.01)\times10^3\,\mathrm{km/GeV}
}
\]

for the 10% smearing diagnostic.

This is the current experimental sensitivity target for distinguishing the exact ratio-33 spectrum from the unconstrained NuFIT profile spectrum within the declared vacuum comparison.

## Firewalls

The calculation includes vacuum oscillation dynamics and an abstract fractional `L/E` smearing diagnostic. Matter effects, flux models, cross sections, detector response, nuisance parameters and experiment-specific likelihoods remain separate required gates before experimental exclusion sensitivity can be quoted.

The extended `L/E <= 10000 km/GeV` ideal scan is retained as a mathematical map and is not promoted to an experimental target.

Claim promotion remains false.
