# GREMLIN ARPL × Fractal-Orbital × 36D Overlap Audit

Date: 2026-09-26
Status: CROSS_REPO_AUDIT_PASS / SOURCE_PIN_REPAIRED / ADAPTER_FAIL_PRESERVED / PHYSICAL_BINDING_OPEN

## 1. Scope

This audit consolidates the current arithmetic-relational phase, fractal-orbital
Hilbert, overlap-Gram and PhaseNav 36D branches.

The goal is not to add a new prime theorem or a new physical claim.

The goal is to determine which bridges are exact, which are representation
contracts, which adapters fail, and which witnesses are still missing.

## 2. Live NOEMA state at audit

The local NOEMA AUX tether guard reported:

\[
\text{tether status}=\text{ACTIVE},
\]

with no failures in the guard result.

This runtime state is operational provenance only. It does not promote any
mathematical or physical theorem.

## 3. Current immutable source pins

### On-Primes repaired integration snapshot

Repository:

AdrianLipa90/On-Primes

Branch:

integrate/arpl-fractal-orbital-bridge-v0.2-20260926-r4

Pinned head:

\[
\boxed{
22171349917c97392db7d35605f15be1441fa5bb
}
\]

Immediate compare against active parent at pin/receipt time:

ahead_by = 6

behind_by = 0

The repaired snapshot contains:
- two bridge proof notes;
- two validation receipts;
- executable bridge module;
- bridge tests.

The previous source pin

\[
705872f11aaf8b933ab3b713fb10443326fde62b
\]

is superseded.

Reasons:
- stale/diverged parent ancestry;
- missing Fraction import in the old bridge module.

### Orbital-System-base overlap-stabilizer snapshot

Repository:

AdrianLipa90/Orbital-System-base

Branch:

formalism/fractal-orbital-moire-hilbert-v0.8-20260926

Validation receipt commit:

\[
074f04328f7a615928d24b33474acb056e151985.
\]

### PhaseNav / NOEMA latest provenance layer

Repository:

AdrianLipa90/noema-phasenav-core

Branch:

formalism/fractal-moire-hilbert-36d-bridge-v0.10-20260926

Validation receipt commit:

\[
2006fcad8e6c02ab4df5f26d98b15bdc82658ed9.
\]

## 4. Exact ARPL source mathematics retained

The active ARPL branch already supplies:

1. exact modular character phase law;
2. exact complete prime-power residue signature;
3. exact ordered-gap reconstruction;
4. exact dyadic phase transport;
5. exact procyclic phase refinement tower;
6. exact cumulative clocks

\[
L_N=\operatorname{lcm}(e_1,\ldots,e_N);
\]

7. exact refinement factors

\[
b_N=\frac{L_{N+1}}{L_N};
\]

8. exact Haar cylinder measures;
9. exact canonical arithmetic ultrametric;
10. exact ARPL phase-covering Gram matrix.

None of these statements by itself proves a new asymptotic prime-distribution
law, the twin-prime conjecture, RH, or a physical prime law.

## 5. Exact refinement-channel bridge

For one refinement step

\[
L_{N+1}=b_NL_N,
\]

the bridge defines cross-level child isometries

\[
V_{N,c}.
\]

They satisfy

\[
\boxed{
V_{N,c}^*V_{N,d}
=
\delta_{cd}I
}
\]

and

\[
\boxed{
\sum_cV_{N,c}V_{N,c}^*
=
I.
}
\]

The finite odometer translation has the exact carry law

\[
\boxed{
U_{N+1}V_{N,c}
=
V_{N,c}U_N(I-Q_N)
+
V_{N,c+1\bmod b_N}U_NQ_N.
}
\]

Therefore:

ARPL_REFINEMENT_TO_CUNTZ_BRANCHING = PASS_EXACT.

ARPL_ODOMETER_TO_CARRY_COCYCLE = PASS_EXACT.

ARPL_ODOMETER_IS_GENERIC_FIXED_BRANCH_RECURSION = NO_GO.

The correct finite operator class is CUNTZ_BLOCK_COCYCLE_UNITARY.

## 6. Exact hit-cylinder overlap bridge

For active prime channels, ARPL hit events are

\[
C_p.
\]

Their exact raw Gram is

\[
G_{pq}
=
m(C_p\cap C_q).
\]

After normalization,

\[
\boxed{
\widetilde G_{pq}
=
\frac{
m(C_p\cap C_q)
}{
\sqrt{m(C_p)m(C_q)}
}.
}
\]

For generalized-CRT compatible channels,

\[
\boxed{
\widetilde G_{pq}
=
\frac{\gcd(e_p,e_q)}
{\sqrt{e_pe_q}}.
}
\]

Incompatible channels give zero.

Therefore:

ARPL_HIT_CYLINDER_TO_OVERLAP_GRAM = PASS_EXACT_SOURCE_ADAPTER.

This source object is not the same as the refinement-child Cuntz family.

## 7. Exact adapter failure preserved

For

\[
h=6,
\qquad
P=\{5,7,11,13,19\},
\]

the arithmetic pulse rendering is

\[
\left(
\pi,
\frac{2\pi}{3},
\frac{4\pi}{5},
\frac{2\pi}{3},
\frac{10\pi}{9}
\right).
\]

The naive scalar orbital assignment

\[
R_p=e^{i\theta_p}
\]

fails the normalized overlap-Gram stabilizer with residual

\[
\boxed{
1.0236181222825256.
}
\]

Therefore:

ARPL_PULSE_ANGLE_EQUALS_SCALAR_OVERLAP_ORBITAL_PHASE = FAIL.

This FAIL is local to the adapter.

It does not invalidate the exact arithmetic phase coordinate or the exact
overlap Gram.

PhaseNav v0.8 preserves this distinction by allowing the ARPL source packet to
pass while setting

scalar_orbital_pulse_promotion = false.

## 8. Matrix-valued overlap theorem

The exact local overlap condition is

\[
\boxed{
R_p^*A_{pq}R_q=A_{pq}
}
\]

or equivalently

\[
\boxed{
A_{pq}R_q=R_pA_{pq}.
}
\]

Thus the cross-Gram is an intertwiner.

### Trivial common internal tensor

If

\[
A_{pq}=g_{pq}I_d,
\qquad
g_{pq}\neq0,
\]

then

\[
\boxed{
R_p=R_q.
}
\]

Hence merely increasing internal dimension does not restore independent
channel phases.

### Full-rank unitary frames

If

\[
A_{pq}=g_{pq}J_p^*J_q
\]

with square unitary frames, local coordinate matrices can differ, but the
external operators obey

\[
\boxed{
J_pR_pJ_p^*
=
J_qR_qJ_q^*.
}
\]

Therefore the difference is frame conjugacy, not independent external dynamics.

### Rank-deficient overlap

