# GREMLIN Fundamental Repository Overlay v0.1

Status: `CANDIDATE_ONLY / NON_CANONICAL / GREMLIN_ASSISTED_DEPENDENCY_AUDIT`

Date: 2026-09-21

## 1. Frozen source heads

- GREMLIN: `86059ead6177fbb5bf33211f674781883a149a57`
- FPDG: `4f1d316c5fcee2a29c91e12b8f7157bd07b3ba99`
- TIR: `f7b754347502f5051d423867f8a8d60627b1f8d7`
- IDT: `2960a936e3f74b07a4bf30ebc5cb78b6c1811b4c`
- RFC: `786d1e1a9f9c91a4c3174719ed76966aa73edcef`
- SOH: `41772776dadf837c7a2f8b095b752e586d85c5dc`
- Infinities: `c1ad8376f9dd4c2daf2c4ea0bf61568d718fd794`

GREMLIN role split for this audit:

- **SPIDER** — dependency/relation overlay;
- **MOLE** — high-impact missing-premise localization;
- **HOUND** — contradiction and circularity firewall;
- **OWL** — epistemic-status preservation;
- **MANTIS** — prune duplicated/equivalent frontiers.

No claim is promoted by this report.

## 2. Canonical FPDG topology

The current FPDG snapshot contains:

- **160 claim nodes**;
- **219 directed dependency edges**;
- represented repositories: **TIR 35**, **IDT 28**, **RFC 90**, **SOH 7**;
- **65 nodes** carry an OPEN / CONDITIONAL / CANDIDATE / INPUT / FRONTIER style status;
- **26 frontier roots** have no unresolved parent inside the same frontier subgraph;
- the full directed graph is a DAG: **no nontrivial strongly connected component was found**.

The last point is important for proof hygiene: the current canonical graph does not close a theorem by cycling through equivalent claims.

## 3. Repository-level overlay

Current canonical cross-repository edge counts:

```text
TIR -> IDT   1
TIR -> RFC  11
IDT -> RFC  13
RFC -> IDT   1
TIR -> SOH   1
SOH -> IDT   3
```

The dominant backbone is therefore:

```text
TIR
 | \
 |  \----------------------.
 v                         v
IDT ---------------------> RFC
 ^                         |
 '-------------------------'
 ^
 |
SOH
```

with the SOH contribution currently entering IDT through candidate half-seam / double-cover / centered-rapidity interfaces.

**Infinities is not represented in the canonical FPDG node set at all.**
This is an integration gap, not a mathematical refutation. Its Hilbert-shift,
Collatz-operator, reciprocal-inversion and spectral-carrier structures therefore
cannot currently participate in automated cross-repository dependency closure.

A wider repository inventory also finds:

- `Metatime`: explicitly historical and points current work to IDT — omission from
  FPDG is expected.
- `Informational-Dynamics-of-Metatime`: explicitly marked `TO BE ARCHIVED` —
  omission from the live fundamental graph is expected.
- `Metatime-Relation_of_Information_Framework`: active research framework with
  open validation debts — currently absent from FPDG and should be classified as
  either an active source lineage or a provenance-only satellite.
- `QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics`:
  active falsifiable physical-hypothesis repository — absent from FPDG and best
  represented downstream of the established mathematical carrier, with its
  physical coupling hypotheses kept explicitly open.

## 4. SPIDER finding — the core physics stack is already heavily overlapped

The TIR/IDT/RFC overlap is not sparse. Existing cross-repository seams include:

- TIR local (R^3) and IDT clock structure into RFC ADM;
- TIR Levi-Civita / metric-jet structure into RFC Einstein selection;
- TIR global 3-manifold plus IDT foliation/event exactness into RFC shared spacetime atlas;
- IDT lapse and foliation into RFC covariant propagation / hyperbolicity;
- TIR and IDT Collatz phase interfaces into RFC Collatz phase fibre;
- TIR physical-realization bundle into RFC clock-transverse matching.

This supports the interpretation that much of the remaining work is integration
and source binding rather than invention of unrelated new local formulae.

