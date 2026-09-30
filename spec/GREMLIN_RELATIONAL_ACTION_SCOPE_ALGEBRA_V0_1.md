# GREMLIN Relational Action-Scope Algebra v0.1

Status: **CANDIDATE / FAIL-CLOSED / NON-PROMOTING**

## Purpose

This layer converts action safety from an informal checklist into a committed
relational state.

The action state is

\[
G=(T,S,V,A,R,P,L,U,C,F,K,N)
\]

where:

- \(T\): exact target domain,
- \(S\): operation/resource scope,
- \(V\): visibility,
- \(A\): authority modes,
- \(R\): reversibility,
- \(P\): provenance lineage,
- \(L\): relational lineage,
- \(U\): uncertainty,
- \(C\): consequence radius,
- \(F\): fail mode,
- \(K\): consent boundary,
- \(N\): NO-GO hits.

No component grants execution by itself. The algebra is a pre-admission and
scope-control layer.

## Hard invariants

1. Target domain is exact: surface + domain + revision.
2. A child contract may narrow scope; it may not widen it.
3. Authority may only narrow.
4. Visibility may not widen.
5. Provenance and relational lineage may accumulate but may not silently
   disappear during narrowing.
6. NO-GO evidence may accumulate but may not disappear.
7. Any target-domain change requires a new explicit authorization root.
8. High-consequence actions require zero unresolved uncertainty.
9. There is no implicit fallback. Supported fail modes are STOP, QUARANTINE,
   and REQUEST_CONTEXT.
10. Capability is not authority: knowing how to perform an operation does not
    grant permission to perform it.

## Domain transition

For contracts \(G_0,G_1\),

\[
D(G_0,G_1)=1
\]

iff any component of

\[
T=(surface,domain,revision)
\]

changes.

Then the parent contract cannot authorize the candidate:

\[
D=1 \Rightarrow \text{new explicit authorization required}.
\]

This prevents semantic or operational fallback from one repository, branch,
surface or execution domain into another.

## Monotone narrowing

A child \(G_1\preceq G_0\) only if:

\[
S_1\subseteq S_0,\qquad A_1\subseteq A_0,
\]

visibility does not widen, reversibility risk does not increase, uncertainty
does not increase, consequence radius does not widen, fail mode does not
weaken, provenance is retained, relation lineage is retained, and the target
domain is unchanged.

A child is commitment-bound to its parent.

A decrease in uncertainty, or resolution of UNKNOWN visibility/reversibility,
requires new provenance not present in the parent contract. The algebra does
not permit confidence to improve by assertion alone.

## Meet

For same-target contracts the algebra exposes a conservative meet:

- operations/resources: intersection,
- authority: intersection,
- provenance/relation evidence: union,
- NO-GO evidence: union,
- uncertainty: maximum,
- consequence radius: maximum,
- reversibility: conservative/worst-known state,
- consent: hard lattice meet,
- fail mode: stricter mode.

An empty executable intersection fails closed.

Cross-domain meet is forbidden.

## Admission

The relational admission vector evaluates:

\[
(
T,S,A,V,R,P,L,U,F,K,N
)
\]

using the same non-compensating \(-1,0,+1\) lattice already used by the
GREMLIN mathematical constitution.

For high-consequence actions, every gate participates. Therefore:

- any BLOCK -> DENY,
- no BLOCK but at least one UNRESOLVED -> DEFER,
- ALLOW only when every required gate is PASS.

This algebra does not replace the mathematical constitution, RAPHAEL, consent,
reversibility or NO-GO gates. It supplies the missing relational contract that
those layers can bind to.
