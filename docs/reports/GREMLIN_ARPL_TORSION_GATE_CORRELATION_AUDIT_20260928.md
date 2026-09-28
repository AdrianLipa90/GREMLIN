# GREMLIN ARPL Torsion-Gate Correlation Audit — 2026-09-28

Status: EXACT_SHARPENING / TWO_NEW_NO_GO_GATES / RESTRICTED_SUPPORT_FRONTIER

## 1. Current source-of-truth frontier

The current ARPL unconditional exposure event is

\[
\mathcal E_{h,d}
=
\{q:A_q=1,\ D_q=1\},
\]

where

\[
A_q
=
\frac{\operatorname{ord}_q(h^2)}
{\gcd(\operatorname{ord}_q(h^2),\operatorname{ord}_q(4))}
\]

and

\[
D_q
=
\frac d{\gcd(d,\operatorname{ord}_q(4))}.
\]

Both marginals are closed unconditionally.

Their correlation is not.

## 2. Chain-index compression no-go

Define

\[
\langle4^d\rangle
\subseteq
\langle4\rangle
\subseteq
\langle4,h^2\rangle.
\]

The adjacent indices are

\[
B_q
=
[\langle4\rangle:\langle4^d\rangle]
=
\gcd(d,\operatorname{ord}_q(4)),
\]

and

\[
A_q
=
[\langle4,h^2\rangle:\langle4\rangle].
\]

The total index is

\[
K_q
=
[\langle4,h^2\rangle:\langle4^d\rangle]
=
A_qB_q.
\]

Exposure requires

\[
(A_q,B_q)=(1,d)
\]

and hence

\[
K_q=d.
\]

But for

\[
(h,d,q)=(6,5,241),
\]

\[
\operatorname{ord}_{241}(4)=12,
\qquad
\operatorname{ord}_{241}(36)=10,
\]

so

\[
\boxed{
(A,B,K)=(5,1,5).
}
\]

Therefore

\[
K=d
\]

is an exact false positive.

Verdict:

ONE_TOTAL_INDEX_COMPRESSION = NO_GO.

A one-subgroup reduction-index theorem applied only to K cannot close the
frontier.

Source receipt:

AdrianLipa90/On-Primes  
research/arpl-cyclotomic-two-target-frontier-v0.1-20260927  
ARPL_CHAIN_INDEX_COMPENSATION_NO_GO_V0_1_VALIDATION_20260928.md.

## 3. Source-calibrated finite depth cylinder

Let p be a source exposure prime.

For every

\[
\ell^{a_\ell}\Vert d,
\]

define

\[
s_\ell=v_\ell(p-1),
\]

\[
i_\ell
=
v_\ell
\left(
\frac{p-1}{\operatorname{ord}_p(4)}
\right).
\]

Then

\[
s_\ell-i_\ell\ge a_\ell.
\]

Define the finite Galois extension

\[
L_{p,d}
=
\prod_{\ell\mid d}
\mathbb Q
\left(
\zeta_{\ell^{s_\ell+1}},
4^{1/\ell^{s_\ell}}
\right).
\]

The source Frobenius conjugacy class in this extension freezes:

- the exact valuation \(v_\ell(q-1)=s_\ell\);
- the exact local power-residuacity profile of 4;
- hence the exact valuation
  \[
  v_\ell\left((q-1)/\operatorname{ord}_q(4)\right)=i_\ell.
  \]

Therefore every prime q in the source class satisfies

\[
v_\ell(\operatorname{ord}_q(4))
=
s_\ell-i_\ell
\ge
a_\ell.
\]

Thus the source Chebotarev cylinder

\[
\mathcal C_{p,d}
\]

satisfies

\[
\boxed{
\mathcal C_{p,d}\subseteq T_d.
}
\]

Because it is one nonempty conjugacy class of a finite Galois extension,
Chebotarev gives positive density.

## 4. Concrete d=5 source cylinder

For

\[
p=11,
\qquad
d=5,
\]

\[
s_5=1,
\qquad
i_5=0.
\]

The cyclotomic part fixes

\[
q\equiv11\pmod{25}.
\]

Finite matching controls include

\[
q=61,211,311,461,661.
\]

Each preserves

\[
5\mid\operatorname{ord}_q(4).
\]