## 5. MOLE finding — highest-leverage unresolved seams

Graph downstream-impact analysis places the following unresolved nodes at the
largest leverage points:

1. `TIR.SPACETIME.INTERLEAF_MATCHING_INPUT_CONTRACT`
   - status: production matching field open;
   - unresolved parent count inside frontier: 0;
   - **69 downstream claims** depend on its branch.

2. `RFC.F8.EOS_PHASE_CONTINUITY`
   - exact conditional;
   - **17 downstream claims**.

3. `TIR.SPACE.CARTAN_REFINEMENT_A2`
   - smooth refinement conditional / physical refining family next;
   - **15 downstream claims**.

4. `RFC.F13.VARIATIONAL_COMMON_ACTION`
   - mathematical branch passes, physical binding conditional;
   - **15 downstream claims**.

5. `TIR.SPACE.LEVI_CIVITA_A3`
   - local/regular uniqueness passes, global continuum existence open;
   - **14 downstream claims**.

6. `TIR.SPACE.METRIC_JET_A4` and `IDT.CLOCK.EVENT_EXACTNESS_05H`
   - **12 downstream claims each**.

This makes the interleaf matching field the strongest graph bottleneck by a
large margin.

## 6. HOUND finding — not all remaining frontier items are theorem gaps

The unresolved set separates into three distinct classes.

### A. Formal mathematics suitable for theorem proving

Examples:

- cocycle / quotient compatibility;
- local-to-global glue lemmas;
- affine / regular smooth extension lemmas;
- gauge invariance and representation quotient statements;
- finite graph exactness and path independence;
- Collatz Möbius / representation identities;
- SOH algebraic reductions and no-go lemmas.

These are appropriate eventual Lean targets.

### B. Physical-binding obligations

Examples:

- production interleaf matching field;
- actual relational-complex certificate;
- physical refining family;
- physical clock coupling;
- physical Collatz-time coupling;
- physical metric coupling;
- physical (G) universality;
- flavour-sector physical binding.

Lean can verify the implication **from explicit premises**, but cannot manufacture
or empirically validate the missing physical premise.

### C. Open external mathematical problems

SOH remains explicit:

[
X(u)=0 \Longrightarrow u^{-1}=\bar u
]

is RH-equivalent and OPEN. The GREMLIN half-orbit audit already shows that
quotient/barycentric symmetry alone cannot force pointwise orbit collapse.

Therefore repository overlap must not be interpreted as a proof of RH.

## 7. Missing graph structure found by overlay

The audit finds four concrete integration gaps before a Lean rollout should be
used as a completeness arbiter.

### GAP-1 — active satellite coverage is incomplete

The first missing active mathematical source is Infinities. Needed candidate
interfaces include:

```text
Infinities.HILBERT.SHIFT
  -> countable history/state allocation interfaces

Infinities.COLLATZ.OPERATOR
  -> TIR/IDT Collatz transition carrier

Infinities.RECIPROCAL.INVERSION
  -> SOH reciprocal-conjugation geometry

Infinities.SPECTRAL.N
  -> SOH/TIR spectral carrier crosswalk
```

The active Metatime-Relation framework needs an ownership decision: either map
its unique live claims into FPDG or mark them provenance/superseded by current
TIR/IDT/RFC owners.

QHTRI neutrino/phase-optics should enter only as a downstream physical-
hypothesis branch; its own README explicitly separates model mathematics from
unverified physical coupling.

These edges must remain candidate until source-typed. Historical Metatime and
Informational-Dynamics-of-Metatime do not need live theorem nodes because their
repositories explicitly mark themselves historical/to-be-archived.

### GAP-2 — TIR <-> IDT direct seam is underrepresented

There is only one canonical `TIR -> IDT` repository-level edge even though the
current stack contains multiple shared structures: quotient state, half/binary
carrier, phase transport, event/slice structure and Collatz phase interfaces.

This is primarily a **dependency-graph coverage gap**. It does not by itself
show a missing theorem.