If \(A_{pq}\) is rank deficient, degrees of freedom in its kernel/complement may
remain unconstrained by that overlap edge.

The independent replay control

\[
A=\operatorname{diag}(0.7,0)
\]

allowed different hidden phases while retaining stabilizer residual

\[
1.1385499105160516\times10^{-16}.
\]

Therefore:

TRIVIAL_INTERNAL_EXTENSION_RESCUES_ARPL_SCALAR_ADAPTER = NO_GO.

FULL_RANK_FRAME_VARIATION_GIVES_INDEPENDENT_EXTERNAL_DYNAMICS = NO_GO.

RANK_DEFICIENT_OVERLAP_HIDDEN_FREEDOM = PASS_EXACT_REFERENCE.

Physical selection of such a rank-deficient source remains OPEN.

## 9. PhaseNav representation layers

The current 36D bridge stack now distinguishes:

- COMPRESSION_ONLY;
- FIXED_BRANCH_UNITARY_INTERTWINER;
- BRANCH_PERMUTATION_UNITARY;
- CUNTZ_BLOCK_COCYCLE_UNITARY;
- OVERLAP_GRAM_COVARIANT;
- UNITARY_DILATION;

plus depth semantics:

- FINITE_LEVEL_ONLY;
- INDUCTIVE_STEP_COVARIANT;
- INDUCTIVE_LIMIT_COVARIANT;
- SUMMABLE_DEFECT_INDUCTIVE_COVARIANCE.

ARPL-specific typed surfaces include:

- ARPL_ODOMETER_CARRY;
- ARPL_PROCYCLIC_ODOMETER_LIMIT;
- ARPL_HIT_OVERLAP_GRAM.

Matrix-overlap internal modes include:

- TRIVIAL_INTERNAL_TENSOR;
- FULL_RANK_FRAME_CONJUGACY;
- RANK_DEFICIENT_STABILIZER;
- GENERAL_MATRIX_GRAM_STABILIZER.

This is representation typing, not a claim that the complete arithmetic hull or
complete Hilbert state is 36-dimensional.

## 10. Immutable provenance firewall

PhaseNav v0.10 requires every ARPL-derived packet to carry:

- repository;
- branch;
- exact 40-hex commit SHA;
- source-file ledger;
- pin witness.

The known stale/broken source SHA

\[
705872f11aaf8b933ab3b713fb10443326fde62b
\]

is explicitly rejected.

The repaired source SHA is

\[
\boxed{
22171349917c97392db7d35605f15be1441fa5bb.
}
\]

A moving branch label is not treated as an immutable source identity.

## 11. Hosted validation status

No hosted GitHub status checks were present on the checked PhaseNav candidate
heads.

Therefore:

HOSTED_CI = NOT_PRESENT.

Reference/algebraic validation and hosted CI are kept separate.

## 12. Current strongest closed chain

The strongest current mathematical/representation chain is

\[
\boxed{
\text{ARPL exact phase clocks}
\to
\text{procyclic refinement}
\to
\text{Cuntz child decomposition}
\to
\text{odometer carry cocycle}
}
\]

in the refinement channel, and independently

\[
\boxed{
\text{ARPL hit cylinders}
\to
\text{exact arithmetic Gram}
\to
\text{normalized overlap Gram}
\to
\text{stabilizer/intertwiner theorem}.
}
\]

These channels are compatible but not identical.

## 13. Current no-go chain

The following shortcuts are now explicitly blocked:

\[
\text{generic IFS}
\not\Rightarrow
\text{global unitary dilation},
\]

\[
\text{global unitary}
\not\Rightarrow
\text{fixed-branch recursion},
\]

\[
\text{overlapping local unitaries}
\not\Rightarrow
\text{global quotient unitary},
\]

\[
\text{arithmetic pulse angle}
\not\Rightarrow
\text{scalar orbital phase},
\]

\[
\text{larger common internal dimension}
\not\Rightarrow
\text{independent local orbital freedom},
\]

\[
\text{full-rank frame change}
\not\Rightarrow
\text{independent external dynamics},
\]

\[
\text{36D transport vector}
\not\Rightarrow
\text{full infinite Hilbert state}.
\]

## 14. Nearest open mathematical witness

The closest non-artificial next gate is:

\[
\boxed{
\text{derive a source-owned nontrivial matrix-valued ARPL cross-Gram}
}
\]

or prove that the natural ARPL source cannot supply one.

Specifically, one needs a mathematically intrinsic branch feature family whose
cross-Gram is not merely

\[
\widetilde G_{pq}I_d
\]

and whose stabilizer supports a nontrivial channel-dependent orbital family.

Candidate source structures must come from existing ARPL data rather than an
added free matrix chosen after seeing the desired result.

Possible source classes to audit:
- multi-harmonic character fibres;
- local frequency-module subspaces;
- transfer-spectrum eigenspaces;
- arithmetic cylinder feature vectors.

No one of these is promoted by this audit.

## 15. Physical gates remain open

The following remain OPEN:

- physical interpretation of prime phases;
- source-owned physical orbital realization;
- physical matrix overlap source;
- physical branch/cell calibration;
- physical 36D state family;
- empirical validation.

## 16. GREMLIN verdict

FOUND:
- exact refinement branch theorem;
- exact odometer carry cocycle;
- exact ARPL overlap Gram;
- exact scalar adapter reverse-test FAIL;
- exact matrix-overlap stabilizer theorem;
- exact provenance repair and immutable source pin.

REPAIRED:
- stale/diverged On-Primes integration ancestry;
- missing Fraction import;
- stale PhaseNav source-pin semantics via v0.10 denylist/pinning contract.

NOT PROMOTED:
- hosted CI;
- physical prime-Moire law;
- physical hidden internal sector;
- physical 36D realization.

NEXT WITNESS:
source-owned nontrivial matrix-valued ARPL cross-Gram or a proof-level no-go
showing that the natural source remains scalar on every canonical fibre.

No main branch was modified by this audit.


## 17. Matrix witness closure update

The previous NEXT WITNESS has now been closed.

On-Primes branch:

integrate/arpl-clock-fibre-matrix-gram-v0.1-20260926

immutable source pin:

\[
\boxed{
8781f4a685257eced538daa7462ec4fc48093a6b
}
\]

supplies canonical local clock fibres

\[
\mathcal H_e
=
\ell^2(\mathbb Z/e\mathbb Z)
\]

and source-owned rectangular cross-Gram operators

\[
\boxed{
A_{ef}=J_e^*J_f.
}
\]

Their exact rank is

\[
\boxed{
\operatorname{rank}A_{ef}
=
\gcd(e,f).
}
\]

The local odometers satisfy

\[
\boxed{
A_{ef}U_f=U_eA_{ef}.
}
\]

The local Moire mismatch operators satisfy

\[
\boxed{
A_{ef}\Delta_f=\Delta_eA_{ef}.
}
\]

