# GREMLIN Adaptive Minimal-Cover Runtime v0.1

Status: `IMPLEMENTED CANDIDATE / DISCRETE ROUTING THEORY / NON-ACTUATING / CHYBA`

Date: 2026-09-22

## Purpose

This layer formalizes adaptive GREMLIN routing as a minimum-closure problem rather than a fixed all-Bestiary pipeline.

It does not replace the existing Cognitive Action Principle. The existing principle governs local continuous/hybrid state dynamics; this layer governs discrete operator selection, obligation closure, causal depth and read-only graph retrieval.

The core claim is algorithmic:

```text
GREMLIN = the minimal causal evolution required to close the declared obligations
          without violating capability, authority, provenance or resource bounds.
```

No claim is made that the graph quantities below are physical gravity, or that causal depth is physical time.

## 1. State

The conceptual runtime state is

```text
X_tau = (M, G, H_tau, Phi_tau, Q_tau)
```

where:

- `M` is durable append-only memory;
- `G` is a relation graph derived from memory;
- `H_tau` is transient expression/activation state;
- `Phi_tau` is a phase/expression state;
- `Q_tau` is the active task.

The write boundary is directional:

```text
M -> G -> H_tau
```

but no reverse update from transient activation to durable memory is admitted without a separate existing memory-admission path.

Therefore

```text
Delta H_tau != 0
```

does not imply

```text
Delta M != 0.
```

## 2. Obligations, not animals, are primary

For a task `q`, define a finite obligation set

```text
O(q) = {o_1, ..., o_n}.
```

Examples include source retrieval, contradiction checking, derivation, provenance validation, synthesis and explicit external actuation.

A Bestiary species exposes tiered operators:

```text
B_i = { B_i^(0), B_i^(1), B_i^(2), B_i^(3) }.
```

The tier names are:

```text
T0 PROBE
T1 LOCAL_CLOSURE
T2 RECURSIVE_CLOSURE
T3 CROSS_DOMAIN_CLOSURE
```

A tier is not "more intelligent". It is a larger closure scope.

The intended capability relation is monotone:

```text
C(B_i^0) subseteq C(B_i^1) subseteq C(B_i^2) subseteq C(B_i^3).
```

The intended resource relation is likewise non-decreasing for a given species/profile.

## 3. Exact minimum capability cover

Let `C(B_i^k)` be the declared capability set of one operator tier.

A valid route `R` must satisfy

```text
union_(B_i^k in R) C(B_i^k) superset O(q).
```

The reference implementation performs exact dynamic programming over the finite obligation subsets. It fails closed above 32 declared obligations rather than silently switching to an approximate set-cover heuristic.

Heterogeneous resources are not collapsed into an arbitrary weighted sum.

For resource vector

```text
c(R) = (tokens, latency, calls, memory)
```

and positive budget vector

```text
B = (B_T, B_L, B_C, B_M),
```

the normalized minimax pressure is

```text
K(R) = max(
  tokens / B_T,
  latency / B_L,
  calls / B_C,
  memory / B_M
).
```

For independent parallel operators, work-like quantities are additive while critical latency is the maximum branch latency.

The deterministic route ordering is lexicographic:

1. smallest `K(R)`;
2. fewest operators;
3. smallest aggregate tier;
4. stable operator identifier order.

This ordering makes tie-breaking explicit and auditable.

## 4. Minimal-tier principle

If a lower tier closes the same required obligations at no greater resource pressure than a higher tier, the higher tier is dominated for that routing state.

Operationally:

```text
never escalate without an unmet obligation
```

is implemented by keeping an obligation frontier.

Given current frontier `O_tau`, closed obligations `C_tau`, and newly discovered obligations `D_tau`:

```text
O_(tau+1) = (O_tau - C_tau) union D_tau.
```

Escalation is generically required iff the resulting frontier is non-empty.

Authority checks remain separate: satisfying an obligation never grants write, execution, publication or canon authority.

## 5. Causal time tau

Tau is defined as computational causal depth, not wall-clock time.

For an operation `a_j` with causal parents `a_i`:

```text
tau(a_j) =
  0                                      if a_j has no parents
  1 + max_(a_i prec a_j) tau(a_i)       otherwise.
```

Independent operations may share the same `tau` layer and execute concurrently.

The route depth is

```text
tau(R) = max_a tau(a),
```

the longest dependency-chain depth.

Dependency cycles fail closed because no finite causal layering exists.

## 6. Relational graph and exact Laplacian

Let memory relations induce an undirected weighted graph

```text
G = (V,E)
```

with positive conductances `w_ij`.

Let `B` be an incidence matrix and `W` the diagonal conductance matrix. The graph Laplacian is

```text
L = B W B^T.
```