### GAP-3 — quotient / representation-invariance contract is not yet a
cross-stack dependency node

The RC/OES work exposed a reusable rule:

[
\mathcal R \to \mathcal R/G \to O.
]

TIR, IDT and RFC already contain local versions of this idea, but FPDG does not
yet expose one shared typed contract joining:

- projective quantum state;
- temporal representation/gauge;
- spatial/atlas frame quotient;
- holonomy observables.

Until that node exists, identical gauge structure appears as several separate
local proofs and GREMLIN cannot mechanically check that the seams commute.

### GAP-4 — physical-realization inputs dominate the remaining spacetime chain

The biggest apparent "holes" are not missing algebraic formulas. They are
source-owned inputs/certificates: matching fields, production complexes,
global coverage, physical clock/source bindings, and scale/coupling bindings.

A formal prover should classify these as explicit assumptions/input contracts,
not silently replace them with theorems.

## 8. Recommended pre-Lean theorem graph

Before formalization, GREMLIN recommends one shared seam layer:

```text
REPRESENTATION_QUOTIENT
    |
    +--> TIR physical state class
    +--> IDT physical event / clock class
    +--> RFC atlas/frame class

TIR spatial carrier ----.
                         +--> INTERLEAF_MATCHING --> SHARED_SPACETIME_ATLAS
IDT temporal carrier ---'                         |
                                                   +--> GLOBAL EINSTEIN CARRIER

Infinities Collatz operator --> TIR/IDT Collatz interface --> RFC phase fibre

SOH reciprocal geometry --> orbit-separating target
                         X  quotient-only shortcut
```

The `X` is deliberate: GREMLIN/HOUND rejects the shortcut from quotient
symmetry to pointwise RH orbit collapse.

## 9. GREMLIN verdict

```text
LOCAL_MATHEMATICAL_COVERAGE: HIGH
CROSS_REPO_INTEGRATION: HIGH_BUT_INCOMPLETE
MAIN_MISSING_FORMAL_LAYER: SHARED_QUOTIENT/GLUING CONTRACT
MAIN_MISSING_SPACETIME_INPUT: INTERLEAF_MATCHING FIELD
MAIN_MISSING_REPO_INTEGRATION: INFINITIES -> FPDG
RH_STATUS: OPEN
PHYSICAL_BINDING_STATUS: MULTIPLE OPEN INPUTS
LEAN_READY_SUBGRAPH: YES
LEAN_READY_WHOLE_PROGRAM: NO
```

The graph does **not** support the statement "nothing remains to prove".
It does support a narrower and useful conclusion: most remaining high-impact
gaps are now identifiable seams, input bindings, or a small number of explicit
open theorem frontiers rather than a diffuse lack of mathematical structure.

## 10. Next gate

Do not start by formalizing every repository independently.

First define the shared seam schema:

```text
claim
premises
quotient/gauge group
source domain
target domain
transition/intertwiner
invariant observable
proof status
physical-binding status
upstream claim IDs
downstream claim IDs
```

Then Lean can attack the exact subgraph while GREMLIN checks that every theorem
has the same typed premises and dependencies as the repository graph.

The intended cross-validation is:

```text
GREMLIN says edge missing  <=>  Lean requires an unproved premise / explicit axiom
GREMLIN says edge exact    <=>  Lean kernel accepts the theorem with no sorry
GREMLIN says physical bind <=>  Lean exposes it as a premise rather than a proof
```

A disagreement between those two systems becomes the next audit target.


## 11. GREMLIN second pass — candidate overlay

A second SPIDER/HOUND pass was run conceptually by applying
`provenance/FUNDAMENTAL_CANDIDATE_OVERLAY_V0_1.json` on top of the frozen FPDG
snapshot without mutating FPDG.

The candidate overlay adds:

- one shared representation/quotient meta-contract;
- one shared slice-glue/cocycle meta-contract;
- one countable-history interface;
- four Infinities source nodes;
- one missing SOH reciprocal-conjugation coverage node;
- one MRIF semantic-holonomy firewall node;
- one QHTRI model node plus one explicitly open physical-coupling node.

