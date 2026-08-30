# GREMLIN Evidence Family Quorum v0.1

Status: `CANDIDATE_ONLY / CHYBA`

Authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## Purpose

This layer prevents multiple records from one provenance family from being treated as multiple independent support chains.

It is intentionally separate from contradiction resolution.

## Core rule

For unipolar semantic evidence:

```text
SUPPORT only      -> require >= N provenance families
CONTRADICT only   -> require >= N provenance families
```

Default strict profile:

```text
N = 2
```

A provenance family is a deterministic heuristic derived from execution citations using stable work identity where available (DOI, arXiv work ID, URL, conservative title bridge).

It is not proof of statistical, institutional, experimental or causal independence.

## Conflict rule

Mixed evidence is never resolved by quorum:

```text
SUPPORT + CONTRADICT -> HOUND contradiction gate
```

No number of SUPPORT families can vote away a CONTRADICT family, and vice versa.

## Confidence rule

Confidence is metadata only:

```text
confidence = 0.999 from one family != two provenance families
```

## Compatibility

The existing `semantic_bridge` remains unchanged.

The strict profile is exposed through:

```text
gremlin_mcp.semantic_quorum_bridge.apply_semantic_producer_output_with_quorum
```

This preserves backward compatibility while allowing higher-rigor research modes to require provenance-family diversity explicitly.

## Alias/version resistance

Two different `source_id` values that resolve to the same DOI/arXiv work/provenance family count once for quorum purposes.

Producer-declared source-family labels have no authority over this count.

## States

```text
FAMILY_QUORUM_SUFFICIENT
FAMILY_QUORUM_INSUFFICIENT
FAMILY_CONFLICT_DEFER_TO_HOUND
NO_RESOLVED_EVIDENCE
```

When a previously synthesizable unipolar result fails quorum, the strict bridge moves the synthesis to `quarantined_synthesis`, sets `synthesis=null`, and returns:

```text
SEMANTIC_EVIDENCE_FAMILY_QUORUM_INSUFFICIENT
```

## Invariants

1. Multiple evidence records from one provenance family count as one family.
2. Producer-declared family labels cannot increase quorum count.
3. Confidence cannot substitute for provenance-family diversity.
4. Conflict always defers to HOUND rather than majority voting.
5. Quorum cannot grant canon or production authority.
6. Existing semantic bridge behavior is preserved outside the strict wrapper.
7. Family diversity is explicitly labeled as heuristic, not proof of independence.