The prime q=31 passes the broad depth gate but lies outside this source
cyclotomic cylinder.

Thus the source class is a strict structured positive-density subset of the
depth marginal.

## 5. Quantitative marginal no-go remains

For the fixed two-variable support marginal, Murty--Seguin--Stewart give only

\[
|S_h(x)|\gg\log x
\]

unconditionally.

The depth marginal has positive density.

Those two marginal sizes do not force an intersection.

For d=5, the complement of the necessary congruence

\[
q\equiv1\pmod5
\]

already has positive prime density, so a set known only at logarithmic scale
could lie entirely outside the gate.

Verdict:

MARGINAL_COUNTING_ONLY = NO_GO.

## 6. Sharpened minimal missing theorem

Since

\[
\mathcal C_{p,d}\subseteq T_d,
\]

it would suffice to prove

\[
\boxed{
\#(S_h\cap\mathcal C_{p,d})=\infty.
}
\]

This is:

\[
\boxed{
\text{SOURCE-CALIBRATED CHEBOTAREV-RESTRICTED TWO-VARIABLE SUPPORT}.
}
\]

This is narrower than:
- generic rank-two torus support;
- generic finite-target Schinzel--Wojcik;
- unrestricted torsion-gate correlation.

The source prime itself proves compatibility/nonemptiness of the local
Frobenius condition.

## 7. Current literature boundary

Reviewed unconditional pair-support theorems produce infinitely many support
primes but do not state that the final output primes may be restricted to one
preassigned finite Frobenius conjugacy class.

Restricting an auxiliary exponent prime inside a proof is not equivalent to
restricting the final output prime.

Under GRH, the existing multivariable Artin/Kummer index-map theorem already
handles simultaneous exact-index and finite Frobenius conditions.

## 8. Verdict

FOUND:
- exact chain-index compensation false positive;
- exact finite source depth signature;
- positive-density source Chebotarev subgate.

NO-GO:
- one total index closes the correlation;
- marginal counting closes the correlation;
- unrestricted pair-support automatically respects the source Frobenius class.

NEXT WITNESS:

\[
\boxed{
\text{UNCONDITIONAL CHEBOTAREV-RESTRICTED TWO-VARIABLE SUPPORT}.
}
\]

Equivalent acceptable input:

an unconditional proof that

\[
S_h\cap\mathcal C_{p,d}
\]

is infinite for every source-calibrated class.

No physical interpretation is involved.
No main branch was modified by this audit.


## 9. Pollack restricted-output architecture barrier

The source-calibrated class reduces the missing theorem to

\[
\#(S_h\cap\mathcal C_{p,d})=\infty.
\]

A direct reuse of Pollack's unrestricted pair proof fails at one exact point.

For an auxiliary prime exponent r and output prime divisor P of

\[
\alpha^r-\beta,
\]

pair-badness implies

\[
r\mid\operatorname{ord}_P(\alpha)
\]

and hence

\[
r\mid N(P)-1.
\]

This is the congruence that removes pair-bad output factors in the fundamental
identity.

Under the restricted-good definition there is a third class:

\[
P\text{ pair-good but }P\notin\mathcal C_{p,d}.
\]

For these primes,

\[
\langle\alpha^r\rangle=\langle\alpha\rangle,
\]

so for prime r,

\[
\gcd(r,\operatorname{ord}_P(\alpha))=1.
\]

There is no corresponding divisibility

\[
r\mid N(P)-1.
\]

Therefore the restricted-finiteness hypothesis does not imply the same
fundamental identity.

This proves:

VERBATIM_POLLACK_RESTRICTION_TO_FIXED_OUTPUT_FROBENIUS = NO_GO.

The auxiliary filter prime and the final output prime are distinct arithmetic
objects.

Updated next mechanism:

\[
\boxed{
\text{FROBENIUS-WEIGHTED OUTPUT CONTROL}
}
\]

or an exactly equivalent

\[
\boxed{
\text{CHEBOTAREV-RESTRICTED TWO-VARIABLE SUPPORT THEOREM}.
}
\]

Source receipt:

AdrianLipa90/On-Primes  
research/arpl-cyclotomic-two-target-frontier-v0.1-20260927  
ARPL_CHEBOTAREV_RESTRICTED_POLLACK_BARRIER_V0_1_VALIDATION_20260928.md.
