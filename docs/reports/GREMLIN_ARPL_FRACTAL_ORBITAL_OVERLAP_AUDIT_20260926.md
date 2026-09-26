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