Thus:

SOURCE_OWNED_NONTRIVIAL_MATRIX_ARPL_CROSS_GRAM = FOUND_PASS_REFERENCE.

The previous scalar hit-cylinder Gram is a selected matrix element of this
larger clock-fibre Gram.

A full Fourier transform of the same scalar hit indicator remains only a
unitary basis change and does not create this extra matrix structure.

## 18. Finite-support network visibility update

For h=6 and the first five active channels with periods

\[
(2,3,5,6,9),
\]

the finite-support network-hidden dimensions are

\[
(0,0,4,2,6).
\]

The source refinement reverse control shows that after extending to the first
15 active channels through p=79, the hidden dimensions of those original five
channels become

\[
\boxed{
(0,0,0,0,0).
}
\]

Therefore finite-support hidden modes are exact but support-relative.

They are not promoted to a persistent hidden physical sector.

## 19. Updated nearest open gate

The nearest hard arithmetic gate is now

\[
\boxed{
\text{INFINITE_SUPPORT_VISIBILITY / PERSISTENCE}.
}
\]

For a local reduced frequency denominator d, determine whether another active
ARPL channel eventually has

\[
d\mid e_q=\operatorname{ord}_q(4).
\]

Finite searches or finite-support disappearance controls do not prove the
infinite statement.

The physical gates remain downstream and unchanged.

Updated NEXT WITNESS:

an infinite-support persistence/exposure theorem, or a rigorous reduction of
that question to an identified open arithmetic distribution problem.


## 20. Infinite-support visibility reduction

The finite-support hidden-mode question has now been reduced exactly.

For an odd prime q away from h,

\[
q\text{ is ARPL-active}
\iff
h\in\pm\langle2\rangle\pmod q.
\]

For a local mode with reduced denominator d, exposure by q is equivalent to

\[
d\mid\operatorname{ord}_q(4).
\]

Therefore complete-network persistence is equivalent to the absence of another
prime satisfying both conditions simultaneously.

This closes the representation reduction but not the infinite prime-existence
problem.

For h=6, finite controls show:

- q=31 has ord_31(4)=5 but is inactive, so order-divisibility alone is
  insufficient;
- p=13 e=6 hidden modes are exposed by q=37, e_37=18;
- p=19 e=9 hidden modes are exposed by q=37;
- p=11 e=5 hidden modes are exposed by q=61, e_61=30.

The first P5 hidden vector

\[
(0,0,4,2,6)
\]

therefore disappears on the original five channels by the P15 extension.

Literature boundary:

the bare condition

\[
h\in\langle2\rangle\pmod q
\]

belongs to the two-variable Artin/subgroup-membership problem. Conditional
positive-density results under GRH are known. The additional fixed divisibility

\[
d\mid\operatorname{ord}_q(4)
\]

is not promoted here as a consequence of those results.

Updated frontier:

ARPL_INFINITE_SUPPORT_EXPOSURE_THEOREM = OPEN_ARTIN_TYPE.

The exact reduction is closed; the distribution theorem is not.


## 21. Active-channel infinitude correction

Full-text literature audit strengthens the frontier.

Moree--Stevenhagen Theorem 1 records unconditionally, via Polya, that for
multiplicatively independent rational a,b there are infinitely many primes q
such that

\[
b\bmod q\in\langle a\bmod q\rangle.
\]

Applying a=2, b=h gives infinitely many unsigned ARPL-active channels whenever
2 and h are multiplicatively independent.

For signed dyadic integer h, the signed-subgroup active condition is elementary
for all relevant odd primes.

Therefore for nonzero integer h:

\[
\boxed{
\text{INFINITE_ARPL_ACTIVE_CHANNELS}
=
\text{CLOSED / LITERATURE-GROUNDED}.
}
\]

The positive-density statement remains a stronger GRH-conditional result in
the multiplicatively independent case.

The remaining arithmetic blocker is not active-channel infinitude but the
fixed-denominator set

\[
\mathcal E_{h,d}
=
\{
q:
h\in\pm\langle2\rangle,\ 
d\mid\operatorname{ord}_q(4)
\}.
\]

For d>1, this audit retains:

FIXED_DENOMINATOR_INFINITE_EXPOSURE = OPEN_ARTIN_TYPE.


## 21. Visibility-frontier sharpening: both marginals closed

The infinite-support frontier has been reduced one step further.

### Active-channel marginal

For multiplicatively independent \(2,h\), the two-variable Artin set

\[
\{
q:
h\bmod q\in\langle2\bmod q\rangle
\}
\]

is unconditionally infinite; the positive-density theorem is the
GRH-conditional strengthening.

The signed ARPL active set is therefore also infinite.

For \(h=\pm2^k\), activity is elementary for all relevant odd primes.

Hence:

INFINITE_ARPL_ACTIVE_CHANNELS = CLOSED.

### Prescribed order-divisibility marginal

For every fixed \(d\ge1\),

\[
N_4(d)
=
\{
q:
d\mid\operatorname{ord}_q(4)
\}
\]

has a positive natural density by the Wiertelak/Moree theorem.

Hence:

PRESCRIBED_ORD4_DIVISIBILITY = CLOSED_POSITIVE_DENSITY.

### Signed-dyadic consequence

If \(h=\pm2^k\), activity imposes no further restriction, so

\[
\mathcal E_{h,d}
\]

has positive natural density for every fixed d.

Thus:

SIGNED_DYADIC_FIXED_DENOMINATOR_EXPOSURE = CLOSED.

### Remaining generic gate

For multiplicatively independent h such as h=6, the only unresolved set is

\[
\boxed{
\mathcal E_{h,d}
=
\{
q:
h\in\pm\langle2\rangle\pmod q,
\quad
d\mid\operatorname{ord}_q(4)
\}.
}
\]

Both defining marginals are individually infinite/positive-density, but this
does not by itself prove their intersection is nonempty or infinite.

Therefore the current exact NEXT WITNESS is:

\[
\boxed{
\text{GENERIC JOINT SUBGROUP-MEMBERSHIP + ORD4-DIVISIBILITY THEOREM}.
}
\]

For h=6 this is the sole remaining arithmetic persistence gate before any
physical interpretation is considered.


## 22. GRH-conditional closure of generic infinite exposure

The generic joint exposure gate has now been closed conditionally on GRH by an
explicit source-prime replication construction.

Fix an active source prime p and any reduced local denominator

\[
d\mid e_p=\operatorname{ord}_p(4).
\]

Let

\[
I_4(p)
=
\frac{p-1}{\operatorname{ord}_p(4)},
\qquad
I_h(p)
=
\frac{p-1}{\operatorname{ord}_p(h^2)}.
\]

Activity gives

\[
I_4(p)\mid I_h(p).
\]

For every prime \(\ell\mid d\), freeze the exact value

\[
v_\ell(q-1)=v_\ell(p-1)
\]