Second-pass graph metrics:

```text
nodes                 171
edges                 236
frontier nodes         75
frontier roots         29
nontrivial SCCs         0
```

Repository coverage becomes:

```text
TIR          35
IDT          28
RFC          90
SOH           8
CROSS_STACK   3
INFINITIES    4
MRIF          1
QHTRI         2
```

The candidate overlay does not create a dependency cycle. This is important:
adding the missing cross-stack seams did not manufacture a circular proof route.

The strongest new candidate source is:

```text
INF.COLLATZ.OPERATOR
    -> TIR.COLLATZ_FS.RELATIONAL_PHASE_INTERFACE
    -> ...
    -> RFC.E27.COLLATZ_FS_PHASE_FIBRE

INF.COLLATZ.OPERATOR
    -> IDT.COLLATZ_FS.PHASE_MAP
    -> IDT.COLLATZ_FS.TEMPORAL_PHASE_INTERFACE
    -> RFC.E27.COLLATZ_FS_PHASE_FIBRE
```

It reaches **9 downstream claims** in the combined candidate graph. This makes
the Collatz operator crosswalk worth formal checking, but it remains a
crosswalk candidate and does not imply the Collatz conjecture.

The original leading bottleneck remains unchanged in identity and increases in
downstream reach after the overlay:

```text
TIR.SPACETIME.INTERLEAF_MATCHING_INPUT_CONTRACT
    downstream: 69 -> 72
```

Thus the overlay strengthens, rather than removes, the diagnosis that physical
interleaf matching is the dominant spacetime integration gate.

### 11.1 Shared quotient/glue seam

The overlay now makes the common structure explicit:

```text
TIR.HOLONOMY.WIJ --------------------.
IDT.NOETHER.GAUGE_COVARIANT_SOURCE --+--> REPRESENTATION_QUOTIENT_CONTRACT
RFC.F1.GAUGE_RELATIONAL_PHASE -------+
RFC.GSC3B.RELATIONAL_EVENT_PLACEMENT-+
MRIF.W_SEMANTIC firewall ------------'   [type example only]
                                              |
                                              v
                                  SLICE_GLUE_COCYCLE_CONTRACT
                                      ^                 ^
                                      |                 |
                         IDT.CLOCK.GLOBAL_COCYCLE   RFC.E25.ATLAS
```

This is the correct target for later proof-assistant comparison because it
forces the local representations to expose the same domains, quotient actions,
transition maps and invariant outputs before any theorem is imported across a
repository boundary.

### 11.2 Satellite firewalls

The second pass deliberately keeps three boundaries:

1. `MRIF.W_SEMANTIC.U1_HOLONOMY_FIREWALL` may demonstrate a semantic type
   pattern, but no edge identifies it with physical holonomy.
2. `QHTRI.FLAVOUR.HOLONOMIC_POTENTIAL_MODEL -> QHTRI.PHYSICAL.HNUQ` is a
   model-to-hypothesis edge. The physical coupling remains OPEN and requires
   measurement.
3. `INF.RECIPROCAL.INVERSION` only crosswalks to SOH reciprocal-conjugation
   geometry. It does not supply the missing pointwise zero-orbit-collapse
   theorem.

## 12. Pre-Lean GREMLIN conclusion

The second pass does **not** reveal a missing large mathematical sector.

It reveals a compact set of seams that should be normalized before Lean:

```text
A. representation quotient contract
B. slice/cocycle glue contract
C. Infinities Collatz operator crosswalk
D. TIR interleaf matching physical input
E. global continuum / production atlas inputs
F. SOH pointwise orbit-collapse incoming theorem
G. physical binding: G, flavour, clocks, QHTRI coupling
```

Items A-C are suitable for immediate formalization once their exact source
statements are frozen. Items D, E and G must remain explicit physical/source
premises. Item F is genuine open mathematics and must not be converted into an
axiom merely to make a proof assistant turn green.

