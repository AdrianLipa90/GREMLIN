# GREMLIN HoloMemory v0.2 — Recursive Eisenstein Orbital Addressing

Status: \`IMPLEMENTED_CANDIDATE / DERIVED_INDEX_ONLY / NO_MAIN_MERGE\`

Date: 2026-09-23

## Scope

This module defines a testable memory-addressing law over the existing
GREMLIN/HoloMemory stack. It is an indexing and activation geometry, not a new
source of truth and not a claim about biological memory.

Authoritative memory remains the existing GREMLIN / NOEMA append-only memory
surface. v0.2 may derive addresses, shortlist candidates, expose local
complexity and route recall. It may not silently write, delete, overwrite or
canonize memory.

Implementation:
\`gremlin_mcp/eisenstein_orbital_memory.py\`

## 1. Eisenstein carrier

Use

\[
\mathbb Z[\omega],\qquad \omega^2+\omega+1=0,
\]

with

\[
N(a+b\omega)=a^2-ab+b^2.
\]

The six unit directions are

\[
\{\pm1,\pm\omega,\pm\omega^2\},
\]

ordered cyclically by 60 degrees for routing.

## 2. Exact centered-hex identity

For hex radius \(n\),

\[
H_n=1+3n(n+1)=3n^2+3n+1.
\]

Define

\[
\pi_n=(n+1)-n\omega.
\]

Then exactly

\[
\boxed{H_n=N(\pi_n)}.
\]

Thus the number of cells in a complete radius-\(n\) hex patch equals an
Eisenstein norm. This is an exact algebraic invariant, not a metaphor.

## 3. Recursive orbital address

A memory route is a word

\[
w=(a_1,\ldots,a_d),\qquad a_k\in\{0,\ldots,5\}.
\]

For integer base \(B\ge4\), define

\[
Z_0=0,\qquad
Z_{k+1}=BZ_k+u_{a_{k+1}},
\]

where \(u_a\) is the corresponding Eisenstein unit.

Equivalently,

\[
Z_w=\sum_{k=1}^{d}B^{d-k}u_{a_k}.
\]

The exact word remains part of the address. The final coordinate is not used as
a substitute for provenance.

### First-difference separation

For \(B\ge4\), the leading contribution at the first differing symbol dominates
the largest possible tail contribution. Therefore equal-depth words are
injectively represented by \(Z_w\).

The implementation fails closed for \(B<4\).

## 4. Zero, infinite recursion and Poincare disk

Define the normalized point

\[
\xi(w)=\frac{B-1}{B^d}Z_w.
\]

The empty word maps to

\[
\xi(\varnothing)=0.
\]

For every finite non-empty route,

\[
|\xi(w)|^2
=
\frac{(B-1)^2N(Z_w)}{B^{2d}}
<1.
\]

Thus finite recursive addresses lie inside the unit disk without an arbitrary
post-hoc normalization. A constant-direction infinite route approaches the
boundary asymptotically.

This gives a direct exact-to-floating bridge:

\[
\text{root at zero}
\rightarrow
\text{recursive Eisenstein address}
\rightarrow
\text{finite Poincare interior}
\rightarrow
\text{infinite-path boundary limit}.
\]

No physical-space identity is asserted.

## 5. PhaseNav 6x6 -> orbital word

Each existing memory packet contains six 6D projection rows.

For row \(a\),

\[
z_a=
\frac16\sum_{k=0}^{5}
A_{ak}e^{i\phi_{ak}}.
\]

The projection orientation is applied:

\[
\tilde z_a=z_ae^{ia\pi/3}.
\]

The phase of \(\tilde z_a\) is quantized to the nearest of six Eisenstein unit
directions. The resulting sequence is the initial recursive orbital word.

Zero-amplitude rows contribute no invented direction. If every row is inactive,
routing fails closed.

## 6. Typed orbital separation

Three coordinates remain distinct:

1. \`priority_orbit_index\`: existing Hive priority/ring coordinate.
2. \`semantic_orbit_id\`: explicit relational/semantic orbit supplied by a
   trusted graph or caller.
3. \`RecursiveEisensteinAddress\`: derived trajectory address.

No conversion between these types is automatic.

In particular,

\[
M_k\neq\text{semantic orbit}\neq\text{priority orbit}.
\]

## 7. Sparse recall

The index stores every prefix of the recursive word.

A query:

1. derives its 6x6 orbital word;
2. requests the deepest prefix;
3. includes neighboring final directions if configured;
4. backs off one prefix level until \`min_candidates\` is reached;
5. optionally applies an explicit semantic-orbit filter;
6. optionally applies the experimental prime radial filter;
7. reranks the surviving set with the existing
   \`GREMLIN_RELATIONAL_MEMORY_SIMILARITY_V0_1\`.

Therefore the new geometry prunes; it does not replace the semantic scorer.

## 8. Prime radial channels

For prime \(q>3\),

\[
H_n\equiv0\pmod q
\]

has two radial residue classes exactly when \(q\equiv1\pmod6\). They satisfy

\[
n_++n_-\equiv-1\pmod q.
\]

v0.2 computes these two classes using the discriminant

\[
(6n+3)^2\equiv-3\pmod q.
\]

Prime channels are experimental sparse-routing evidence only.

Default:

\[
\texttt{prime_mode=off}.
\]

When \`prime_mode=filter\`, an empty prime intersection falls back to the
pre-prime candidate set rather than creating a false negative.

Prime factorization is not required at query time; configured split primes are
checked by residue class.

## 9. Holographic / moire relation

v0.2 does not replace v0.1 moire memory. It supplies a trajectory hierarchy over
the existing holographic cells:

\[
\text{36D cell}
\to
\text{hex patch}
\to
\text{recursive Eisenstein address}
\to
\text{prefix/orbit shortlist}
\to
\text{moire + semantic rerank}.
\]

This allows overlapping memories to retain local interference while avoiding a
full global scan when routing is sufficiently informative.

## 10. Validation boundary

Required before promotion:
- exact norm identity tests;
- two-root prime-channel tests;
- recursive injectivity tests;
- finite-address Poincare interior tests;
- semantic/priority orbit non-conflation;
- structural sparse-routing benchmark;
- existing 18-paraphrase semantic regression with large distractor set;
- exact-head hosted CI.

A structural speedup is not a semantic-memory result unless semantic recall is
also preserved.
