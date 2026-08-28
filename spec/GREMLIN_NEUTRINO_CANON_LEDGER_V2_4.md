# GREMLIN Neutrino Canon Ledger v2.4

Status: `CANONICAL / ACTIVE`

Authority date: `2026-08-28`

## Canonical claims

### C-Nu-1 — Complex-overlap frame bridge

Status: `CANONICAL_CONDITIONAL`

Parent artifact: `GREMLIN_COMPLEX_OVERLAP_FRAME_BRIDGE_V2_3`

Parent commit: `4d16a924a21acc2404f4af2c7e5681946c58c6fc`

Canonical construction:

\[
(C_\nu I)_\alpha=\langle S_{\nu_\alpha}|I\rangle,
\qquad
J_m=U_{\rm PMNS}^\dagger C_\nu.
\]

Precondition: a provenance-bearing labelled orthonormal neutrino triple in the same symbolic/intention Hilbert space, together with declared PMNS basis orientation.

Provenance: July symbolic Hilbert/resonance source; neutrino fixed-point source; GREMLIN v1.5 PMNS orientation; v2.3 implementation and regression receipt.

Falsifier: a source-grounded embedding that contradicts the labelled orthonormal frame assumption, a failure of the declared PMNS orientation/unitarity requirement, or a reproducible failure of the norm/phase-loss tests under the stated preconditions.

Open debt: `NEUTRINO_FRAME_TO_H_I_SOURCE_BINDING`.

### C-Nu-2 — Probability-shadow firewall

Status: `CANONICAL`

Canonical statement:

\[
R_\alpha=|\langle S_{\nu_\alpha}|I\rangle|^2
\]

retains component probabilities while relative complex phase information required by the mass-amplitude bridge is carried by the overlaps themselves.

Provenance: v2.3 phase-loss witness and regression suite.

Falsifier: a reproducible construction showing that the declared mass-amplitude output is uniquely reconstructible from the same probability-shadow vector for all admissible relative phases under the same PMNS map.

### C-Nu-3 — Cross-framework neutrino-spectrum holonomy firewall

Status: `CANONICAL_FIREWALL`

Parent artifact: `GREMLIN_NEUTRINO_FRAMEWORK_HOLONOMY_FIREWALL_V2_4`

Parent commit: `a9faf42bb7016c649eb8eb93cf5827bd89323684`

Canonical branch registry:

- Graded-projection branch: `m2/m1 = sqrt(7/6)`; v2.2 remains `BRANCH_LOCAL_EVIDENCE / GRADED_PROJECTION_SCOPE`.
- TIR/Metatime tetrahedron branch: `r = [1,2,10]`; remains `BRANCH_LOCAL_EVIDENCE / TIR_TETRAHEDRON_SCOPE`.
- Shared absolute-neutrino-spectrum authority: `WITHHELD_PENDING_EXPLICIT_RELATION_OR_AUTHORITY`.

The exact conflict marker is

\[
2\ne\sqrt{7/6}.
\]

Provenance: graded-projection source; Metatime/TIR tetrahedron source; v2.2 cross-check; v2.4 implementation and regression receipt.

Falsifier or supersession condition: a provenance-bearing source correction showing that one ratio was assigned to a different observable, an explicit transformation/limit deriving one branch law from the other, or a declared supersession/authority decision backed by its derivation or empirical discriminant.

Open debt: `NEUTRINO_SPECTRUM_CROSS_FRAMEWORK_HOLONOMY`.

## Precedence

For GREMLIN neutrino work after v2.4:

1. `C-Nu-3` governs every use of an absolute neutrino spectrum across research branches.
2. `C-Nu-1` governs the coherent intention-to-mass amplitude bridge when its source-binding precondition is satisfied.
3. `C-Nu-2` requires complex overlaps to be retained whenever relative phase affects downstream amplitudes.
4. Earlier v1.7-v2.2 artifacts remain provenance-bearing parent work with their original evidential scope; this ledger controls promotion status for the v2.3-v2.4 frontier.

## Validation provenance

Pre-canonical regression receipts:

- v2.3 head `4d16a924a21acc2404f4af2c7e5681946c58c6fc`: GitHub Actions run `33130435139`, `success`.
- v2.4 head `a9faf42bb7016c649eb8eb93cf5827bd89323684`: GitHub Actions run `33130613499`, `success`.

Canonicalization is admitted only after the post-promotion branch regression on the canonicalization head is green.

## Merge target

Canonical repository target: `AdrianLipa90/GREMLIN:main` via PR #4.
