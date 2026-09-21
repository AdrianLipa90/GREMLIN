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