The correct GREMLIN -> Lean handoff is therefore not "formalize every file".
It is "freeze these typed seams, then ask Lean whether the exact mathematical
subgraph closes without hidden axioms".


## 13. Existing PNCS relational graph adopted as the seam carrier

The earlier idea of a separate neutral relational/formal kernel is withdrawn.
The repository already exists:

`AdrianLipa90/PhaseNav-Natural-Coding-System`

at source head:

`3aa3393cea390c8703a5bf50209f10939beb9b34`.

PNCS explicitly defines written code as a projection of a **canonical 36D
relational graph** and already supplies the hierarchy

```text
KAKU -> RADICAL -> DEFINITION_PATH -> CLASS_PATH -> ... -> SYSTEM_PATH
```

with exact downward lineage to KAKU and fail-closed handling of missing or
ambiguous relations.

More importantly, PNCS already contains the exact integration path needed by
this audit:

```text
FPDG pain witness
 -> explicit claim_id -> grammar binding
 -> GREMLIN relation mining
 -> canonical KAKU resolver
 -> relational-isomorphism compiler
 -> RADICAL
 -> native PNV operators
 -> READ_ONLY candidate conformance
```

Therefore GREMLIN must **reuse PNCS** rather than create a second relational
compiler or a new Formal-Kernel repository.

The revised authority split is:

```text
source theorem repos   -> own mathematics and physical claims
FPDG                   -> owns dependency/status graph
GREMLIN                -> discovers, overlays, falsifies, localizes seams
PNCS                    -> owns canonical relational-graph representation,
                           KAKU/RADICAL lowering and machine-checkable
                           cross-formalism candidate compilation
Lean [later]           -> kernel-checks frozen mathematical statements
```

PNCS is not promoted to theorem authority. Its compiler can preserve an
isomorphism candidate as executable relational structure while the evidence
status remains owned by the source repositories.

### Revised second-pass metrics

Replacing the synthetic `CROSS_STACK` carrier with the actual PNCS graph and
adding its existing compiler/FPDG ingress produces:

```text
nodes                 174
edges                 241
frontier nodes         77
frontier roots         30
nontrivial SCCs         0
```

Repository overlay:

```text
TIR          35
IDT          28
RFC          90
SOH           8
PNCS          6
INFINITIES    4
MRIF          1
QHTRI         2
```

No proof cycle is introduced.

The principal bottleneck remains unchanged:

```text
TIR.SPACETIME.INTERLEAF_MATCHING_INPUT_CONTRACT
downstream = 72
```

and the Infinities Collatz operator crosswalk remains the strongest new
mathematical satellite:

```text
INF.COLLATZ.OPERATOR
downstream = 9
```

### Repository-creation decision

Current verdict:

```text
NEW_RELATIONAL_KERNEL_REPOSITORY = NO
NEW_CROSS_REPO_GRAPH_REPOSITORY = NO
USE_EXISTING_PNCS_RELATIONAL_GRAPH = YES
USE_EXISTING_FPDG_DEPENDENCY_GRAPH = YES
USE_GREMLIN_AS_AUDITOR = YES
```

A new repository is justified only if a later artifact has a genuinely new
ownership class that is not representable as:

- source theorem/physics content in TIR, IDT, RFC, SOH, Infinities or QHTRI;
- dependency/status metadata in FPDG;
- relational graph structure in PNCS;
- audit/orchestration in GREMLIN.

At present no such missing ownership class is detected.


## 14. PNCS seam-bank realization

The generic seam placeholders have now been replaced by concrete post-v1 PNCS
relational-isomorphism candidates on branch
`research/fundamental-seam-bank-v0.1` / draft PR `#71`.

The PNCS bank contains:

```text
FSI.01  TIR SE(3) affine glue <-> RFC rigid overlap cocycle
FSI.02  IDT/TIR/RFC global cocycle/gluing spine
FSI.03  IDT/TIR/RFC representation-quotient/invariant spine
FSI.04  Infinities/TIR/IDT accelerated-Collatz block/phase crosswalk
```