### Correction to the single-source shorthand

For a free graph Laplacian, `L phi = b` is solvable only for a balanced injection satisfying

```text
1^T b = 0.
```

Therefore a bare `b=e_q` source is not the admitted v0.1 definition.

The exact source-target injection is

```text
b_(q,v) = e_q - e_v.
```

This yields pairwise effective resistance

```text
R_eff(q,v) = (e_q-e_v)^T L^+ (e_q-e_v).
```

where `L^+` is the Moore-Penrose pseudoinverse.

For reachable nodes, the software relational-gravity score is

```text
g_rel(v|q) = 1 / R_eff(q,v).
```

Unreachable nodes receive zero score. The query node itself is omitted.

This is graph conductance / effective resistance. The term "relational gravity" is a GREMLIN software metaphor and does not assert physical gravity.

Multiple independent paths reduce effective resistance and therefore raise the relational-gravity score naturally, without embedding-similarity weights.

## 7. Phase / hypercrystal modulation

The structural graph provides base conductance `W_0`.

An external read-only expression layer may provide finite non-negative edge activation factors:

```text
E(Phi_tau).
```

Then

```text
W_tau = W_0 odot E(Phi_tau)
L_tau = B W_tau B^T.
```

The v0.1 implementation does not invent an activation law. It only validates and applies caller-owned factors.

Therefore:

```text
genome / durable memory -> what is stored
graph                   -> how stored records are related
expression / hypercrystal -> what is currently activated
relational gravity      -> what the graph makes close to the query
router                   -> what obligations must be closed
tau                      -> how deep causal execution has progressed
```

The expression layer is read-only with respect to durable memory.

## 8. Adaptive action principle

The discrete routing layer is

```text
(X_tau, U_tau) --R_tau--> (X_(tau+1), U_(tau+1))
```

with

```text
R_tau = MinRoute(U_tau, G_tau, A, B)
```

where:

- `U_tau` is the unresolved obligation frontier;
- `G_tau` is the current relation/expression graph;
- `A` is the external authority/capability boundary;
- `B` is the resource budget.

Termination requires

```text
U_tau = empty
```

and all separately mandatory gates to be satisfied.

The reference objective is lexicographic minimization of

```text
(tau(R), K(R))
```

subject to closure and external authority/provenance constraints. v0.1 implements the exact minimum capability cover, minimax pressure, causal `tau`, obligation transition and relational graph primitives; it does not yet replace the production OCTOPUS routing path.

## 9. Relationship to existing GREMLIN components

This candidate layer is compatible with, but does not supersede:

- `gremlin_mcp/router.py` / OCTOPUS semantic routing;
- `spec/GREMLIN_COGNITIVE_ACTION_PRINCIPLE_V0_1.md`;
- Bestiary capability and memory contracts;
- Hive append-only memory authority;
- RAPHAEL / constitutional mutation boundaries;
- genetic/hypercrystal memory candidate layers when separately admitted.

A future integration can use OCTOPUS evidence to propose obligations, then use this runtime to choose the minimum tiered cover. That integration must be benchmarked by ablation before replacing the existing route selector.

## 10. Candidate theorems / executable invariants

v0.1 tests the following software propositions:

1. **Exact cover:** every returned plan covers every declared obligation.
2. **Fail-closed incompleteness:** an uncovered obligation raises instead of producing a partial route.
3. **Lower-tier dominance:** when two same-species tiers cover the same obligation and the lower tier has lower minimax pressure, the exact planner selects the lower tier.
4. **Parallel causal depth:** independent operations occupy the same `tau` layer; a dependent synthesis step increases depth by one.
5. **Cycle rejection:** cyclic causal dependencies fail closed.
6. **Resistance path law:** adding a genuinely independent parallel path lowers effective resistance between its endpoints.
7. **Disconnected isolation:** unreachable memory nodes receive zero relational gravity.
8. **Read-only phase modulation:** phase/expression factors change graph conductances only; they do not mutate a memory object.
9. **No authority promotion:** runtime receipts remain `COGNITIVE_ROUTING_ONLY / CHYBA / canon_allowed=false`.

## 11. Evidence boundary

PASS establishes only software-level properties of the candidate planner and graph mathematics.

It does not establish:

- a universal principle of cognition;
- physical time from `tau`;
- physical gravity from `g_rel`;
- a biological memory mechanism;
- that the 36D PhaseNav/hypercrystal layer is a physical substrate;
- that adaptive minimal-cover routing is superior to current OCTOPUS routing on real workloads.

The latter requires explicit A/B ablation on frozen tasks and cost/quality metrics.

Implementation:

`gremlin_mcp/adaptive_runtime.py`

Tests:

`tests/test_gremlin_adaptive_minimal_cover_runtime_v01.py`
