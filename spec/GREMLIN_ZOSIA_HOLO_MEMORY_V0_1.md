# GREMLIN Zosia Holographic Memory v0.1

Status: \`IMPLEMENTED_CANDIDATE / DERIVED_INDEX_ONLY / APPEND_ONLY_SOURCE / NO_CANON_AUTHORITY\`

Date: 2026-09-23

## Purpose

Add a regenerable holographic/hexagonal/orbital recall surface above existing
GREMLIN memory without creating a second source of truth.

Authoritative persistence remains \`OrbitalHiveMemory\` / PhaseNav memory
exchange and consolidation. Holo memory is a derived index and activation
field. It may shortlist, phase-couple, compute moire overlap and propose
derived candidates; it may not overwrite, delete, latch or canonize memory.

## State factorization

Each relational memory already carries a \`6 x 6 = 36D\` phase-organized state.
For memory \(\mu\),

\[
X^{(\mu)}_{ak}
=
A^{(\mu)}_{ak}e^{i\phi^{(\mu)}_{ak}},
\qquad
a,k\in\{0,\ldots,5\}.
\]

Define each row resultant

\[
z_a=
\frac{1}{6}
\sum_k A_{ak}e^{i\phi_{ak}}.
\]

## Hexagonal BEES remap

The six row resultants are embedded on six 60-degree directions:

\[
Z_{\rm hex}
=
\sum_{a=0}^{5}
z_a e^{ia\pi/3}.
\]

\`Z_hex\` is quantized onto an axial hex lattice \((q,r)\) using deterministic
cube rounding.

This is an address/index candidate only. It does not establish semantic truth.
BEES may use neighboring hex cells as local overlap patches.

The cardinality of a radius-\(R\) hex patch is exact:

\[
N_{\rm hex}(R)=1+3R(R+1).
\]

## Orbital factor

The existing Hive \`orbit_index\` is preserved as an independent coordinate.
Hex address and orbital radius are not conflated.

A query may prune in two independent dimensions:

\[
\text{candidate set}
=
\text{HEX_PATCH}(q,r,R_{\rm hex})
\cap
\text{ORBIT_BAND}(O,R_{\rm orbit}).
\]

This preserves the existing \`r\` versus \`r_phase\` separation and does not
reinterpret priority orbit as semantic distance.

## Moire memory observable

For two 36D cells, define the normalized coherent cross term

\[
\mathcal M(\mu,\nu)
=
\frac{
2\sum_j
\sqrt{A_{\mu j}A_{\nu j}}
\cos(\phi_{\mu j}-\phi_{\nu j})
}{
\sum_j(A_{\mu j}+A_{\nu j})
}.
\]

\(\mathcal M\in[-1,1]\) when the denominator is nonzero.

It is an interference observable only:
- \(+1\): phase-aligned equal support;
- \(-1\): anti-phase equal support;
- intermediate values: partial constructive/destructive overlap.

A high moire score is not evidence of truth, identity or causal relation.

## Kuramoto patch dynamics

For activated patch phases \(\psi_i\), reuse the existing GREMLIN phase
potential

\[
V=
-\sum_{i<j}K_{ij}\cos(\psi_i-\psi_j).
\]

The implemented reference step uses the overdamped candidate dynamics

\[
\dot\psi_i
=
\Gamma_i^{-1}
\sum_jK_{ij}\sin(\psi_j-\psi_i).
\]

No new physical substrate claim is introduced. This is an activation/settling
surface for nearby memory cells.

## Retrieval contract

The holo layer is a two-stage route:

1. \`HoloMemoryIndex.shortlist\` performs hex/orbit pruning.
2. \`retrieve_reference\` reuses
   \`GREMLIN_RELATIONAL_MEMORY_SIMILARITY_V0_1\` for final semantic scoring.

Therefore holo memory does not replace the existing semantic scorer. It
reduces candidate count before the existing scorer executes.

If a patch is empty and \`fallback_full=true\`, retrieval falls back to the
complete candidate set. An empty geometric bucket must not silently become a
false negative.

## Rebuild and provenance

Every Holo cell binds:
- memory id / Hive subject id;
- exact ledger record id;
- phase36;
- amplitude36;
- hex coordinate;
- orbit index;
- priority;
- semantic commitment;
- source commitment.

The index is regenerable from ledger rows plus encoded 36D memory packets.

\[
\text{ledger}
\to
\text{remap}
\to
\text{HoloMemoryIndex}
\]

is permitted.

\[
\text{HoloMemoryIndex}
\not\to
\text{rewrite ledger}.
\]

Derived moire patterns remain \`CANDIDATE_ONLY\` and must pass the existing
ELEPHANT / BEES / OWL / HOUND / consolidation / authority boundaries before
persistent promotion.


## NOEMA / Hive materialization bridges

Two read-only bridges are explicit:

1. \`holo_memory_hive_bridge.py\` consumes current \`OrbitalHiveMemory\`
   records and verifies that record ids, subject ids, versions and payload
   hashes are unchanged before/after materialization.
2. \`holo_memory_noema_bridge.py\` consumes receipted
   \`NOEMA_MEMORY_TRACE_V1\` traces.

NOEMA phase provenance is typed:

- \`EXACT_SOURCE_36D\` is allowed only when an exact finite 36D phase packet is
  actually present.
- Otherwise the bridge may derive a fresh candidate 36D representation from
  the explicit receipted semantic body through
  \`GREMLIN_RELATIONAL_MEMORY_ENCODER_V0_1\`.

A derived encoding is never described as recovered historical phase.

The bridge also enforces:

\[
\text{trace hash}\neq\text{semantic coordinate},
\]

and

\[
\text{NOEMA layer }M_k\neq\text{Hive orbit index}.
\]

Without an explicit complete orbit map, NOEMA traces remain orbit-unbound and
receive only the neutral derived-index default. This prevents an accidental
identification of memory-layer number with orbital geometry.

## Bestiary roles

- RAVEN: retrieval/query addressing.
- BEES: local hex-patch coherence, overlap and anti-entropy proposals.
- ELEPHANT: replay/consolidation of validated derived relations.
- SPIDER: typed cross-memory graph relations.
- HOUND: contradictions and confabulation checks.
- OWL: epistemic support audit.
- GREMLIN: aggregate candidate synthesis.
- RAPHAEL: unchanged mutation/admission authority boundary.

No new memory permission is created by this module.

## Synthetic benchmark receipts

### Hex-only, 6000 cells

- queries: 30
- full candidates/query: 6000
- mean Holo candidates/query: 916.07
- mean evaluated fraction: 15.27%
- top-1 agreement with exhaustive scan: 100%
- measured wall-clock speedup: 6.08x

### Hex + orbital, 6480 cells

- 36 orbit indices
- 6 hex phase patches per orbit
- mean Holo candidates/query: 30
- evaluated fraction: 0.463%
- top-1 agreement with exhaustive scan: 100%
- measured wall-clock speedup: 175.22x

These are synthetic structural benchmarks. They demonstrate pruning mechanics
under prepared clustered geometry; they do not establish general semantic
recall performance or production speedup.

## Validation gates

T0 implemented:
- exact 36D input validation;
- exact hex-patch cardinality;
- deterministic rebuild;
- duplicate fail-closed;
- lineage-preserving non-mutating remap;
- moire aligned/anti-phase limits;
- candidate-only authority firewall;
- hex shortlist recall/cost reduction;
- compounded orbit+hex pruning;
- Kuramoto patch coherence increase on deterministic fixture.

Open:
1. real GREMLIN episodic/semantic/relational corpus benchmark;
2. paraphrase and adversarial phase false-negative tests;
3. held-out calibration of \`hex_scale\`, patch radius and orbit band;
4. Liminal Memory transition tests;
5. rebuild/incremental insertion memory-footprint benchmark;
6. random cell/channel-loss degradation;
7. hosted exact-head CI;
8. live NOEMA/QHTRI activation binding as a separate admission step.

Implementation: \`gremlin_mcp/holo_memory.py\`

Tests: \`tests/test_holo_memory_v01.py\`

Benchmarks:
- \`benchmarks/holo_memory_benchmark_v01.py\`
- \`benchmarks/holo_memory_orbital_benchmark_v01.py\`