All four compile through the existing
`PNCS_GREMLIN_RELATIONAL_ISOMORPHISM_COMPILER_V0_1` and remain:

```text
POST_V1_EXPERIMENTAL
EPISTEMIC CHYBA
CANDIDATE_ONLY
READ_ONLY
runtime_execution_authority = false
canon_write_authority = false
```

Focused PNCS gate:

```text
5 passed
quarantine boundary PASS
```

The active PNCS v1 package does not import the seam bank.

The overlay also exposed two RFC source claims that exist in RFC but were not
yet represented as FPDG claim nodes:

```text
RFC.GSC4F.GLOBAL_SE3_GAUGE_QUOTIENT
RFC.GSC4G.RIGID_OVERLAP_COCYCLE
```

They are therefore added only as candidate FPDG-coverage nodes in the GREMLIN
overlay, not as replacements for RFC authority.

Recomputed overlay after using the actual PNCS FSI bank:

```text
nodes                 178
edges                 248
frontier nodes         81
frontier roots         32
nontrivial SCCs         0
```

Repository coverage:

```text
TIR          35
IDT          28
RFC          92   [90 canonical FPDG + 2 candidate coverage nodes]
SOH           8
PNCS          8
INFINITIES    4
MRIF          1
QHTRI         2
```

The leading bottleneck remains

`TIR.SPACETIME.INTERLEAF_MATCHING_INPUT_CONTRACT`

with `72` downstream claims. The Infinities Collatz operator now reaches
`10` downstream claims after routing through PNCS FSI.04.

This strengthens the repository-creation verdict:

```text
new relational graph repo      NO
new formal-kernel repo now     NO
new theory repo now            NO
existing PNCS graph            USE
existing FPDG dependency graph USE
GREMLIN audit overlay          USE
```


## 15. Hilbert-shift / countable-history seam completed as a PNCS candidate

The final generic countable-history placeholder has been replaced by the concrete
PNCS candidate:

`FSI.05.HILBERT.SHIFT.COUNTABLE.HISTORY`.

The bridge is intentionally narrow. Infinities owns the standard unilateral
shift result

[
operatorname{rank}(I-U^kU^{*k})=k,qquad operatorname{ind}(U^k)=-k,
]

while IDT owns serial realized-prefix history

[

u_0prec_T
u_1prec_T
u_2prec_Tcdots.
]

Under the explicit index identification (e_nleftrightarrow
u_n), both expose
the successor embedding

[
nmapsto n+k,
]

which is injective, order-preserving and leaves the first (k) labels outside
the image.

The relational invariant is therefore **countable successor order**, not
Hilbert-space structure. The Fredholm index remains typed to Infinities and is
not imported as a physical time observable. IDT memory semantics remain owned
by IDT.

Updated focused PNCS seam-bank result:

```text
6 passed
post-v1 quarantine boundary PASS
```

This removes the last synthetic cross-stack seam placeholder from the current
GREMLIN overlay. All five shared formal seams are now represented by concrete
PNCS FSI candidates.


## 16. Source-export freshness audit

A direct comparison of each source repository's current main head against the
`source_commit` embedded in its current `DEPENDENCY_EXPORT.json` changes the
interpretation of the remaining graph gaps.

FPDG is fully synchronized with the **declared exports**:

```text
TIR export: 35/35 claims represented in FPDG
IDT export: 28/28 claims represented in FPDG
RFC export: 90/90 claims represented in FPDG
SOH export:  7/7 claims represented in FPDG
```

The problem is therefore not an FPDG import failure. The source exports lag the
current source repositories:

```text
TIR  export source_commit -> current main:  18 commits ahead
IDT  export source_commit -> current main:  18 commits ahead
RFC  export source_commit -> current main: 122 commits ahead
SOH  export source_commit -> current main:   4 commits ahead
```

Known examples of current source structures outside the exported FPDG surface
include RFC GSC4F/GSC4G. TIR also contains newer SP3 compatibility/half-lift
candidate material, while IDT contains newer production-event and mod6pi/C3
bridge work.

Therefore the correct ownership diagnosis is:

```text
SOURCE REPOSITORY
  -> refresh / classify DEPENDENCY_EXPORT
  -> FPDG import/update
  -> GREMLIN overlay
  -> PNCS relational compilation
```

not:

```text
GREMLIN invents missing FPDG nodes directly.
```

The two RFC GSC4F/GSC4G nodes retained in the GREMLIN overlay are consequently
typed as **source-export coverage candidates**, not evidence that FPDG failed to
consume a declared export.

No new repository is required to fix this. The missing mechanism is export
freshness and ownership discipline in the existing source repositories.


## 17. First GREMLIN ↔ Lean cross-validation

The first proof-assistant target was selected directly from the PNCS/GREMLIN
FSI.05 seam rather than from an arbitrary repository file.

GREMLIN/PNCS candidate:

`FSI.05.HILBERT.SHIFT.COUNTABLE.HISTORY`

predicted that the safe shared invariant is only the countable successor/order
embedding

[
nmapsto n+k,
]

while Hilbert-space structure, Fredholm index and physical-time semantics must
remain outside the crosswalk.

Lean was then attached independently to both source sides.

### Infinities

Draft PR `#2`, branch `formalize/lean-proof-gates-v0.1`.

Lean kernel build: **PASS**.

Axiom audit:

```text
7 declarations audited
all within allowlist [propext, Classical.choice, Quot.sound]
```

Formalized:

- injectivity of (nmapsto n+k);
- preservation of (le) and (<);
- exclusion of indices (0,ldots,k-1) from the shifted image;
- identity of the zero shift.

The Fredholm-index theorem is deliberately not imported into this cross-repo
formalization.

### IDT

Draft PR `#103`, branch `formalize/lean-proof-gates-v0.1`.

Lean kernel build: **PASS**.

Axiom audit:

```text
9 declarations audited
all within allowlist [propext, Classical.choice, Quot.sound]
```

Formalized:

- injectivity/order preservation of the serial-history successor;
- exclusion of the initial (k) history indices from the shifted range;
- append-only finite-history prefix preservation;
- append-only length accounting.

The ordinary IDT reference suite and the 05J production-event input gate are
also GREEN on the same PR head.

### Cross-validation verdict

```text
GREMLIN predicted invariant:
    COUNTABLE SUCCESSOR / ORDER EMBEDDING

Lean independently closes:
    COUNTABLE SUCCESSOR / ORDER EMBEDDING

GREMLIN firewall:
    NO HILBERT-SPACE IDENTIFICATION
    NO FREDHOLM->PHYSICAL-TIME IMPORT

Lean proof surface:
    contains neither identification

VERDICT:
    GREMLIN_LEAN_AGREEMENT_PASS
```

This is the first concrete validation of the intended architecture: GREMLIN
localizes the shared structure and its firewall; Lean accepts exactly the
mathematical core without requiring the forbidden semantic promotion.


## 17. First Lean arbitration results

The first two GREMLIN-selected seams have now been checked in the source
repositories with Lean 4 proof gates rather than only Python/graph validation.

### FSI.05 countable-history seam

Infinities draft PR #2 and IDT draft PR #103 are GREEN on their Lean proof
gates. The admitted theorem scope is deliberately narrow:

```text
n -> n+k is injective
n -> n+k preserves order
0,...,k-1 are outside the shifted image
append-only finite IDT history preserves the complete previous prefix
```

This confirms the exact countable-successor structure predicted by GREMLIN.
It does **not** identify IDT with a Hilbert space and does not import the
Fredholm index as a physical clock observable.

### FSI.01 affine SE(3) crosswalk

TIR draft PR #175 and RFC draft PR #168 are GREEN on their Lean proof gates.

Lean verifies that under the explicit symbol convention

[
R_{ba}leftrightarrow A_{qp},qquad
t_{ba}leftrightarrow t_{qp},
]

the two source coordinate laws reduce to the same typed composition formula and
the same inverse-coordinate formula.

This closes the **formal crosswalk** only. Production overlap data,
continuum curvature/torsion binding and physical spacetime realization remain
separate source gates.

