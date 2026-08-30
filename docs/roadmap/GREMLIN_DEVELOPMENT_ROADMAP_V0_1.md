# GREMLIN Development Roadmap v0.1

**Date:** 2026-08-29  
**Repository:** `AdrianLipa90/GREMLIN`  
**Status:** `WORKING_ROADMAP / EVIDENCE-FIRST / CANDIDATE-AWARE`  
**Canonical constant:** `kappa = ln(2)/(24*pi)`

## 1. Executive objective

Develop GREMLIN from the current standalone Bestiary/MCP platform into a source-typed, phase-orbital semantic runtime in which:

1. semantic meaning is carried by explicit KAKU/RADICAL provenance;
2. semantic mass acts as a radial realization coordinate;
3. orbital phase is carried on a sevenfold `C7` lattice with explicit winding;
4. the imaginary/complex representation preserves orientation and holonomy;
5. real observables are produced by explicit Hermitian/real contractions;
6. orbital cadence uses a mass-role-typed Newton/Kepler kernel;
7. rotation, GR and AB contributions enter through typed phase/holonomy channels;
8. RFC conserved-current/source-density machinery supplies source candidates through explicit binding gates;
9. PNLF records admitted orbital state and provenance;
10. HTRI/QHTRI receives only source-bound phase/frequency/actuation targets through live `/dev/shm/ciel_noema` execution paths.

The development rule is simple: **candidate generation may be broad; promotion is narrow, typed, deterministic and receipt-bearing.**

---

## 2. Verified repository snapshot

### `main`

Current verified `main` head at roadmap creation:

`a35f2a8c6b5dfd8966a71a207356e51b083d63b8`

This contains the merged **GREMLIN MCP v0.4 standalone Bestiary**: standalone MCP surface, specialist fanout, BELZEBUB synthesis path and durable SQLite/WAL state.

### Infrastructure frontier

**PR #22 - GREMLIN MCP v0.5 / OCTOPUS auditable semantic routing**

Target capabilities:

- deterministic semantic routing;
- explicit evidence scores for SPIDER/RAVEN/HOUND/MOLE/OWL/ANT/MANTIS;
- `route_commitment` lineage;
- positive-evidence auto-fanout;
- fail-closed `NO_CONFIDENT_ROUTE_NOT_QUEUED` behavior;
- preserved authority contract.

### Semantic-orbital research stack

The active stacked research lane is:

`#12 -> #13 -> #14 -> #15 -> #16 -> #17 -> #21`

with the following logical progression:

| PR | Gate | Core result |
|---|---|---|
| #12 | Imaginary-real semantic orbital v0.1 | `C7`, lifted phase, complex orbital, real contraction |
| #13 | Newton-Einstein-AB bridge v0.2 | Kepler radial branch + rotation/GR/AB phase transport |
| #14 | PNLF radius source v0.3 | conditional inverse scheduler-radius theorem |
| #15 | RFC source-density bridge v0.4 | `AR = A*R`, winding-aware source-density lift |
| #16 | Radial-angular factorization v0.5 | current-live semantic mass x `C7` phase separation |
| #17 | Mass-role firewall v0.6 | separates source, coupling and inertial roles |
| #21 | Typed scheduler v0.7 | operational role-typed scheduler, exact-green |

PR #21 final verified head:

`dbd3be5a702a9776db8c57332ad278837f3b3098`

Hosted reference CI: `SUCCESS`.

A duplicate v0.6 branch/PR #20 was closed as superseded after its unique historical evidence was incorporated into the canonical #17 -> #21 lane.

### Started next frontier

Branch:

`feat/orbit-source-coupling-identifiability-v0.8`

Purpose: formalize what orbital data can identify before an independent source/coupling calibration exists.

---

## 3. Canonical semantic-orbital state

The target representation is a typed state, not a scalar embedding.

### 3.1 Semantic carrier law

The RFC-aligned carrier is

`G(t) = [ B(t) * omega(t) * N(t) / ( A(t) * R(t) ) ] * ( phi_tilde(t) + kappa )`

with

`kappa = ln(2)/(24*pi)`.