by prescribing the Frobenius class of p in the finite cyclotomic extension

\[
\mathbb Q(\zeta_{M_{p,d}}),
\qquad
M_{p,d}
=
\prod_{\ell\mid d}
\ell^{v_\ell(p-1)+1}.
\]

Simultaneously freeze the exact multivariable index tuple

\[
(I_4(q),I_h(q))
=
(I_4(p),I_h(p)).
\]

The source p itself realizes this combined index/Frobenius condition, so the
class is nonempty.

Under the GRH assumptions of the Järviniemi--Perucca multivariable index-map
density theorem, a nonempty exact index/Frobenius class has positive natural
density.

Every prime q in that class remains ARPL-active and satisfies

\[
d\mid\operatorname{ord}_q(4).
\]

Hence the full exposure set has positive lower natural density:

\[
\boxed{
\underline{\delta}(\mathcal E_{h,d})>0
}
\]

under GRH.

Therefore every fixed local ARPL mode is exposed by infinitely many other
active channels under GRH.

Consequently:

\[
\boxed{
\mathcal N_p^\infty=\{0\}
}
\]

for every fixed finite local clock fibre under GRH.

This does not establish a physical observability statement.

Current status:

GENERIC_FIXED_DENOMINATOR_EXPOSURE = PASS_UNDER_GRH  
INFINITE_SUPPORT_HIDDEN_SUBSPACE = ZERO_UNDER_GRH  
UNCONDITIONAL_GENERIC_EXPOSURE = OPEN

Pinned frontier receipt:

AdrianLipa90/On-Primes  
branch research/arpl-infinite-clock-visibility-frontier-v0.1-20260926  
commit deac8af3ae12ac80f0cfab21b440b6e727c0b342


## 23. Clean theorem extraction and PhaseNav v0.12 promotion

The GRH-conditional exposure result has been extracted from the evolving
frontier note into a clean theorem artifact:

AdrianLipa90/On-Primes  
proofs/ARPL_GRH_SOURCE_PRIME_REPLICATION_THEOREM_V0_1.md

validation receipt snapshot:

\[
\boxed{
deac8af3ae12ac80f0cfab21b440b6e727c0b342.
}
\]

PhaseNav now carries a separate conditional visibility layer:

AdrianLipa90/noema-phasenav-core  
formalism/fractal-moire-hilbert-36d-bridge-v0.12-20260926

current validation receipt head:

\[
\boxed{
c9bc3b07016e2d41258c0f68294400cf54c13755.
}
\]

The layer preserves:
- exact finite hidden dimensions;
- conditional zero infinite-support hidden dimensions under GRH;
- unconditional generic status OPEN;
- physical observability NOT PROMOTED.

No main/master branch was changed.


## 24. Unconditional generic frontier reduced to strict subgroup-depth preservation

The generic unconditional gate is now expressed exactly as a finite-group
condition.

For

\[
d=\prod_{\ell^a\parallel d}\ell^a,
\]

the condition

\[
d\mid\operatorname{ord}_q(4)
\]

is equivalent to strictness of the first a inclusions

\[
\langle4\rangle
\supsetneq
\langle4^\ell\rangle
\supsetneq\cdots
\supsetneq
\langle4^{\ell^a}\rangle
\]

for every prime-power factor of d.

Therefore

\[
q\in\mathcal E_{h,d}
\]

iff the prime simultaneously satisfies:

1. subgroup inclusion
   \[
   \langle h^2\rangle\subseteq\langle4\rangle;
   \]
2. every required strict finite \(\ell\)-power tower.

Thus the remaining unconditional theorem is an enhanced
Schinzel--Wojcik problem with prescribed finite order-filtration depth.

Executable controls verified exact equivalence with d|order for all

\[
1\le\operatorname{order}<200,
\qquad
1\le d<100.
\]

## 25. Carella prescribed-order preprint excluded at proof level

The previously surfaced preprint

N. A. Carella,
arXiv:2103.04822 v1,

is not merely unverified in this audit.

Its printed Lemma 2.2 is false.

For

\[
p=7,\quad d=2,\quad\tau=3,\quad u=2,
\]

the required exact order holds:

\[
\operatorname{ord}_7(2)=3=(p-1)/d.
\]

But the printed shortened additive-character expression evaluates to

\[
\boxed{
0.6428571428571428
-
0.03439818705768061\,i
}
\]

instead of 1.

The failure comes from replacing full additive-character orthogonality modulo p
by a truncated k-range of length approximately \((p-1)/d\).

Section 10 then invokes Lemma 2.2 to set the one-sided error terms to zero, and
Theorem 1.1 uses those cancellations.

Therefore:

CARELLA_2103_04822_V1_LEMMA_2_2 = FAIL_COUNTEREXAMPLE.

CARELLA_2103_04822_V1 = EXCLUDED_FROM_PROOF_EVIDENCE.

This says nothing about a hypothetical corrected later proof.

## 26. Current frontier after proof-level audit

PASS UNDER GRH:
- positive lower density of every fixed-denominator exposure set;
- infinitely many exposures of every fixed local mode;
- zero complete-network hidden subspace for every fixed local fibre.

PASS EXACT:
- unconditional target reduction to subgroup inclusion plus strict power-tower
  depth.

OPEN:
- unconditional infinitude of the enhanced subgroup-depth intersection;
- unconditional quantitative lower bound;
- effective least-exposure bounds.

No additional PhaseNav or Hilbert formalism is missing.

Current unconditional frontier snapshot:

AdrianLipa90/On-Primes  
research/arpl-infinite-clock-visibility-frontier-v0.1-20260926  
head c5c3cc1e579009ac4232a3aede29f403bc4b9004


## 23. Unconditional-frontier hardening

The GRH-conditional generic exposure theorem remains PASS.

The unconditional audit now has two additional exact no-go controls.

### Recurrence exponent restriction

For

\[
h=6,\ d=5,\ n=10,\ q=5,
\]

\[
q\mid4^n-h^2
\quad\text{and}\quad
d\mid n,
\]

but

\[
\operatorname{ord}_5(4)=2.
\]

Therefore selecting recurrence indices divisible by d does not force

\[
d\mid\operatorname{ord}_q(4).
\]

### Active arithmetic progression

For

\[
h=6,\ d=5,\ q=431,
\]

q is active and

\[
q\equiv1\pmod5,
\]

but

\[
\operatorname{ord}_{431}(4)=43.
\]

Thus an arithmetic-progression restriction alone also fails the order gate.

### 2025 unconditional-index scope

The Sgobba 2025 unconditional framework allows substantial one-subgroup index
conditions and finite Frobenius restrictions, but it does not turn a generic
exact multivariable index tuple into an unconditional theorem.

Hence it cannot directly replace the GRH exact-index replication step.

### Sharpened next witness

The smallest sufficient missing input is now:

\[
\boxed{
\text{UNCONDITIONAL CHEBOTAREV-RESTRICTED TWO-VARIABLE SUPPORT}.
}
\]

Concretely, for compatible finite Galois \(F/\mathbb Q\) and Frobenius
condition C, prove infinitude or an effective lower bound for

\[
\{
q:
b\bmod q\in\langle a\bmod q\rangle,
\operatorname{Frob}_q(F/\mathbb Q)\in C
\}.
\]

For ARPL, take

\[
a=4,\qquad b=h^2
\]

and choose C to enforce the finite Kummer/cyclotomic conditions implying

\[
d\mid\operatorname{ord}_q(4).
\]

This is narrower and more precise than asking for an unconditional generic
Artin exact-index theorem.

Current state:

GENERIC_FIXED_DENOMINATOR_EXPOSURE_UNDER_GRH = PASS  
UNCONDITIONAL_GENERIC_EXPOSURE = OPEN  
RECURRENCE_MULTIPLE_EXPONENT_SHORTCUT = REFUTED  
ACTIVE_PLUS_CONGRUENCE_SHORTCUT = REFUTED


## 27. Cyclotomic two-target reduction of the unconditional frontier

The unconditional generic exposure problem now has a source-calibrated
two-target form.

For every active source certificate

\[
(p,h,d),
\qquad
d\mid\operatorname{ord}_p(4),
\]

work in

\[
K_d=\mathbb Q(\zeta_d).
\]

One can choose a source prime ideal \(P\mid p\) and positive shifts
\(s_h,s_\zeta\) such that

\[
\beta_h=4^{s_h}h^2,
\qquad
\beta_\zeta=4^{s_\zeta}\zeta_d
\]

satisfy

\[
\boxed{
\beta_h\equiv\beta_\zeta\equiv4\pmod P.
}
\]

For any later prime ideal Q, simultaneous membership

\[
\beta_h\bmod Q\in\langle4\bmod Q\rangle,
\]

\[
\beta_\zeta\bmod Q\in\langle4\bmod Q\rangle
\]

implies for the rational prime q below Q:

\[
\operatorname{ord}_q(h^2)\mid\operatorname{ord}_q(4),
\]

\[
d\mid\operatorname{ord}_q(4).
\]

Therefore q lies in the exact ARPL exposure set.

### Pairwise marginals

Pollack's 2025 number-field theorem applies separately to the calibrated pairs

\[
(4,\beta_h)
\]

and

\[
(4,\beta_\zeta),
\]

because positive calibration shifts make both targets non-torsion and their
absolute field norms differ from 1.

Hence each individual support set is unconditionally infinite.

What remains open is only their common intersection.

### One-product no-go

The two targets cannot generically be compressed to one multiplied target.

In

\[
C_{20},
\qquad
H=\langle5\rangle,
\]

take

\[
x=16,
\qquad
z=4.
\]

Then

\[
x,z\notin H,
\]

but

\[
x+z=0\in H
\]

and even

\[
\langle5+x+z\rangle=H.
\]

Thus one combined subgroup relation cannot recover the two required
memberships.

### Sharpened missing theorem

The current unconditional blocker is now equivalently:

\[
\boxed{
\text{SIMULTANEOUS CYCLOTOMIC TWO-TARGET SUPPORT}.
}
\]

A stronger sufficient theorem is a finite-set Schinzel--Wojcik theorem for the
source-calibrated triple

\[
(4,\beta_h,\beta_\zeta).
\]

This is a more constructive formulation of the previous
Chebotarev-restricted two-variable support frontier.

Current source:

AdrianLipa90/On-Primes  
branch research/arpl-cyclotomic-two-target-frontier-v0.1-20260927  
receipt commit

\[
\boxed{
2cf143124a9b5e34e27160b525a5ca405ab79e6d.
}
\]

No main/master branch was modified.


## 28. Pair-theorem intersection barrier

The current Pollack 2025 number-field theorem closes each source-calibrated
target separately:

\[
\#S(4;\beta_h)=\infty,
\]

\[
\#S(4;\beta_\zeta)=\infty.
\]

It does not close

\[
\#\left(
S(4;\beta_h)\cap S(4;\beta_\zeta)
\right)=\infty.
\]

This is not only a set-theoretic warning.

Pollack's proof is pair-specific: its fundamental-identity mechanism starts
from failure/finite support hypotheses for one fixed pair
\((\alpha,\beta)\). Finiteness of the simultaneous intersection does not imply
finiteness of either pair-support marginal, so the Proposition-2.1 entry
hypothesis cannot be inferred for either calibrated target.

Using the same auxiliary exponent prime in both pair arguments does not
synchronize the final output prime ideals. Common divisors of

\[
\alpha^q-\beta_1
\]

and

\[
\alpha^q-\beta_2
\]

for one shared exponent q divide the fixed difference

\[
\beta_1-\beta_2
\]

and therefore cannot generate the required generic infinite simultaneous
support.

Pollack's 2025 paper itself records finite-list analogues as known under GRH or
Schinzel Hypothesis H, while its unconditional theorem remains pairwise.

Therefore:

POLLACK_PAIR_THEOREM_PLUS_PAIR_THEOREM = NO_GO_AS_DIRECT_INTERSECTION_PROOF.

SHARED_FILTER_EXPONENT_SYNCHRONIZATION = NO_GO.

The current unconditional frontier remains:

\[
\boxed{
\text{SIMULTANEOUS CYCLOTOMIC TWO-TARGET SUPPORT}.
}
\]

This is now the minimal missing synchronization input found in the reviewed
proof mechanisms.

Pinned barrier receipt:

AdrianLipa90/On-Primes  
research/arpl-cyclotomic-two-target-frontier-v0.1-20260927  
commit

\[
\boxed{
688c3c28e0fb7463d9cca690b1efc638f57559a6.
}
\]


## 29. Torus order-divisibility packaging of the simultaneous frontier

The simultaneous cyclotomic two-target condition has an exact single-point
formulation on the split torus

\[
G=\mathbb G_m^2.
\]

Define

\[
P=(4,4),
\qquad
T=(\beta_h,\beta_\zeta).
\]

For every good prime ideal Q,

\[
\operatorname{ord}_Q(P)
=
\operatorname{ord}_Q(4),
\]

while

\[
\operatorname{ord}_Q(T)
=
\operatorname{lcm}
\left(
\operatorname{ord}_Q(\beta_h),
\operatorname{ord}_Q(\beta_\zeta)
\right).
\]

Since the residue-field multiplicative group is cyclic,

\[
\boxed{
\beta_h,\beta_\zeta\in\langle4\rangle
\iff
\operatorname{ord}_Q(T)
\mid
\operatorname{ord}_Q(P).
}
\]

Thus the existing frontier

SIMULTANEOUS_CYCLOTOMIC_TWO_TARGET_SUPPORT

