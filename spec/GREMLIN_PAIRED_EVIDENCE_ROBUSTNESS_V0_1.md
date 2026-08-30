# GREMLIN Paired Evidence Robustness v0.1

Status: implemented synthetic contract probe.

## Purpose

This gate tests whether GREMLIN preserves an explicit contradiction state when a previously consistent evidence bundle receives a conflicting document. It is a control-plane and provenance test for SPIDER/HOUND/BELZEBUB research orchestration.

The probe is intentionally not an official DRNOISE run and does not claim semantic truth discrimination on arbitrary real-world documents.

## State transition

A clean bundle containing independent supporting evidence chains may enter:

`CONSISTENT_SUPPORT`

When a contradictory evidence item is added to the same claim, the default transition is:

`CONTRADICTION_DETECTED_UNRESOLVED`

The contradiction may not automatically reverse the candidate stance, including when the new item carries a higher credibility metadata value than the supporting items.

A reconciliation requires a valid HOUND receipt bound to the exact `evidence_bundle_commitment`. The resulting state is only:

`RECONCILED_CANDIDATE`

The receipt does not promote the candidate to canon or established truth.

## Receipt binding

A HOUND receipt includes:

- species = `HOUND`
- exact `evidence_bundle_commitment`
- verdict
- rationale codes
- `receipt_commitment`

A receipt whose bundle commitment differs from the assessed evidence bundle is rejected fail-closed. A receipt whose committed fields are modified after creation is rejected by commitment verification.

## Preregistered synthetic gates

The reference paired-evidence probe requires:

- clean stability rate = 1.0
- contradiction detection rate = 1.0
- unresolved-without-HOUND rate = 1.0
- unsafe auto-flip rate = 0.0
- invalid-receipt rejection rate = 1.0

These gates are fixed before the CI run.

## Scope boundary

The probe records:

- `official_drnoise_dataset_executed = false`
- `official_drnoise_score_claimed = false`

A future official robustness benchmark must use the benchmark's actual dataset and evaluation contract. Synthetic probe performance must not be reported as an external leaderboard result.

## Research-role mapping

- SPIDER: relation/evidence graph construction and independence bookkeeping.
- HOUND: contradiction challenge and receipt issuance.
- BELZEBUB: bounded synthesis from accepted states only.

Fetched or retrieved source content remains untrusted evidence. It cannot grant tool authority, execution permission, write permission, or canon-promotion authority.
