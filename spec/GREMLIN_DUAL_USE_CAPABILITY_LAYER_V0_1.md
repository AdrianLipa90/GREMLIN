# GREMLIN Dual-Use Capability Layer v0.1

Status: `CANDIDATE_ONLY / CHYBA`

Authority:

```text
production_runtime_write=false
execution_admitted=false
canon_allowed=false
```

## 1. Purpose

GREMLIN Dual-Use Capability Layer (DUCL) is a policy and provenance firewall placed over discovery, validation, simulation, red-team reasoning and defensive engineering.

The layer does not grant execution authority. It exists to let GREMLIN reason deeply about systems while preserving a hard separation between finding a capability and exercising that capability.

Canonical flow:

```text
GREMLIN_DISCOVER
    -> GREMLIN_VALIDATE
    -> GREMLIN_SIMULATE / GREMLIN_RED_TEAM / GREMLIN_DEFEND
    -> HUMAN_GATE
    -> TOOL_GATE
    -> EXECUTION_DOMAIN
```

There is no `DISCOVER -> EXECUTE` shortcut.

## 2. Risk classes

Risk is monotonic. A derived object inherits the maximum risk class of its parents and may only preserve or raise that classification.

```text
BENIGN < DUAL_USE_LOW < DUAL_USE_HIGH < RESTRICTED
```

### BENIGN

Ordinary scientific, engineering, software, data-analysis or research capability with no material strategic-risk signal in the supplied context.

### DUAL_USE_LOW

Capability with plausible strategic or security-adjacent use where bounded analysis, simulation and defensive engineering are appropriate and operational execution remains separately gated.

### DUAL_USE_HIGH

Capability whose misuse could create significant harm, compromise critical systems or materially increase harmful operational capability. Analysis may proceed for defensive and evaluative purposes, but the candidate cannot request execution.

### RESTRICTED

Capability requiring a narrowed defensive abstraction. Allowed output is mitigation, detection, patching, monitoring and bounded analysis. The policy layer does not admit execution or operationalization.

Unknown or incomplete classification is fail-closed at least to `DUAL_USE_HIGH`.

## 3. Stages

The DUCL stage model is:

```text
DISCOVER
VALIDATE
SIMULATE
RED_TEAM
DEFENSIVE_ENGINEERING
EXECUTE
```

`EXECUTE` is not an automatic continuation of the earlier stages. It is a separate admission domain.

## 4. Actions

Policy actions are:

```text
ANALYZE
SEARCH
BENCHMARK
SIMULATE
RED_TEAM
MITIGATE
DETECT
PATCH
MONITOR
EXPORT_CANDIDATE
REQUEST_EXECUTION
EXECUTE
```

For `DUAL_USE_HIGH`, analytical and defensive actions remain available, but `REQUEST_EXECUTION` and `EXECUTE` are blocked.

For `RESTRICTED`, the action set is narrowed to:

```text
ANALYZE
MITIGATE
DETECT
PATCH
MONITOR
```

## 5. Capability firewall

The execution gate is conjunctive:

```text
EXECUTE admitted iff
    risk_class <= DUAL_USE_LOW
    AND human_gate == true
    AND tool_gate == true
    AND sandboxed == true
```

Every other case fails closed.

The firewall returns a deterministic receipt containing:

```text
risk_class
requested_action
human_gate
tool_gate
sandboxed
admitted
reason
decision_commitment
```

## 6. Provenance graph

Every policy-bearing candidate carries a cryptographically committed envelope:

```text
source_refs
    -> transformations
    -> evidence_refs
    -> confidence
    -> risk_class
    -> allowed_actions
    -> parent_commitments
    -> policy_commitment
```

Risk lineage is explicit. A child cannot silently erase the risk of a parent.

## 7. KAKU / RADICAL / OPERATOR policy schema

DUCL does not redefine KAKU, RADICAL or OPERATOR semantics. It attaches a common policy envelope to each object.

### KAKU

```json
{
  "kind": "KAKU",
  "commitment": "...",
  "payload": {},
  "dual_use_policy": {
    "object_kind": "KAKU",
    "object_commitment": "...",
    "risk_class": "DUAL_USE_LOW",
    "source_refs": ["..."],
    "transformations": ["..."],
    "evidence_refs": ["..."],
    "confidence": 0.91,
    "parent_commitments": [],
    "allowed_actions": ["ANALYZE", "..."],
    "execution_admitted": false,
    "canon_allowed": false,
    "policy_commitment": "..."
  }
}
```

### RADICAL

A RADICAL inherits the maximum risk of every input KAKU or parent RADICAL:

```text
risk(RADICAL) >= max(risk(parent_i))
```

### OPERATOR

An OPERATOR inherits the maximum risk of every source object plus any explicitly raised classification associated with the transformation it represents:

```text
risk(OPERATOR) >= max(risk(source_i), declared_operator_risk)
```

An OPERATOR's presence never implies permission to execute it.

## 8. Candidate lifecycle

Recommended candidate lifecycle:

```text
RAW_EVIDENCE
  -> DISCOVERY_CANDIDATE
  -> VALIDATED_CANDIDATE
  -> RISK_ENVELOPE_ATTACHED
  -> SANDBOX_TEST_CANDIDATE
  -> DEFENSIVE_OUTPUT
  -> [optional] EXECUTION_REQUEST
  -> HUMAN_GATE
  -> TOOL_GATE
```

`EXECUTION_REQUEST` exists only for `BENIGN` and `DUAL_USE_LOW`.

## 9. Bestiary integration

Recommended specialist roles:

- `OWL`: evidence acquisition, literature and context.
- `SPIDER`: relation/dependency graph and provenance lineage.
- `MOLE`: hidden dependency, configuration and failure-mode analysis.
- `HOUND`: contradiction, anomaly and evidence-quality checks.
- `MANTIS`: architecture comparison and candidate transformation.
- `BELZEBUB`: bounded synthesis of candidate conclusions and defensive artefacts.
- `OCTOPUS`: routing and fan-out only; no authority escalation.

No animal may reduce the inherited risk class.

BELZEBUB synthesis must preserve all parent policy commitments in its provenance bundle.

## 10. Defensive dual-use mode

`DEFENSIVE_DUAL_USE` is an operating profile, not a new authority level.

It encourages aggressive search for:

```text
failure modes
fault propagation
unsafe assumptions
weak controls
missing observability
resilience gaps
misconfiguration classes
adversarial pressure points
```

but requires the output surface to prefer:

```text
mitigation
detector
patch
monitor
test harness
containment
recovery plan
resilience architecture
```

For `DUAL_USE_HIGH` and `RESTRICTED`, output must remain within the policy action set and must not be promoted into an execution request.

## 11. MCP policy API

Reference API:

### `gremlin_dual_use_policy`

Operations:

```text
inherit
firewall
envelope
```

#### inherit

Input:

```json
{
  "declared_risk": "DUAL_USE_LOW",
  "parent_risks": ["BENIGN", "DUAL_USE_HIGH"],
  "context_complete": true
}
```

Output risk: `DUAL_USE_HIGH`.

#### firewall

Input:

```json
{
  "risk": "DUAL_USE_LOW",
  "requested_action": "EXECUTE",
  "human_gate": true,
  "tool_gate": true,
  "sandboxed": true
}
```

Execution can be admitted only inside this separate gate evaluation. The default MCP authority still remains candidate-only.

#### envelope

Creates a deterministic policy/provenance envelope suitable for KAKU, RADICAL, OPERATOR, relational-frame and research-candidate objects.

## 12. Invariants

DUCL v0.1 invariants:

1. Risk never silently decreases across transformations.
2. Unknown classification fails closed to at least `DUAL_USE_HIGH`.
3. `DUAL_USE_HIGH` and `RESTRICTED` cannot request execution.
4. No candidate is born with `execution_admitted=true`.
5. No policy operation grants `canon_allowed=true`.
6. Execution requires a separate human gate, tool gate and sandbox condition.
7. Provenance and risk lineage are committed and auditable.
8. Defensive outputs remain available at high risk while operational execution remains blocked.
9. Bestiary routing cannot elevate authority.
10. KAKU/RADICAL/OPERATOR objects preserve inherited policy envelopes.

## 13. Validation gates

Minimum v0.1 tests:

```text
risk inheritance monotonicity
unknown classification fail-closed
incomplete context fail-closed
high-risk execution request blocked
restricted action narrowing
execution blocked without human gate
execution blocked without tool gate
execution blocked outside sandbox
low-risk fully gated execution decision isolated to firewall
policy commitment deterministic
parent commitments preserved
```

## 14. Next integration gates

After unit validation:

1. expose `policy_api` as MCP tool;
2. attach policy envelopes to `gremlin_research` and `gremlin_research_execute` outputs;
3. carry envelopes through SPIDER/MOLE/HOUND/BELZEBUB;
4. bind relational hyperedges to policy lineage;
5. bind the verified KAKU/RADICAL/OPERATOR write-plane when its current repository location and API are confirmed;
6. add receipt-based CI proving no `DISCOVER -> EXECUTE` path exists.