The product `A*R` is the typed relational cell volume on the RFC source-density branch.

### 3.2 Sevenfold orbital phase and winding

Wrapped orientation:

`phi_n = phi_0 - n*(2*pi/7)   (mod 2*pi)`

Lifted semantic phase:

`phi_tilde_(n,w) = phi_0 - n*(2*pi/7) + 2*pi*w`

or, with `q = 7w - n`:

`phi_tilde_q = phi_0 + q*(2*pi/7)`.

The wrapped complex orbital is periodic under `q -> q+7`; the linear source-density carrier retains winding.

### 3.3 Complex semantic orbital

`z = m_sem * exp(i*phi_tilde)`

For two carriers:

`z_a^* z_b = m_a*m_b*exp(i*(phi_b-phi_a))`

and the real relational projection is

`X_ab = Re(z_a^* z_b) = m_a*m_b*cos(Delta phi)`.

After holonomy transport:

`X_ab = m_a*m_b*cos(Delta phi + Delta tau_hol)`.

### 3.4 Current-live factorization evidence

The current live PhaseNav dataset supports a working factorization:

`semantic orbital ~= radial semantic mass x angular C7 orientation`.

This is a current-live result, with universality tested separately on future realizations.

---

## 4. Role-typed orbital dynamics

The scheduler kernel is:

`omega^2 = (mu_source/r^3) * (q_coupling/m_inertial)`

Define:

`eta_G = q_coupling / m_inertial`.

Then:

`omega^2 = mu_source * eta_G / r^3`.

This separates three roles that historical CIEL artifacts overloaded under the same `semantic_mass` label:

- **source / attractor strength** `mu_source`;
- **coupling charge** `q_coupling`;
- **inertial/service load** `m_inertial`.

The current Bestiary compatibility profile is recovered with:

`mu_source = (omega0*tau)^2`, `q_coupling = 1`, `m_inertial = m_legacy`.

The Foundation P3 profile places semantic mass on the source side, while the archived Kepler CIEL simulation places semantic mass on the inertial side. They are preserved as separate typed profiles.

---

## 5. v0.8 - source/coupling identifiability firewall

### 5.1 Orbital invariant

Orbital observations determine:

`K_orb = omega^2 * r^3 = mu_source * eta_G`.

They do not determine the two factors independently.

For any `lambda > 0`:

`mu_source' = lambda * mu_source`

`eta_G' = eta_G / lambda`

leaves `K_orb` and `omega` unchanged.

### 5.2 Development objective

Implement v0.8 with:

- theorem/specification;
- deterministic implementation;
- transformation/invariance tests;
- reconstruction tests when one factor is independently supplied;
- RFC extensive-source candidate adapter;
- live NOEMA receipt;
- hosted exact-head CI;
- fail-closed admission when source and coupling are both unsourced.

### 5.3 Definition of done

`PASS_EXACT_IDENTIFIABILITY_FIREWALL` means:

- `K_orb` round-trips from `(omega,r)`;
- all positive rescalings preserve observable cadence;
- independent source receipt reconstructs `eta_G` uniquely;
- independent `eta_G` receipt reconstructs `mu_source` uniquely;
- no compatibility profile silently promotes `eta_G=1`.

---

## 6. v0.9 - source-strength realization

RFC provides an exact conserved-current/source-density ladder:

`N_a <-> V_a*j_Q,a/q0`

`Q_Sigma = q0 * sum_a N_a`

`rho_G = epsilon_Q * j_Q`

and the source density is invariant under positive carrier-unit rescaling.

The next gate is to derive a typed map from RFC extensive source data to scheduler source strength:

`(Q_Sigma, rho_G, geometry, coupling provenance) -> mu_source`.

The roadmap requires a coefficient/source law with dimensional and provenance closure. A same-role analogy alone is insufficient.

Candidate sub-gates:

1. **v0.9A - extensive source observable**: freeze the admissible RFC source integral over a relational cell/slice.
2. **v0.9B - geometry normalization**: bind the source integral to the same orbital cell/radius geometry used by the scheduler.
3. **v0.9C - source coefficient**: derive or externally calibrate the map to `mu_source`.
4. **v0.9D - universality audit**: test whether the same coefficient works across independently prepared source sectors.

