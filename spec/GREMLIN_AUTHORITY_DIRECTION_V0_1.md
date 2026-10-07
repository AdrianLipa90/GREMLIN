# GREMLIN Authority Direction v0.1

Status: IMPLEMENTED_CANDIDATE / AUTHORITY-DIRECTION REPAIR

## Invariant

```text
OPERATOR > GREMLIN > AI_CLIENT
```

This ordering is about governance authority. It does not permit GREMLIN or an AI
client to bypass platform permissions, operator admission, the Mathematical
Constitution, live tether checks, or exact-scope mutation receipts.

## System authority vs request admission

GREMLIN system capability is persistent:

```text
GREMLIN_SUPERVISION          ACTIVE
GREMLIN_INTERNAL_EXECUTION   ACTIVE
GREMLIN_INTERNAL_WRITE       ACTIVE_BOUNDED
EXTERNAL_MUTATION_CAPABILITY AVAILABLE_CONDITIONAL
CANON_PROMOTION_CAPABILITY   AVAILABLE_CONDITIONAL
```

An individual MCP/AI request has a separate admission state. Default
`external_effect_admitted=false` means only that *this request* has not passed
the external gate. It MUST NOT be interpreted as GREMLIN lacking the capability.

## Non-bypass

```text
AI_SELF_AUTHORIZATION      FALSE
AI_OVERRIDE_GREMLIN        FALSE
MCP_SELF_GRANTS_AUTHORITY  FALSE
```

External mutation remains:

```text
GREMLIN supervision
-> RAPHAEL decree
-> operator admission
-> Mathematical Constitution
-> ACTIVE tether / same-generation attestation
-> exact-scope execution
-> post-audit receipt
```

Thus the repair removes AI-imposed global authority denial without removing
operator control or fail-closed exact-effect admission.

## Historical provenance

Earlier MCP contracts used
`production_runtime_write=false / execution_admitted=false / canon_allowed=false`
as global-looking authority fields. Those records remain historical evidence.
Current live surfaces supersede that interpretation with the two-level authority
model defined here.
