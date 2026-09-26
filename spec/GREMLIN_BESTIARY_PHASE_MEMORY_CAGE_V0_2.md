# GREMLIN Bestiary Phase-Memory Cage v0.2

Status: CANDIDATE ENGINEERING INTEGRATION / 20-ROLE PHASE SURFACE / MEMORY-LAW RUNTIME / MAIN NOT MODIFIED

Date: 2026-09-26

## 1. Objective

Arm the full canonical 20-role GREMLIN Bestiary with explicit 36-dimensional
PhaseNav carriers, introduce reviewable binding points, apply the existing
Arithmetic Relational Phase Law (ARPL), apply the existing Memory Law as a
causally effective but bounded scheduling state, and preserve all authority,
provenance and historical-v0.1 firewalls.

The v0.2 layer does not reinterpret the historical 18-carrier v0.1 receipts.

## 2. Three typed geometries

The implementation keeps three objects distinct:

1. Role index geometry: a candidate 10-orthoplex with vertices ±e_1,...,±e_10.
2. Phase carrier geometry: exact T^36 ARPL signatures.
3. Execution graph: the sparse routed GREMLIN task graph.

No claim is made that the execution graph itself is the 1-skeleton of the
orthoplex.

## 3. Candidate binding points

| axis | + | - |
|---:|---|---|
| 1 | HUMMINGBIRD | GREMLIN |
| 2 | OCTOPUS | FERRET |
| 3 | SPIDER | ELEPHANT |
| 4 | RAVEN | BEES |
| 5 | HOUND | BELZEBUB |
| 6 | MOLE | OWL |
| 7 | ANT | MANTIS |
| 8 | FOX | BEAVER |
| 9 | BAT | CANARY |
| 10 | SERPENT | CHAMELEON |

This is an engineering hypothesis and remains CANDIDATE_10_ORTHOPLEX.
The pairs are not promoted as intrinsic semantics.

Each role receives an integer address a in {±1,...,±10}.

## 4. Arithmetic Relational Phase Law binding

Canonical mathematical source:

- repository: AdrianLipa90/On-Primes
- branch: feat/arithmetic-relational-phase-law-v0.1
- artifact: proofs/ARITHMETIC_RELATIONAL_PHASE_LAW_V0_1.md

For each modular channel q,

chi_q(a) = exp(2*pi*i*a/q).

The carrier uses 36 pairwise-coprime moduli from 23 through 193. The role phase
vector is

Theta(a)_j = 2*pi*((a mod q_j)/q_j).

For any addresses a,b,

Theta(b)-Theta(a) == Theta(b-a) (mod 2*pi)

coordinatewise, the finite 36-channel realization of ARPL OP-D029.

Because every selected modulus exceeds the diameter of the finite address set,
the finite signature is injective on this 20-role binding surface.

## 5. Live PhaseNav operator seam

The ARPL role carrier is the deterministic scheduler/reference anchor.

A separate live adapter binds every role to compositions of already existing
PhaseNav operator vectors. No new 36D axis meaning is invented.

ELEPHANT = MEMORY + COMPOSITION + RETURN
BEES     = DIFFERENCE + COMPOSITION + ASSERTION

The live adapter remains fail-loud: canonical live root when required, ACTIVE
binding status, exact finite 36D vectors, no static fallback, and antipodal
cancellation rejected.

## 6. Memory Law binding

Canonical source:

- repository: AdrianLipa90/Memory-Ontology
- artifact: formalism/memory-law-v0.1.md

The operative law is that memory is a persistent, history-dependent modification
of transition structure that causally changes future reachable trajectories.

The runtime stores append-only directed route history:

M_t = (visit counts, transition counts, last role, commitment_t).

For an already admitted candidate role j,

s'_j = s_j + beta*A_t(j),  0 <= beta <= 0.12,

where A_t(j) is directed transition affinity from source roles to j.

Memory may reorder already admitted roles. It cannot add or remove semantic
membership selected by OCTOPUS/policy.

Counterfactual gate: identical current base scores with different stored
histories must be able to produce different future preferred ordering.

## 7. Persistence

With a configured GREMLIN state path, phase memory uses a sibling append-only
JSONL ledger. Every record carries monotone sequence, parent commitment,
SHA-256 self commitment, visit counts, directed transition counts and last role.

Restart recovery validates the entire chain fail-closed.

## 8. Active runtime integration

user task -> semantic graph -> OCTOPUS membership -> derived T^36 state ->
ARPL role anchors -> bounded Memory-Law bias -> schedule order -> WorkerBroker
geometry/phase/state scheduler.

Historical v0.1 numerical suites remain separate:
- scalar/vector/continuous three-way suite: 18-role frozen scope;
- analog specialist invariant suite: 9-role frozen scope.

They are not silently relabeled as 20-role evidence.

## 9. Falsification gates

The v0.2 integration fails if:
1. the 20-role registry is not covered exactly;
2. the 10 candidate pairs fail the orthoplex Gram signature;
3. two ARPL carriers collide;
4. OP-D029 fails on any role pair;
5. ELEPHANT or BEES remains anchor-neutral;
6. memory state fails commitment/parent-chain validation;
7. different histories cannot change future ordering under equal base scores;
8. Memory Law changes semantic membership;
9. live binding silently substitutes a static/fake surface;
10. any new route grants external/canon authority.

## 10. Evidence boundary

The exact algebraic orthoplex and ARPL checks are software/mathematical gates.
The functional dual pairing itself is candidate architecture.
The Memory-Law adapter is an executable causal scheduling mechanism, not proof
of a universal physical memory law. No physical analog-hardware claim is
promoted.

## 11. Main-branch rule

Staged branch: feat/bestiary-phase-memory-cage-v02-20260926.
Do not merge to main without explicit authorization.