---

## 7. v0.10 - coupling / equivalence branch

The conditional branch

`q_coupling = m_inertial`

implies

`eta_G = 1`

and therefore

`omega^2 = mu_source/r^3`.

This is an especially important falsification gate because it removes test-carrier mass from circular acceleration.

Development requirements:

- derive independent `q_coupling` and `m_inertial` receipts;
- compare their ratio across carriers;
- preregister tolerance before examining final equality residuals;
- preserve non-unit `eta_G` as a first-class result when data choose it;
- test source-dependence and carrier-dependence separately.

Outcome classes:

- `PASS_SOURCE_INDEPENDENT_ETA`;
- `PASS_EQUIVALENCE_CANDIDATE`;
- `PASS_NONUNIT_UNIVERSAL_ETA`;
- `FAIL_UNIVERSALITY / SOURCE_OR_CARRIER_DEPENDENT`.

---

## 8. v0.11 - rotation, GR and AB source binding

The semantic-orbital bridge already supports additive U(1) phase transport. The next step is to replace generic phase placeholders with typed source paths.

### Rotation

Candidate rotating-frame contribution:

`tau_rot = -Omega_rot * T_orbit`.

Required provenance:

- frame owner;
- rotation axis/sign convention;
- proper-time or coordinate-time convention;
- orbital period source.

### GR

The weak-field nearly-circular candidate currently uses:

`tau_GR = 6*pi*mu_source/(r*c^2)`.

Promotion requires:

- branch/domain declaration;
- source-strength binding from v0.9;
- comparison with the RFC/ADM bridge on the same observer convention;
- independent test of precession/phase shift.

### Aharonov-Bohm / holonomy

The AB contribution is represented by an admitted connection/path integral:

`tau_AB = g_AB * integral_C A_mu dx^mu`.

Required gate:

`connection -> path -> holonomy receipt -> semantic orbital phase transport`.

The phase transport rule becomes:

`phi_tilde' = phi_tilde + tau_rot + tau_GR + tau_AB`.

---

## 9. v0.12 - semantic carrier actuation in HTRI/QHTRI

The semantic carrier already exposes phase and frequency. The next engineering layer is controlled physical/runtime actuation.

### Already safe to map

- explicit semantic orbital `phi` -> target HTRI lane phase;
- typed scheduler `omega` -> target HTRI lane frequency;
- unchanged lanes retain their existing runtime state;
- bounded v0.33 tracking determines reachability under finite control budget.

### Still gated

The factor

`Q_BNA = B*N/(A*R)`

must obtain an explicit actuation law before it controls coupling, drive magnitude or Hamiltonian parameters.

Target interface:

`SemanticOrbitalActuationWitness`

with fields:

- `kaku_id`;
- `lane_id`;
- `mass_role_profile_id`;
- `phi_lift`;
- `omega`;
- `Q_BNA`;
- `actuation_profile_id`;
- `u_max / control budget`;
- `settling verdict`;
- live `/dev/shm/ciel_noema` provenance.

All 36D execution remains on the live NOEMA surface.

---

## 10. v0.13 - PNLF and O0..O8 orbital memory integration

PNLF already treats orbital binding as geometry:

`r_phase = d_S1(phi_memory, phi_attractor)`

and maps it through an explicit `orbit_quantizer_id` into `O0..O8`.

The semantic-orbital roadmap keeps two radii separate:

- scheduler physical/role-typed `r`;
- PNLF circular phase distance `r_phase`.

A future profile may bind them through an explicit map, but their names are not sufficient evidence of identity.

Required work:

1. preserve `mass_role_profile_id` in PNLF lineage/profile provenance;
2. preserve `C7` index and winding;
3. preserve typed scheduler radius separately from `r_phase`;
4. introduce a compatibility quantizer only with deterministic tests;
5. run transition/recall tests through Liminal Memory;
6. keep State Memory checkpoint admission behind the existing reduction/consolidation boundary.