### Interpretation

GREMLIN and Lean agree on the first two tested seams:

```text
GREMLIN structural seam detected
        |
        v
PNCS candidate compiles
        |
        v
Lean source theorem PASS
```

No hidden axiom was required for either crosswalk. This is evidence that the
graph is locating real formal correspondences rather than merely lexical
similarities.

Next formal targets remain FSI.04 Collatz block/phase, then FSI.02 cocycle
spine and FSI.03 quotient/invariant spine.


## 18. Second GREMLIN ↔ Lean cross-validation — FSI.01 affine SE(3) seam

GREMLIN/PNCS selected the next exact seam:

`FSI.01.SE3.AFFINE.GLUE.TIR.RFC`.

The source formulas are:

```text
TIR:
(R2,t2) o (R1,t1) = (R2 R1, R2·t1 + t2)

RFC GSC4G:
A_rp = A_rq A_qp
t_rp = A_rq t_qp + t_rq
```

under the explicit convention map

```text
R_ba <-> A_qp
t_ba <-> t_qp
```.

Lean was attached independently to both source repositories.

### TIR

Draft PR `#175`.

Head:

`f2668ad71a192f5cc3ae654f90f552c5381e004a`

Lean proof gate: **PASS**.

Axiom audit:

```text
25 declarations audited
all within allowlist [propext, Classical.choice, Quot.sound]
```

The formal surface defines an abstract typed affine pair and proves by kernel
reduction that the TIR composition/inverse formulas and the normalized RFC
formulas coincide under the declared symbol map.

### RFC

Draft PR `#168`.

Head:

`ed2c5f5e6284ae1a80bb4a3f2585c0df87a57fd2`

Lean proof gate: **PASS**.

Axiom audit:

```text
25 declarations audited
all within allowlist [propext, Classical.choice, Quot.sound]
```

The RFC-side formal surface independently exposes the same affine composition
and inverse crosswalk.

### Exact boundary of the result

Lean has closed the **coordinate/algebraic crosswalk**, not the entire physical
SE(3) programme.

The following remain outside this theorem and keep their source status:

- membership/validation of the rotational carrier in the intended (SO(3))
  realization;
- production numeric overlap cocycle;
- production coframe/source realization;
- continuum curvature/torsion interpretation;
- physical spacetime promotion.

Therefore the correct verdict is:

```text
FSI.01 coordinate composition crosswalk     PASS
FSI.01 coordinate inverse crosswalk         PASS
hidden axiom required                       NO
production overlap witness                  OPEN SOURCE INPUT
curvature/torsion physical binding          OPEN
GREMLIN_LEAN_AGREEMENT                      PASS
```

This is the second consecutive seam where the proof assistant closes exactly
the mathematical core isolated by GREMLIN without forcing a forbidden physical
promotion.


## 18. FSI.04 Collatz block / phase seam — Lean PASS

The third GREMLIN-selected seam has now passed Lean on both source sides.

Infinities draft PR #2 proves the local accelerated-branch statement under an
explicit exact factorization

[
3n+1=u,2^a
quadLongrightarrowquad
rac{3n+1}{2^a}=u,
]

and records the branch word (1,0^a) with length (a+1).

IDT draft PR #103 proves, independently,

[
D^k(q)=2^k q
]

for repeated lifted doubling and the finite-modulus analogue

[
D_m^k(q)equiv 2^k qpmod m.
]

Therefore the local FSI.04 crosswalk now has kernel-checked support on both
repositories:

```text
accelerated odd Collatz block
       |
       | a+1 branch operations
       v
a+1 phase doublings
       |
       v
2^(a+1) phase multiplier
```

The firewall is unchanged: this is local exact arithmetic. It does not prove
global Collatz convergence and it does not identify iteration count with
physical time.

Three of the five PNCS seam-bank candidates have now passed independent Lean
arbitration:

```text
FSI.01  PASS
FSI.04  PASS
FSI.05  PASS
FSI.02  next
FSI.03  next
```
