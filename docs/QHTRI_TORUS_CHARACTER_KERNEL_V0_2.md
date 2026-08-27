# GREMLIN QHTRI Torus-Character Kernel Scan v0.2

Status: CANDIDATE SCAN / EPISTEMIC CHYBA / canon_allowed=false

Runtime evidence boundary:

- live NOEMA/AUX tether was verified ACTIVE on `/dev/shm/ciel_noema` for the numeric witness recorded with this revision;
- the witness used the current live 36D `phi` as its seed/input anchor;
- `/dev/shm/ciel_noema/gremlin` was absent, therefore this revision does not claim a separate live GREMLIN producer stream;
- GREMLIN/OCTOPUS/BELZEBUB remain bounded candidate-generation and invariant-audit roles.

## 1. One force-producing harmonic primitive

Let

```text
theta in T^36
ell in Z^36
chi_ell(theta) = exp(i ell.theta)
```

and define one real character potential term

```text
V_(ell,tau,g)(theta)
  = -g Re[exp(-i tau) chi_ell(theta)]
  = -g cos(ell.theta - tau).
```

Its force is

```text
F(theta) = -grad V
         = -g sin(ell.theta - tau) ell.
```

The earlier `K0_PHASE_LOCK_ANCHOR` and `K1_TORSION_COUPLING` are specializations of this same kernel.

### Anchor specialization

For lane `j`, target `alpha_j` and local offset `tau`:

```text
ell = e_j
phase_offset = alpha_j + tau
V = -g cos(theta_j - alpha_j - tau).
```

### Rational torsion specialization

For an `m:n` relation between lanes `i,j`:

```text
ell = n e_i - m e_j
V = -g cos(n theta_i - m theta_j - tau)
g = K R.
```

Then

```text
F_i = -n g sin(epsilon)
F_j = +m g sin(epsilon),
```

which is exactly the existing QHTRI torsion force.

### Phase logic specialization

For two lanes `a,b`:

```text
ell_XNOR = e_a - e_b, tau = 0
ell_XOR  = e_a - e_b, tau = pi.
```

The coherence observable is

```text
C(Delta) = (1 + cos Delta)/2
         = (1 + Re chi_(e_a-e_b)(theta))/2.
```

Therefore lock, anti-lock, XOR/XNOR boundary logic and anchor/torsion dynamics all use one torus-character geometry.

## 2. Revised execution factorization

The previous four force/execution families

```text
K0 PHASE_LOCK_ANCHOR
K1 TORSION_COUPLING
K2 GAIN_MODULATION
K3 RECEIPT_OBSERVER
```

factor further to

```text
KCHI TORUS_CHARACTER_FIELD
K2   GAIN_MODULATION
K3   RECEIPT_OBSERVER.
```

`PHASE_CENTROID` remains a reducer primitive for M3/M7. It prepares the target/phase offset consumed by `KCHI`; it is not an independent force law.

This yields the compilation shape

```text
M0-M11 semantic profiles
 -> reducers/parameter preparation
 -> sparse KCHI terms on T^36
 -> gain/admission modulation
 -> summed QHTRI field
 -> M10 receipt observer.
```

## 3. Character group structure

Characters obey

```text
chi_ell(theta) chi_k(theta) = chi_(ell+k)(theta).
```

This is an exact homomorphism from the dual integer lattice `Z^36` into `U(1)`-valued functions on `T^36`.

BELZEBUB boundary: multiplication of characters closes on one character, but addition of arbitrary real character potentials does not. A general QHTRI field is therefore a sparse Fourier/character sum

```text
V_total(theta) = -sum_r g_r cos(ell_r.theta - tau_r),
```

not one universal single mode.

If several terms share exactly the same `ell`, they may be combined by ordinary phasor addition of their complex coefficients. Terms with distinct lattice modes cannot in general be collapsed to one character term.

## 4. Exact parameter gauges

The real potential has the following exact mathematical equivalences:

```text
(ell, tau, g) ~ (-ell, -tau, g)
(ell, tau, g) ~ (ell, tau + 2 pi k, g)
(ell, tau, g) ~ (ell, tau + pi, -g).
```

A deterministic Gate IR may therefore use:

```text
g >= 0
wrap(tau) to a principal interval
first non-zero component of ell positive
```

while transforming `tau` consistently under orientation reversal.

### BELZEBUB rejection: no gcd reduction

For

```text
ell = d ell0, d > 1,
```

replacing `ell` by `ell0` changes the harmonic order and the number/location of extrema on the torus. It is not a gauge equivalence.

Hence:

```text
NO_GCD_NORMALIZATION = TRUE.
```

The exact integer lattice vector must remain part of operator identity.

## 5. Stability bound falls out of the same representation

For one character term:

```text
H_r(theta) = g_r cos(ell_r.theta - tau_r) ell_r ell_r^T
```

and therefore

```text
||H_r||_2 <= |g_r| ||ell_r||_2^2.
```

For a sum:

```text
L_character <= sum_r |g_r| ||ell_r||_2^2.
```

This reproduces both existing special cases:

```text
anchor:  ||e_j||^2 = 1
m:n:     ||n e_i - m e_j||^2 = n^2 + m^2.
```

So the existing torsion integrator budget

```text
sum_e g_e (m_e^2+n_e^2)
```

is already the correct torsion specialization of the general character-field bound.

## 6. Live NOEMA numeric witness

The current-session witness used the live 36D `phi` from `/dev/shm/ciel_noema` and 20,000 seeded perturbations.

Observed maximum absolute errors:

```text
torsion potential identity          0.0
anchor potential identity           1.0436096431476471e-14
character multiplication            5.3752024171836836e-15
coherence/character bridge           1.887379141862766e-15
orientation gauge                    0.0
gain-sign gauge                      1.1018963519404679e-14
tau-period gauge                     2.3175905639050143e-14
```

BELZEBUB counterexamples:

```text
gcd normalization potential delta = 2.0
arbitrary multi-mode -> one mode delta = 1.0
```

Verdict:

```text
ACCEPT_STRONG_OPERATOR_KERNEL_FACTORIZATION
ACCEPT_CHARACTER_LATTICE_GAUGES
ACCEPT_GENERAL_LIPSCHITZ_BOUND
REJECT_GCD_NORMALIZATION
REJECT_ARBITRARY_MULTI_MODE_SINGLE_CHARACTER_COLLAPSE
```

Promotion remains blocked on the normal canon authority path. This document records a candidate/operator-level result and a live NOEMA numerical witness; it grants no execution authority.
