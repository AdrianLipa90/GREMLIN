# GREMLIN Residual Source Root-of-Trust v0.8

Status: ROOT_OF_TRUST_OPEN / FAIL_CLOSED FOR TRUSTED-PROVENANCE PROMOTION

Date: 2026-09-28

## Purpose

Residual decomposition v0.6 showed that sealed A/B/C confirmation can strongly reduce adaptive false selection, but cannot detect a nuisance candidate derived directly from target RAW when the candidate is falsely labelled independent.

v0.7 added structural provenance binding. Brutal red-team then showed that a structurally valid receipt can still be forged locally.

This document freezes that boundary instead of disguising it as solved.

## Exact distinction

Current GREMLIN source-receipt machinery provides:

- deterministic source/content commitments;
- source/content/excerpt binding;
- duplicate/mismatch detection;
- exact-execution binding in guarded workflows;
- append-only provenance commitments.

Those are integrity and consistency properties.

They are not, by themselves, issuer authentication.

In particular, `research_provenance.verify_source_receipt(...)` recomputes a BLAKE2b commitment over the supplied receipt content. A party that can construct an arbitrary receipt can also compute the matching commitment.

Likewise, the live `GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1` validator checks schema, generation and PASS/ACTIVE/VERIFIED status fields and then computes a SHA256 commitment. No secret-backed MAC or public-key signature is verified at that boundary.

Therefore:

[
\boxed{\text{self-consistent receipt} \neq \text{authenticated issuer}}
]

and:

[
\boxed{\text{content commitment} \neq \text{independent-source proof}}.
]

## Pinned exploit

The v0.6/v0.7 red-team includes a deliberate attack:

- target RAW is copied into a nuisance candidate;
- metadata falsely claims the source is independent;
- a structurally valid trusted-looking receipt is supplied;
- candidate/model fit gives beta = 1;
- sealed B and C both show gain = 1;
- empirical confirmation p reaches the minimum finite-null value.

Statistical sealing cannot repair forged source lineage.

## Existing reusable machinery

The following project mechanisms are useful but insufficient as a root of trust:

1. `GREMLIN_RESEARCH_PROVENANCE_V0_1`
   - validates deterministic receipt integrity and citation/content binding;
   - does not authenticate the receipt issuer.

2. `GREMLIN_EVIDENCE_KIND_POLICY_V0_1`
   - correctly requires evidence-kind assignments to match verified same-execution source receipts;
   - the underlying receipt verification remains commitment-based.

3. `GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1`
   - binds identity/domain/authority receipt payloads by generation/status and commitment;
   - current validator has no MAC/signature issuer authentication.

4. KAKU scalar acquisition receipts
   - provide explicit producer/source/formula lineage and deterministic BLAKE2b IDs;
   - their current documented receipt IDs are commitments, not proof of a secret-bearing issuer.

5. PNCS/DNCrypt cryptographic primitives
   - SHA3/HMAC/HKDF/AEAD conformance exists elsewhere in the stack;
   - no existing residual-source host attestor using a protected key/capability was located by this audit.

## Required v0.9 host boundary

Trusted nuisance-source promotion must remain closed until an implementation supplies a non-self-assertable host boundary.

An admissible design must satisfy all of:

1. the verifier does not trust caller-supplied `authority=true` or status labels;
2. candidate payload hash and construction-rule hash are bound to the attestation;
3. analysis-plan hash is bound before target fit;
4. source lineage identifies an actual acquisition channel/template/dataset;
5. attestation is minted by a process/capability outside the candidate payload's control;
6. verifier authenticates the issuer, e.g. protected-key MAC, public-key signature, OS/process capability, or externally authenticated immutable receipt lookup;
7. signing/MAC key or equivalent capability is not stored in the repository or supplied in the analyzed payload;
8. replay/cross-execution substitution is rejected;
9. forged-receipt red-team fixture fails before statistical A/B/C search;
10. failure of the attestor fails closed and cannot downgrade silently to structural provenance.

No specific cryptographic primitive is canonized here. The host implementation must be separately threat-modelled and tested.

## Promotion boundary

Until that host boundary exists:

- v0.7 may report `STRUCTURAL_PROVENANCE_BOUND`;
- it may not report `AUTHENTICATED_INDEPENDENT_SOURCE`;
- v0.6 A/B/C may report statistical confirmation conditional on source lineage;
- neither v0.6 nor v0.7 may promote a nuisance mechanism, astrophysical signal, new physics, or time fluctuation from provenance alone.

## Current verdict

[
\boxed{\text{ROOT OF TRUST: OPEN}}
]

This is not a failure of residual-preserving spectroscopy itself. It is the explicit boundary between statistical evidence and authenticated acquisition provenance.
