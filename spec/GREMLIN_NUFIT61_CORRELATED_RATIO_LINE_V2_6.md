# GREMLIN / BELZEBUB NuFIT 6.1 Correlated Ratio-Line Replay v2.6

Status: `OFFICIAL_SURFACE_REPLAY / CLAIM_PROMOTION_FALSE`

## Target

The canonical v2.4 framework firewall leaves the TIR / NOEMA tetrahedron spectrum and the graded-projection spectrum as separate source branches. v2.5 showed that the exact TIR relation

\[
\frac{\Delta m^2_{31}}{\Delta m^2_{21}}=33
\]

is compatible with the NuFIT 6.1 best-fit snapshot under an explicitly approximate diagonal-error treatment.

v2.6 removes that diagonal approximation for the mass-splitting test itself by evaluating the exact ratio line directly on the official NuFIT 6.1 two-dimensional `DMS/DMA` marginalized Delta-chi-square surface.

## Official source

NuFIT 6.1 publishes xz-compressed profile tables. For Normal Ordering v2.6 supports both declared atmospheric treatments:

- `TBoff-NO`: `v61.release-TBoff-NO.txt.xz`
- `TByes-NO`: `v61.release-TByes-NO.txt.xz`

Each file is accepted only if its byte count and SHA-256 match the pinned NuFIT 6.1 source manifest values already independently recorded in public provenance.

The files are downloaded ephemerally by CI and are never committed to this repository.

## Surface coordinates

NuFIT defines the section

`# DMS/DMA projection:`

with coordinates

\[
x=\log_{10}(\Delta m^2_{21}/\mathrm{eV}^2),
\qquad
y=\Delta m^2_{31}/(10^{-3}\,\mathrm{eV}^2)
\]

for Normal Ordering, plus the marginalized `Delta chi^2` value.

The exact TIR ratio line is therefore

\[
\boxed{
\Delta m^2_{21}=\frac{\Delta m^2_{31}}{33}
}
\]

or, in table coordinates,

\[
\boxed{
x(y)=\log_{10}\!\left(\frac{y\times10^{-3}}{33}\right)}.
\]

## Evaluation

The published DMS/DMA grid is checked for rectilinear completeness. Evaluation uses bilinear interpolation with extrapolation forbidden. The common oscillation scale is profiled by minimizing `Delta chi^2` along the exact ratio line across the tabulated surface.

A 40,001-point fine scan is accompanied by a half-resolution scan. The difference between their minima is recorded as a numerical-stability diagnostic.

No other NuFIT profile is summed with DMS/DMA. The returned quantity is the published two-dimensional marginalized surface value along the TIR ratio line.

## Acquisition firewall

CI attempts ordinary certificate-verified HTTPS first. If the NuFIT host certificate chain prevents acquisition, v2.6 permits only an explicit fallback named

`explicit_insecure_tls_fallback_with_sha256_pin`.

The fallback is never silent: the acquisition mode is written into the receipt, and the downloaded bytes must still match the pinned official SHA-256 and byte count exactly before parsing.

## Interpretation gate

A small `Delta chi^2` on the DMS/DMA surface means the exact ratio line is compatible with this marginalized NuFIT projection. It does not establish the TIR source mechanism, the absolute neutrino mass spectrum, PMNS source binding, or the full six-parameter likelihood.

Claim promotion remains false.

## Cross-repository relation

The ratio test is a mass-spectrum discriminant. Current TIR, IDT, RFC and Secret-of-a-Half phase/lapse/interference gates remain provenance-relevant to the larger neutrino-information program, while the numerical v2.6 statistic itself depends only on the exact TIR mass-splitting ratio and the external NuFIT DMS/DMA surface.

## BELZEBUB decision rule

The receipt reports the minimum published `Delta chi^2` reached by the exact TIR line separately for `TBoff-NO` and `TByes-NO`.

The two atmospheric treatments remain separate. Their Delta-chi-square values are not added.