is exactly equivalent to

\[
\boxed{
\text{INFINITE TORUS ORDER-DIVISIBILITY SUPPORT}.
}
\]

The same condition is also

\[
T\bmod Q
\in
\langle(4,1),(1,4)\rangle.
\]

This preserves the independent exponents of the two target coordinates and
does not use the already-refuted one-product encoder.

### Concrete controls

For the h=6, p=11, d=5 source calibration

\[
\beta_h=576,
\qquad
\beta_\zeta=4^5\zeta_5,
\]

q=31 with \(\zeta_5\mapsto2\) gives

\[
\operatorname{ord}(P)=5,
\qquad
\operatorname{ord}(T)=15,
\]

so the torus divisibility fails.

q=61 with \(\zeta_5\mapsto9\) gives

\[
\operatorname{ord}(P)
=
\operatorname{ord}(T)
=
30.
\]

### Finite-l-adic barrier

At q=31,

\[
v_5(\operatorname{ord}T)
=
v_5(\operatorname{ord}P)
=
1
\]

while globally

\[
15\nmid5.
\]

Therefore controlling any fixed selected finite family of l-adic order
valuations does not by itself establish complete point-order divisibility.

Reviewed reduction-of-points theorems for tori provide strong finite-l-adic
density statements, while classical support-problem theorems are converse
almost-all-primes statements.

Neither reviewed class is promoted here as the missing existential theorem.

Updated equivalent unconditional frontier:

\[
\boxed{
\#\{Q:\operatorname{ord}_Q(T)\mid\operatorname{ord}_Q(P)\}=\infty.
}
\]

This is an exact higher-rank torus support existence problem.

Current source receipt:

AdrianLipa90/On-Primes  
research/arpl-cyclotomic-two-target-frontier-v0.1-20260927

receipt head:

\[
\boxed{
698087095df85536b448bf6518da1f8f63d4c8c8.
}
\]


## 30. Relative-index correlation barrier

The simultaneous two-target / torus frontier now has an exact nested-subgroup
formulation.

Work in

\[
K_d=\mathbb Q(\zeta_d)
\]

with

\[
W_0=\langle4\rangle
\subset
\Gamma=\langle4,h^2,\zeta_d\rangle.
\]

For every good prime ideal Q define

\[
I_0(Q)
=
[k_Q^\times:\overline{W_0}],
\]

\[
I_\Gamma(Q)
=
[k_Q^\times:\overline\Gamma].
\]

Because the reduction subgroups are nested,

\[
I_\Gamma(Q)\mid I_0(Q).
\]

Define the relative index

\[
\boxed{
J(Q)
=
[\overline\Gamma:\overline{W_0}]
=
\frac{I_0(Q)}{I_\Gamma(Q)}.
}
\]

Then the ARPL exposure event is exactly

\[
\boxed{
Q\text{ exposes }(h,d)
\iff
I_0(Q)=I_\Gamma(Q)
\iff
J(Q)=1.
}
\]

For split rational controls q,

\[
I_0(q)
=
\frac{q-1}{\operatorname{ord}_q(4)},
\]

\[
I_\Gamma(q)
=
\frac{q-1}{
\operatorname{lcm}
(
\operatorname{ord}_q(4),
\operatorname{ord}_q(h^2),
d
)
}.
\]

### Marginal-index no-go controls

For h=6,d=5:

q=31 has

\[
\operatorname{ord}_{31}(4)=5,
\qquad
\operatorname{ord}_{31}(36)=3,
\]

and therefore

\[
(I_0,I_\Gamma,J)=(6,2,3).
\]

q=61 has

\[
\operatorname{ord}_{61}(4)
=
\operatorname{ord}_{61}(36)
=
30,
\]

hence

\[
(I_0,I_\Gamma,J)=(2,2,1).
\]

Thus

\[
\boxed{
I_\Gamma(31)=I_\Gamma(61)=2
}
\]

while the exposure verdict is opposite.

Likewise q=31 and q=1021 satisfy

\[
\boxed{
I_0(31)=I_0(1021)=6
}
\]

while q=31 fails and q=1021 passes.

Therefore neither one-subgroup index marginal determines the ARPL joint event.

### Scope of current unconditional one-subgroup index results

The 2025 unconditional Artin-index framework of Sgobba studies the reduction
index of one fixed finitely generated subgroup, optionally with finite
Frobenius restrictions.

That machinery is relevant to either

\[
I_0
\]

or

\[
I_\Gamma
\]

separately.

The exact ARPL gate is the correlation equation

\[
\boxed{
I_0=I_\Gamma.
}
\]

The arithmetic controls above prove that no theorem about either one marginal
alone can be promoted to the ARPL exposure theorem without an additional
two-subgroup correlation input.

Hence the minimal unconditional frontier may now be stated equivalently as:

\[
\boxed{
\#\{Q:J(Q)=1\}=\infty.
}
\]

Equivalent forms remain:

- simultaneous cyclotomic two-target support;
- infinite torus order-divisibility support;
- equality of the two nested-subgroup reduction indices.

Pinned source receipt:

AdrianLipa90/On-Primes  
branch research/arpl-cyclotomic-two-target-frontier-v0.1-20260927

\[
\boxed{
159058708e0b75afd3cbad8c855a0dcd71d8ed47.
}
\]

Current unconditional missing input:

\[
\boxed{
\text{TWO-SUBGROUP RELATIVE-INDEX CORRELATION THEOREM}.
}
\]

The GRH multivariable exact-index closure remains valid and unchanged.


## 30. Two-exponent synchronization barrier

For simultaneous support choose logs r_Q,s_Q modulo n_Q=ord_Q(4). For fixed integers u,v,c, the congruence

\[
ur_Q+vs_Q\equiv c\pmod{n_Q}
\]

implies \(\beta_h^u\beta_\zeta^v\equiv4^c\pmod Q\). If the corresponding global identity is false, only finitely many good prime ideals can satisfy that fixed affine synchronization.

For h=6,d=5 the complete global relation lattice is

\[
\boxed{\mathcal L=\{(0,5k,25k):k\in\mathbb Z\}}.
\]

The same-exponent line is therefore nonpersistent. Its explicit norm certificate is

\[
N_{\mathbb Q(\zeta_5)/\mathbb Q}(576-1024\zeta_5)=2^{24}\cdot11\cdot71\cdot181.
\]

The calibrated source q=11 has \((r,s)=(1,1)\pmod5\), while the later simultaneous output q=61 has \((r,s)=(9,11)\pmod{30}\). Infinite simultaneous output must therefore use genuine rank-two exponent motion modulo the true global relation lattice.

## 31. Pollack one-pair architecture barrier

Pollack's generous-prime proof factors \((\alpha^q-\beta)\mathcal O_K\) for one prime exponent q and uses pairwise non-goodness to deduce \(q\mid N(P)-1\) for off-set prime divisors. That exact implication fails for the simultaneous-good complement: a prime may be pair-good for the h-target and simultaneous-bad because the cyclotomic target fails.

