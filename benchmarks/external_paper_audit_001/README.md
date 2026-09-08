# GREMLIN External Paper Audit Benchmark 001

Status: BASELINE_FROZEN
Authority: VALIDATION_ONLY / CANDIDATE_ONLY
Main branch mutation: NONE

## Input

Danail Valov, *The Fractal Dimension of Spacetime: A Unified Geometric Framework from Photons to the Observable Universe* (May 2026), 40 pages.

The paper itself is not vendored in this public repository. Benchmark identity is bound by SHA-256:

`ad9c0c6a7c0ba661c9a0ea9b71efd6d7e708af9d38032545bdcc7dd4a3ec659a`

## Blindness rule

The pre-existing GREMLIN engine at base commit `ebab3dadcfe6674df877576d444648639e42f2e3` is evaluated before any Valov-specific audit logic is added. Manual peer-review findings are not supplied to OWL/SPIDER/MOLE/HOUND. The paper text is supplied as one local evidence source so the existing specialist logic receives the document content without a hand-authored fault list.

## Baseline

Executor: `GREMLIN_RESEARCH_EXECUTOR_V0_1` / `0.1.2`.

Observed baseline:

- HOUND substantive contradictions: `0`
- HOUND full-text contradiction test: `false`
- MOLE equation status: `UNRESOLVED_FROM_METADATA`
- MOLE gate: `REQUIRES_FULL_TEXT_OR_EXPLICIT_PREMISES_FOR_EQUATION_LEVEL_PROMOTION`
- SPIDER directionality gate: `SENTENCE_OR_FULL_TEXT_PARSE_REQUIRED_FOR_SUBJECT_PREDICATE_OBJECT`
- recall against the eight manually established major-fault classes: `0/8`

Verdict: `FAIL_CAPABILITY_GAP_FULL_TEXT_EQUATION_AUDIT`.

This is a useful baseline, not a synthetic PASS. The current engine correctly refuses equation-level promotion but does not yet perform the requested full-text mathematical/physical audit.

## Development rule

Valov 2026 may be used after this baseline only as a NONBLIND_REGRESSION fixture. Any upgraded full-text paper auditor must receive its next headline blind score on a different paper that was not used to design the rules.

Required generic capabilities for the upgrade are claim extraction, equation/number recomputation, dimensional checks, derivation-chain validation, internal contradiction search, source/claim provenance, and explicit OPEN/FAIL/PASS epistemic output. No paper-specific expected-answer strings may be embedded in the auditor.