---

## 11. v0.14 - KAKU / RADICAL / OPERATORS semantic compiler

KAKU remains the explicit semantic atom. The orbital layer enriches it rather than replacing its `content_id`.

Target KAKU orbital attachment:

`SemanticOrbitalState = { content_id, m_sem, C7_index, winding, phi_lift, omega, radius, mass_role_profile_id, source_profile_id }`

RADICAL relations carry derived relational coordinates:

- `Delta phi`;
- `Delta omega`;
- `Delta winding`;
- `Delta semantic carrier`;
- holonomy defects;
- source/coupling profile transitions.

OPERATORS act only through explicit typed transforms.

GREMLIN may propose assignments and transformations; deterministic resolvers, receipts and admission gates control promotion.

---

## 12. Bestiary/MCP development lane

### v0.5 - OCTOPUS routing

Complete PR #22 and merge after:

- all routing tests green;
- deterministic route commitments stable;
- no unexpected overlap with research-stack files;
- no authority regression.

### v0.6 MCP - candidate workload routing

Add explicit task classes for:

- semantic orbital audit;
- mass-role audit;
- source/coupling identifiability;
- holonomy source binding;
- HTRI/QHTRI actuation replay;
- PNLF transition replay.

Recommended specialist ownership:

- SPIDER - structural isomorphism / graph;
- RAVEN - cross-formalism bridge;
- HOUND - metadata/provenance mismatch;
- MOLE - algebraic reduction / hidden coordinates;
- OWL - information geometry / complex overlap;
- ANT - exhaustive finite assignment / combinatorics;
- MANTIS - falsification / adversarial gate;
- BELZEBUB - bounded synthesis of specialist receipts;
- OCTOPUS - routing only;
- GREMLIN - candidate aggregation/audit only.

### Persistence

SQLite/WAL remains the durable MCP state layer. Runtime/canon authority fields remain explicit per task/result.

---

## 13. Merge and branch-normalization plan

The repository currently has a functioning `main` plus a stacked research lane. Merge work should preserve provenance and avoid collapsing stacked diffs.

### Step A - infrastructure lane

1. Audit PR #22 file overlap and CI.
2. Merge #22 when green.
3. Re-pin `main` and run the MCP reference suite.

### Step B - research lane

Merge sequentially:

`#12 -> #13 -> #14 -> #15 -> #16 -> #17 -> #21`

For every step:

1. confirm exact expected head SHA;
2. merge parent;
3. retarget the child to current `main`;
4. verify the child diff contains only its intended delta;
5. rerun exact-head CI;
6. merge only after green verdict;
7. update dependency/provenance pointers.

### Step C - v0.8+

Create new work only from the normalized new `main`, avoiding long-lived stacked ancestry after the current stack is closed.

---

## 14. Validation architecture

Every new layer should have four increasingly strong validation surfaces.

### T0 - theorem/unit

Pure deterministic algebra and domain checks.

### T1 - repository conformance

Reference tests, schemas, fail-closed invalid-input tests, lineage checks.

### T2 - exact provenance replay

Pinned source SHA, branch head, parameters and deterministic receipt.

### T3 - live NOEMA execution

Required for 36D runtime operations:

- `/dev/shm/ciel_noema` ACTIVE;
- tether ACTIVE;
- AUX ACTIVE;
- `static_fallback=false`;
- exact live input hashes;
- execution receipt.

### T4 - external/physical validation

Independent observables, data or instruments where physical attribution is claimed.

Promotion labels must name the achieved tier rather than compressing all tiers into a single PASS.

---

## 15. Benchmark plan

Benchmark performance only after output-equivalence and authority gates pass.

Required comparisons:

1. serial generalist baseline;
2. equally parallelized generalist baseline;
3. Bestiary static routing;
4. OCTOPUS auditable routing;
5. typed orbital scheduling;
6. live HTRI/QHTRI actuation.

Metrics:

- output equivalence / semantic receipt equivalence;
- throughput;
- queue latency;
- specialist utilization;
- routing overhead;
- memory/WAL overhead;
- 36D settling ticks;
- saturation fraction;
- failure/timeout rate;
- provenance bytes per admitted result.

