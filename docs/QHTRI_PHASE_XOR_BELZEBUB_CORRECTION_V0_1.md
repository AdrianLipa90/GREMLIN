# BELZEBUB Correction: Scalar XOR vs Relational Phase XOR v0.1

Status: AUDIT CORRECTION / EPISTEMIC CHYBA / canon_allowed=false

## Candidate under audit

Potential identification:

```text
scalar_xor(a,b) = a+b-2ab
```

with

```text
phase_xor(theta_a,theta_b)
  = 1 - COHERENCE_TRUTH(theta_a-theta_b)
  = (1-cos(theta_a-theta_b))/2.
```

where

```text
a = COHERENCE_TRUTH(theta_a)
b = COHERENCE_TRUTH(theta_b).
```

## BELZEBUB counterexample

For

```text
theta_a = 0.2
theta_b = 1.1
```

we obtain

```text
a = 0.9900332889206208
b = 0.7267980607127886
scalar_xor = 0.27772280077618694
phase_xor  = 0.1891950158646678
absolute_delta = 0.08852778491151914
```

Therefore global operator identity fails.

## Surviving statement

On the binary phase boundary

```text
theta in {0,pi}
```

both constructions reproduce the same Boolean XOR truth table.

Away from that boundary:

```text
SCALAR_XOR_COMPAT != RELATIONAL_PHASE_XOR
```

in general.

## Verdict

`REJECT_GLOBAL_ISOMORPHISM`

`ACCEPT_EXACT_BOOLEAN_BOUNDARY_EQUIVALENCE`

## Implementation correction

Native QHTRI logic:

```text
XOR_NATIVE  := relational anti-lock / relative-phase coherence
XNOR_NATIVE := relational lock / relative-phase coherence
NOT_NATIVE  := pi phase translation
```

Compatibility/admission scalar algebra may retain:

```text
AND_SCALAR = ab
OR_SCALAR  = a+b-ab
XOR_SCALAR = a+b-2ab
NOT_SCALAR = 1-a
```

but must be explicitly tagged as scalar compatibility/gain algebra rather than QHTRI relational phase logic.
