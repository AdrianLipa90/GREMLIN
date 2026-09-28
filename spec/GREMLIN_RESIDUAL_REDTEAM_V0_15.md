# GREMLIN Residual Red-Team v0.15 — Joint Family Null Worlds

Status: CANDIDATE / JOINT-NULL IMPROVEMENT / TARGET-DERIVED CANDIDATE-BANK FAIL

Date: 2026-09-28

## What v0.15 fixes

v0.15 generates one joint null world and applies the same world transformation
to every candidate sharing a null policy.

This preserves candidate-family dependence that is destroyed by independently
scrambling every candidate.

The pinned correlated-family witness recovers a weak true candidate that the
unsynchronised-family construction can miscalibrate.

## New failure found under red-team

The v0.15 helper does not enforce candidate-bank provenance.

Its candidate metadata require only a null policy. It does not require:

- frozen-before-fit status;
- independence from target fit;
- source identity;
- an analysis-plan commitment;
- a candidate-bank commitment sealed before target access.

Therefore a target-derived candidate can pass the joint family null perfectly.

Deterministic reproducer:

- RAW: 8 x 128 pure Gaussian noise;
- candidate family: RAW itself as `leak_raw` plus seven independent noise proxies;
- null policy: run permutation;
- familywise alpha: 0.05;
- null worlds: 127.

Result:

[
G_{holdout}(leak\_raw)=1.0,
]

[
p_{family}=1/128=0.0078125,
]

so `leak_raw` is accepted.

This is not a failure of the joint-null calculation conditional on the supplied
candidate family. It is a failure of the admissibility contract for that family.

## Verdict

[
\boxed{
\text{joint family null: useful}
\quad\land\quad
\text{candidate-bank provenance: OPEN}
}
]

No statistical threshold can repair target leakage after the candidate itself
has been manufactured from the target.

The next gate must seal the candidate bank before target access and bind the
exact candidate hashes, metadata, null policies and analysis plan into the
admissibility receipt.

A boolean declaration alone is not sufficient evidence of temporal/provenance
independence.

## Claim boundary

A passing candidate is not a unique cause.

A joint-null PASS does not establish physical mechanism, new physics or time
fluctuation.