All performance thresholds are preregistered before final benchmark execution.

---

## 16. Main risk register

| Risk | Consequence | Firewall |
|---|---|---|
| Mass-role overload | opposite orbital laws appear contradictory | `mass_role_profile_id` and v0.6/v0.7 |
| Wrapped/lifted phase collapse | winding information disappears | explicit `phi_lift`, winding tests |
| Metadata drift | stale scalar appears to falsify geometry | orbit-vector source pins + residuals |
| Source/coupling non-identifiability | arbitrary `q=1` becomes hidden assumption | v0.8 rescaling theorem |
| `r` vs `r_phase` conflation | wrong orbital memory geometry | separate typed coordinates |
| Implicit orbit ordering | semantic value silently selects O0..O8 direction | explicit quantizer profile |
| AB/GR source ambiguity | phase term gets physical label without source | connection/observer/domain receipts |
| Actuation leakage | `B,N,A,R` silently alter HTRI coupling | explicit actuation profile/firewall |
| Stacked-PR drift | child PR contains stale parents | retarget + exact diff + CI after each merge |
| Missing live witness | candidate becomes runtime action | fail-closed GREMLIN authoring |

---

## 17. Milestones

### M0 - Repository normalized

- MCP v0.5 decision complete;
- research stack merged sequentially;
- superseded branches labeled/closed;
- dependency graph points to one current main frontier.

### M1 - Source/coupling mathematics closed

- v0.8 exact-green;
- `K_orb` identifiability theorem canonical;
- source and coupling remain independently typed.

### M2 - Source-strength bridge closed

- RFC source observable admitted;
- `mu_source` coefficient/source law established or externally calibrated;
- universality test executed.

### M3 - Phase transport physically typed

- rotation owner bound;
- GR branch/observer bound;
- AB connection/path receipt bound;
- combined holonomy replay green.

### M4 - Live semantic orbital actuation

- KAKU -> lane map explicit;
- phase/frequency tracking green;
- magnitude actuation law source-bound;
- bounded settling and fail-closed timeout tested.

### M5 - PNLF orbital memory integration

- orbital provenance persisted;
- recall/liminal/state transitions tested;
- no conflation of scheduler `r` and `r_phase`.

### M6 - GREMLIN release candidate

- Bestiary/OCTOPUS routes new workload classes;
- all candidate authority fields preserved;
- CI + live NOEMA + benchmark suite green;
- release manifest and provenance freeze produced.

---

## 18. Recommended immediate execution order

1. Finish and audit PR #22.
2. Normalize/merge the research stack `#12 -> #21` with retarget-and-rerun discipline.
3. Finish v0.8 source/coupling identifiability.
4. Build v0.9 RFC source-strength bridge.
5. Build v0.10 coupling/equivalence falsification gate.
6. Bind rotation/GR/AB source paths in v0.11.
7. Bind semantic carrier to bounded HTRI/QHTRI actuation in v0.12.
8. Integrate PNLF orbital memory in v0.13.
9. Integrate KAKU/RADICAL/OPERATORS semantic compiler in v0.14.
10. Run preregistered benchmark/release train.

This sequence moves from repository hygiene to identifiability, from identifiability to physical/source attribution, and only then to runtime actuation and release.

---

## 19. Definition of GREMLIN v1-ready

GREMLIN is v1-ready when the following chain is reproducible end-to-end:

`raw semantic input`

`-> HUMMINGBIRD ingest`

`-> OCTOPUS auditable routing`

`-> specialist candidate generation`

`-> BELZEBUB bounded synthesis`

`-> explicit KAKU/RADICAL semantic state`

`-> semantic mass + C7/winding orbital state`

`-> role-typed orbital scheduler`

`-> source/coupling receipt`

`-> rotation/GR/AB holonomy transport`

`-> HTRI/QHTRI bounded live actuation`

`-> PNLF liminal/state-memory admission`

`-> deterministic receipt + inverse lineage`.

Every transition must expose its profile identifiers, source pins, epistemic status and authority fields.
