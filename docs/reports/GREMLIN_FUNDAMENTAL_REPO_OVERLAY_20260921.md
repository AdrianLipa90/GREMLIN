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

### GAP-1 — Infinities is absent from FPDG

Needed candidate interfaces:

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

These edges must remain candidate until source-typed.

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