The direct same-q finite-list lift is also impossible because every common divisor of \(\alpha^q-\beta_h\) and \(\alpha^q-\beta_\zeta\) divides the fixed difference \(\beta_\zeta-\beta_h\).

The exact remaining rank-two ideal problem is

\[
\boxed{\#\bigcup_{r,s\in\mathbb Z}\operatorname{Supp}(\alpha^r-\beta_h,\alpha^s-\beta_\zeta)=\infty.}
\]

This is equivalent to the current torus order-divisibility / relative-index-one frontier. Existing gcd/S-unit results found in the literature give upper bounds on common gcd outside exceptional algebraic subgroups; they do not supply this infinitude theorem.

Source receipts: 1e76c4739056537ed0ba69d9d957439678544f5e and 2d0082667076db14feb12f0cb815e596bced7dab.

Updated unconditional NEXT WITNESS: RANK_TWO_GENEROUS_SUPPORT_PROPAGATION, or an exactly equivalent unconditional higher-rank torus support theorem.


## 32. Cyclotomic-target finite-state collapse

The generic rank-two formulation is exact but not minimal for the ARPL source because the second target has the special form

\[
\beta_\zeta=4^d\zeta_d.
\]

If \(e=\operatorname{ord}_Q(4)\) and \(d\mid e\), the unique order-d subgroup of \(\langle4\rangle\) is generated by \(4^{e/d}\). Hence every primitive d-th root in the residue field has

\[
\zeta_d=4^{j e/d},\qquad j\in(\mathbb Z/d\mathbb Z)^\times,
\]

and therefore

\[
\boxed{s_Q=d+j e/d\pmod e.}
\]

Thus the cyclotomic output log is finite-state once the order e is known. Exact membership collapses to

\[
\boxed{\beta_\zeta\in\langle4\rangle\iff d\mid\operatorname{ord}_Q(4).}
\]

For q=61,d=5: \(e=30\), \(\zeta_5=9=4^6\), and \(s=11\), matching the independent output-log control.

Therefore the preferred minimal unconditional frontier is no longer a fully generic rank-two support theorem. It is

\[
\boxed{\#\{Q:A_Q=1,\ D_Q=1\}=\infty,}
\]

where \(A_Q=1\) is the two-variable activity/support event and \(D_Q=1\) is the fixed finite-state torsion/order-depth gate.

The rank-two torus/common-support formulations remain equivalent and useful as structural cross-checks, but they are analytically broader than necessary for this cyclotomic source.

Source receipts:

- ARPL_TORSION_GATE_CORRELATION_FRONTIER_V0_1: ecdc20dfaa06def5317bae0a3cf9db0c03cc4fd1
- ARPL_CYCLOTOMIC_LOG_PARAMETRIZATION_V0_1: 40b6ecaaf824f3dfc8711c0620dfb4916011a1b8

Updated minimal NEXT WITNESS:

\[
\boxed{\text{UNCONDITIONAL TORSION-GATE CORRELATION}}
\]

equivalently, two-variable subgroup support restricted to the fixed order-depth condition \(d\mid\operatorname{ord}_Q(4)\).


## 33. Cofinite-support no-go for nondyadic h

The classical torus support problem gives a new unconditional boundary on the
current existential frontier.

For the source-calibrated torus points

\[
P=(4,4),
\qquad
T=(4^{s_h}h^2,\ 4^{s_\zeta}\zeta_d),
\]

Perucca's support theorem says:

if

\[
\operatorname{ord}_Q(T)
\mid
\operatorname{ord}_Q(P)
\]

for all but finitely many good prime ideals Q, then there exist a torus
endomorphism

\[
\phi\in\operatorname{End}(\mathbb G_m^2)
\cong M_2(\mathbb Z)
\]

and a nonzero integer c such that

\[
\phi(P)=[c]T.
\]

For

\[
P=(4,4),
\]

every torus endomorphism gives coordinates that are integral powers of 4.

Therefore the first coordinate of the global relation would force

\[
(4^{s_h}h^2)^c=4^m.
\]

For nonzero integer h this is possible only when

\[
\boxed{
h=\pm2^k.
}
\]

Hence for every nondyadic integer h,

\[
\boxed{
\operatorname{ord}_Q(T)\nmid\operatorname{ord}_Q(P)
}
\]

for infinitely many good prime ideals Q.

In particular,

\[
\boxed{
h=6
\Longrightarrow
\text{infinitely many joint-exposure failures unconditionally}.
}
\]

This is compatible with the existing GRH positive-density success theorem.

The signed-dyadic boundary is exact: if

\[
h=\pm2^k,
\]

then taking multiplier c=d kills the cyclotomic torsion and one can construct
an endomorphism satisfying the necessary global relation.

This does NOT prove cofinite support in the dyadic case; it proves only that
the Perucca obstruction disappears.

### Consequence for the frontier

For generic nondyadic h the desired successful set, if proved infinite
unconditionally, is necessarily non-cofinite.

Therefore the current missing theorem cannot be replaced by a hidden
almost-all-primes support theorem.

The frontier remains:

\[
\boxed{
\#\{Q:A_Q=1,\ D_Q=1\}=\infty,
}
\]

but now with the independent unconditional fact

\[
\boxed{
\#\{Q:(A_Q,D_Q)\ne(1,1)\}=\infty
}
\]

for every nondyadic integer h.

Source receipt:

AdrianLipa90/On-Primes  
branch research/arpl-torus-cofinite-no-go-v0.1-20260928-r2

\[
\boxed{
a40ea5e58e727c743ca69ecf5c879aabdb6d8550.
}
\]

Reference:

A. Perucca,
"Two variants of the support problem for products of abelian varieties and
tori",
J. Number Theory 129 (2009), 1883--1892,
DOI 10.1016/j.jnt.2009.01.005.


## 34. Pollack torsion-depth filtered-set barrier

The minimal ARPL gate cannot be obtained by replacing Pollack's one-pair good
set with a torsion-filtered good set inside the published norm proof.

For a pair \((\alpha,\beta)\), Pollack's argument uses the implication

\[
P\notin S,\quad
P\mid(\alpha^q-\beta)
\Longrightarrow
q\mid N(P)-1,
\]

where

\[
S=
\{P:\operatorname{ord}_P(\alpha)=\operatorname{ord}_P(\beta)\}.
\]

The reason is exact: if \(q\nmid N(P)-1\), the q-th power map is an
automorphism of the finite residue multiplicative group, and
\(\alpha^q=\beta\) forces equal order.

For ARPL one would need

\[
S_d
=
\{
P:
\operatorname{ord}_P(\alpha)=\operatorname{ord}_P(\beta),
\quad
d\mid\operatorname{ord}_P(\alpha)
\}.
\]

The same automorphism step proves only pair-goodness, not the order-depth
predicate.

### Exact h=6,d=5 countercontrol

Take

\[
\alpha=4,\qquad
\beta=576,\qquad
P=13,\qquad
q=7.
\]

Then

\[
\operatorname{ord}_{13}(4)
=
\operatorname{ord}_{13}(576)
=
6,
\]

so P is pair-good.

But

\[
5\nmid6,
\]

so

\[
P\notin S_5.
\]

Also

\[
4^7\equiv576\pmod{13},
\]

hence

\[
P\mid(4^7-576).
\]

Yet

\[
7\nmid12=N(P)-1.
\]

Therefore

\[
\boxed{
P\notin S_5,\quad
P\mid(4^7-576)
\not\Rightarrow
7\mid N(P)-1.
}
\]

The critical off-good-set norm simplification is lost.

Thus:

DIRECT_POLLACK_S_TO_S_D_FILTER = REFUTED.

A congruence condition on the auxiliary exponent q is not a typed condition on
the output-prime order.

The missing input remains a genuine correlation theorem:

\[
\boxed{
\#\{Q:A_Q=1,\ D_Q=1\}=\infty.
}
\]

Reviewed unconditional two-variable Artin lower-bound results do not add the
prescribed order-depth filter on the same output primes.

Current source receipt:

AdrianLipa90/On-Primes  
branch research/arpl-cyclotomic-frontier-v3-20260928

\[
\boxed{
4591a6cd650ca00b1350696624835fd94969f8b7.
}
\]

Primary proof interface:

P. Pollack,
"Two variants of a theorem of Schinzel and Wójcik on multiplicative orders",
Acta Arith. 218 (2025), 337--345.


## 35. Relational-zero operator closure

The current arithmetic exposure gate now has an exact Hilbert-operator form.

For one residue fibre

\[
G_Q=k_Q^\times,
\qquad
\mathcal H_Q=\ell^2(G_Q),
\]

and subgroup averaging projectors

\[
\Pi_H
=
\frac1{|H|}
\sum_{h\in H}\lambda_h,
\]

the calibrated subgroup chain

\[
\Gamma_0
\le
\Gamma_h
\le
\Gamma_{h\zeta}
\]

produces

\[
\Delta_h=\Pi_0-\Pi_h,
\]

\[
\Delta_\zeta=\Pi_h-\Pi_{h\zeta},
\]

\[
\Delta=\Pi_0-\Pi_{h\zeta}.
\]

Exact identities:

\[
\boxed{
\Delta=\Delta_h+\Delta_\zeta
}
\]

and

\[
\boxed{
\Delta_h\Delta_\zeta=0.
}
\]

Each defect is an orthogonal projection with spectrum contained in

\[
\{0,1\}.
\]

The complete ARPL exposure condition is exactly

\[
\boxed{
\Delta_Q=0.
}
\]

Thus the former Boolean correlation gate

\[
A_Q=1,\quad D_Q=1
\]

is now an orthogonal positive-operator zero condition.

The defect ranks are

\[
r_h=I_0-I_h,
\]

\[
r_\zeta=I_h-I_{h\zeta},
\]

\[
r=r_h+r_\zeta.
\]

For the h=6,p=11,d=5 controls:

q=31 gives

\[
(r_h,r_\zeta,r)=(4,0,4),
\]

so failure is purely activity.

q=61 gives

\[
(r_h,r_\zeta,r)=(0,0,0),
\]

an exact relational zero.

Pinned sources:

AdrianLipa90/On-Primes  
research/arpl-relational-zero-exposure-v0.1-20260928  
receipt 605119b2b2e50ff6eb4cab550382b48630f14c67

AdrianLipa90/Orbital-System-base  
formalism/fractal-orbital-moire-hilbert-v0.10-20260928  
receipt ae9c11d4f0b835fe298c4ff31536d554bf978952

AdrianLipa90/noema-phasenav-core  
formalism/fractal-moire-hilbert-36d-bridge-v0.13-20260928  
receipt 25c080d8af9ada56771ee441ee97429578f45363

The unconditional prime-distribution problem is now equivalently:

\[
\boxed{
\dim\ker M_\mu=\infty,
\qquad
\mu(Q)=\operatorname{rank}\Delta_Q.
}
\]

This is a spectral-zero multiplicity formulation, not yet an unconditional
infinitude proof.

## 36. Relational quantum-information invariant and kappa

Normalize the subgroup projectors:

\[
\rho_H
=
\Pi_H/\operatorname{Tr}\Pi_H.
\]

For

\[
H\le K,
\]

the exact Umegaki relative entropy is

\[
\boxed{
D(\rho_K\|\rho_H)
=
\ln[K:H].
}
\]

Hence relational information is additive along subgroup chains.

The invariant-subspace survival ratio is

\[
s(H\to K)=1/[K:H],
\]

so

\[
D=-\ln s.
\]

The normalized defect

\[
\varepsilon=1-s
\]

obeys the exact cascade law

\[
\boxed{
\varepsilon_{02}
=
\varepsilon_{01}
+
\varepsilon_{12}
-
\varepsilon_{01}\varepsilon_{12}.
}
\]

Using the project's pre-existing canonical phase-information normalization,

\[
\mathcal I_{24\pi}
=
\frac{D}{24\pi},
\]

a binary relational enlargement gives

\[
\boxed{
[K:H]=2
\Longrightarrow
\mathcal I_{24\pi}
=
\frac{\ln2}{24\pi}
=
\kappa.
}
\]

The algebra derives the logarithmic relative-entropy increment exactly.
The factor \(24\pi\) remains the pre-existing canonical normalization and is
not newly derived here.

Pinned sources:

AdrianLipa90/Orbital-System-base  
formalism/fractal-orbital-moire-hilbert-v0.11-20260928  
receipt c96531e0816dba01f3ade8a849f67494d064727a

AdrianLipa90/noema-phasenav-core  
formalism/fractal-moire-hilbert-36d-bridge-v0.14-20260928  
receipt 8bbe5f7143114f51157a5c3b0c79cfac10bc88ea

Updated GREMLIN operator surface:

- RELATIONAL_AVERAGING_PROJECTOR
- RELATIONAL_ACTIVITY_DEFECT_PROJECTOR
- RELATIONAL_DEPTH_DEFECT_PROJECTOR
- RELATIONAL_ZERO_PROJECTOR
- PRIME_FIBRE_DEFECT_MULTIPLICATION
- RELATIONAL_PROJECTOR_STATE
- RELATIONAL_UMEGAKI_INFORMATION
- RELATIONAL_MODULAR_GAP
- RELATIONAL_INFORMATION_24PI
- BINARY_RELATIONAL_KAPPA

Physical quantum-observable and thermodynamic interpretations remain separate
binding gates.
