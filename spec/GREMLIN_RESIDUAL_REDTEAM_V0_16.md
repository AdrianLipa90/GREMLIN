# GREMLIN Residual Red-Team v0.16 — Sealed Candidate Bank

Status: CANDIDATE / PROVENANCE GATE / NO CANON PROMOTION

Date: 2026-09-28

## Failure inherited from v0.15

The v0.15 joint family null correctly preserves family dependence, but it is conditional on the supplied candidate bank.

A target-derived candidate can therefore pass perfectly if the bank itself is contaminated.

Pinned witness:

- RAW is pure Gaussian noise;
- one candidate is RAW.copy();
- seven candidates are independent noise proxies;
- v0.15 accepts the target-derived candidate with holdout gain 1.0 and familywise p=1/128.

No null calibration can repair a candidate manufactured from the target after target access.

## v0.16 admissibility gate

v0.16 separates candidate-bank admissibility from statistical testing.

Before target access, a bank seal commits to:

- analysis-plan SHA256;
- sorted candidate names;
- exact candidate-array SHA256 values and shapes;
- source type and source id;
- source commitment SHA256;
- null policy;
- frozen-before-fit and independent-of-target-fit declarations;
- external provenance evidence id and SHA256;
- external verification receipt SHA256;
- seal timestamp.

At evaluation time, the exact bank and metadata are recomputed and must match the seal byte-for-byte at the canonical-hash level.

The target access receipt binds the exact RAW/model commitments and a first-access timestamp.

The seal must predate target access.

An exact candidate-array hash equal to target RAW is rejected as defense in depth.

## What v0.16 does not prove

The code cannot prove that an external timestamp or provenance authority is truthful.

A forged external receipt can still lie.

Likewise, numerical similarity cannot prove or disprove causal independence: a legitimate instrument channel may correlate strongly with the target, while a leaked candidate may be transformed enough to evade an exact-hash check.

Therefore:

[
\boxed{
\text{seal consistency is machine-checkable}
\neq
\text{external provenance truth}
}
]

The external append-only/Git/timestamped provenance layer remains a trust root.

## Claim boundary

A statistically passing candidate is not unique causal attribution.

A sealed-bank PASS does not establish physical mechanism, new physics or time fluctuation.
