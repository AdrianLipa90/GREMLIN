# GREMLIN Holographic Orbital Memory v0.1

Status: `IMPLEMENTED CANDIDATE / DERIVED_INDEX_ONLY / APPEND_ONLY_LEDGER_PRESERVED / CHYBA`

Date: 2026-09-23

## Purpose

Add a rebuildable holographic/orbital working-memory layer above existing GREMLIN memory without replacing or mutating the authoritative append-only Hive ledger.

The design reuses existing GREMLIN components:

- `OrbitalHiveMemory` for content-addressed append-only relational memory;
- `GREMLIN_RELATIONAL_MEMORY_BEASTS_V0_1` for 6 x 6 = 36D memory traces;
- BEES for local overlap/coherence and anti-entropy proposals;
- ELEPHANT for replay/consolidation proposals;
- the existing Kuramoto-like phase sector in the Cognitive Action Principle;
- PhaseNav 36D coordinates as explicit derived/runtime addressing.

It does not grant mutation, canon or external actuation authority.

## 1. Memory cell

Every holographic memory cell is a 36D phase state

[
X^{(mu)}_{ak}=A^{(mu)}_{ak}e^{i	heta^{(mu)}_{ak}},
qquad a,kin{0,ldots,5}.
]

The factorization is preserved:

[
36=6_{m projection/context}	imes 6_{m lateral/channel}.
]

The durable payload remains in Hive. The phase cell is a derived coordinate attached by explicit lineage.

## 2. Holographic projection

For source memories (mu=1,ldots,M), non-negative weights (w_mu) and explicit relational phases (ho_mu), define coordinate-wise

[
H_j=rac{1}{sum_mu w_mu}
sum_mu w_mu e^{i(	heta^{(mu)}_j+ho_mu)}.
]

The working hologram stores

[
phi_j=arg H_j,qquad A_j=|H_j|.
]

Thus constructive and destructive interference are explicit. No holographic state is authoritative by itself.

The pairwise memory-moire overlap is

[
oxed{
mathcal C_{mu
u}
=
left|rac1{36}sum_{j=1}^{36}
e^{i(	heta^{(mu)}_j-	heta^{(
u)}_j)}ight|
}
in[0,1].
]

It measures coherence of the relative phase pattern, not truth.

## 3. BEES hexagonal patch topology

BEES patches are implemented as a derived hexagonal index, not as a new persistence layer.

For each 6-row cell, compute row phasors

[
u_a=rac16sum_{k=0}^{5}e^{i	heta_{ak}}.
]

Take the first two sixfold DFT harmonics

[
h_1=rac16sum_a u_a e^{i2pi a/6},
qquad
h_2=rac16sum_a u_a e^{i4pi a/6},
]

and define the planar indexing carrier

[
z=h_1+rac12h_2.
]

`z` is deterministically quantized onto axial hex coordinates `(q,r)`. The map is an index coordinate only; it does not assert semantic truth.

Local BEES neighborhoods are standard hex rings around `(q,r)`.

## 4. Orbital shell

Global cell coherence

[
K=left|rac1{36}sum_j e^{i	heta_j}ight|
]

is mapped monotonically to one of a configurable number of orbital shells. Higher coherence occupies an inner shell.

This shell is a retrieval/index shell and remains distinct from scheduler radius `r`, PNLF circular phase distance `r_phase`, and any physical radial coordinate.

## 5. Orbital/hex remapping

The derived address is

[
mathcal A(X)=(O,q,r,s),
]

where `O` is orbital shell, `(q,r)` the BEES hex patch and `s` a sixfold orientation sector.

A remap is a pure rebuild:

[
oxed{
	ext{Hive records + 36D attachments}
longrightarrow
	ext{new holographic index}
}
]

with a deterministic mapping commitment. The index can be deleted and reconstructed without loss of ledger history.

## 6. Kuramoto update

The existing GREMLIN phase action supplies the local dynamics. For memory cells (mu,
u),

[
V=-sum_{mu<
u}w_mu w_
u
rac1{36}sum_j
cos(	heta^{(mu)}_j-	heta^{(
u)}_j).
]

The bounded overdamped update is

[
dot	heta^{(mu)}_j
=
K_c
rac{sum_
u w_
u
sin(	heta^{(
u)}_j-	heta^{(mu)}_j)}
{sum_
u w_
u}.
]

The reference implementation provides finite-step relaxation and a potential test. It operates only on derived working copies.

## 7. PhaseNav / QHTRI carrier transport

A caller may supply an explicit 36D carrier (q_j) and gain (g):

[
	heta'_j=	heta_j+gq_jpmod{2pi}.
]

This transform is exactly reversible with (-g). It is a software phase-transport adapter only; v0.1 does not claim physical QHTRI execution or analog substrate identity.

## 8. Retrieval

```text
query 36D cell
 -> orbital shell
 -> BEES hex patch
 -> local hex rings + adjacent shells
 -> exact moire/phase rerank inside candidate set
 -> retrieval receipt
```

This is a prefilter. It trades exact global nearest-neighbor identity for fewer exact comparisons unless the caller widens or falls back to a full scan.

## 9. Authority firewall

The holographic layer may derive projections, compute moire/coherence, rebuild the index, perform bounded Kuramoto relaxation on working copies, and propose candidates.

It may not mutate/delete/overwrite Hive memory, treat coherence as truth, promote canon, bypass consolidation receipts, directly persist holographic reconstructions, widen RAPHAEL/FERRET authority, or claim physical QHTRI execution.

Durable write route remains:

```text
holographic candidate
 -> OWL/HOUND evidence audit
 -> PhaseNav semantic/consolidation route
 -> accepted lineage/receipt
 -> append-only RELATIONAL Hive ingest
```

## 10. Synthetic benchmark

`benchmarks/gremlin_holographic_orbital_memory_v01.py` compares orbital/hex prefiltering with an exact full scan over deterministic synthetic clustered 36D phase memories.

The benchmark is explicitly `DETERMINISTIC_SYNTHETIC_REFERENCE_ONLY`. Two profiles are retained:

- `BALANCED`: wider patches, higher recall;
- `AGGRESSIVE`: narrower patches, larger comparison reduction.

## 11. Open gates

1. Bind actual Hive records to 36D cells through explicit PhaseNav receipts.
2. Benchmark on real GREMLIN research-memory traces.
3. Compare with brute force, ANN/vector DB and current RAVEN retrieval.
4. Measure wall-clock latency, memory footprint, provenance bytes and false-recall rate.
5. Test partial-cue completion and interference under BEES overlap loss.
6. Add a typed Poincare adapter only after its radius is derived.
7. Add Zero/Infinity algebra bindings as separate typed transforms with deterministic invariance tests.

## Implementation

- `gremlin_mcp/holographic_orbital_memory.py`
- `tests/test_holographic_orbital_memory_v01.py`
- `benchmarks/gremlin_holographic_orbital_memory_v01.py`
