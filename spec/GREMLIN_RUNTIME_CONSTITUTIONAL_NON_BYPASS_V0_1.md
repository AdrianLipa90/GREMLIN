# GREMLIN Runtime Constitutional Non-Bypass v0.1

Status: IMPLEMENTED_CANDIDATE / DECLARED_SURFACE_NON_BYPASS / CANON_ALLOWED_FALSE

Date: 2026-09-20

## Purpose

The Mathematical Constitution defines admissibility. This layer binds that admissibility to concrete GREMLIN mutation entrypoints.

\[
\boxed{
\text{no declared high-consequence runtime mutation}
\;\text{may occur before}\;
\text{constitutional admission}.
}
\]

The runtime is fail-closed. Omitting the constitutional packet is not a legacy allow path.

## Request-bound action

For endpoint \(e\) and finite JSON request payload \(r\),

\[
h_r=\operatorname{SHA256}(\operatorname{canonicalJSON}(r)).
\]

The runtime ActionContract identifier is

\[
\boxed{
a(e,r)=\texttt{runtime:}e\texttt{:}h_r.
}
\]

Two requests with different canonical payloads therefore receive different request commitments except under a SHA-256 collision.

The binding contains endpoint, consequence class, request SHA-256, parameter provenance IDs, the complete ActionContract, and its own content commitment.

## Constitutional packet

A runtime packet contains

\[
\boxed{P=(B,A)}
\]

where \(B\) is the request-bound runtime action binding and \(A\) is the constitutional admission receipt for the exact ActionContract carried by \(B\).

Validation recomputes the runtime binding from the actual call arguments, the ActionContract commitment, the admission/action relation, and the packet commitment.

A packet for request \(r_1\) cannot admit \(r_2\).

## Fail-closed execution rule

For every declared mutation endpoint,

\[
\boxed{
M_e(r)\text{ executable}
\iff
\operatorname{RequireConstitutionalAdmission}(e,r,P)=ADMITTED.
}
\]

Missing, malformed, cross-endpoint, cross-request, DENY, or DEFER packets are rejected.

## Upstream scalar consistency

Where runtime independently validates an upstream channel, the constitutional admission must carry the same scalar.

The typed Bestiary gateway validates its capability receipt and requires

\[
\sigma_C=+1.
\]

RAPHAEL validates live authorization/tether/triple-pulse state and requires the corresponding authority/evidence values to remain PASS.

Thus an admission packet cannot contradict an independently observed upstream channel at the same execution surface.

## Declared v0.1 mutation registry

The registry contains 25 mutation surfaces.

hive_server.py:
- gremlin_hive_exchange_ingest
- gremlin_hive_exchange_bundle_ingest
- gremlin_hive_sync_apply
- gremlin_hive_place
- gremlin_hive_gates
- gremlin_hive_dispute
- gremlin_hive_latch

hive_authority_server.py: the same seven surfaces.

server_with_hive.py: the same seven Hive surfaces plus gremlin_hive_research_execute.

bestiary_memory_gateway.py:
- ingest_exchange_envelope_as_beast
- ingest_exchange_bundle_as_beast

raphael.py:
- execute

Therefore

\[
7+7+8+2+1=25.
\]

## Guard-before-mutation theorem

For every registered function \(f\), let \(g(f)\) be the top-level statement index of its unconditional require_constitutional_admission call and \(m(f)\) the first top-level statement containing any declared mutation call.

CI requires

\[
\boxed{
g(f)<m(f)
\qquad
\forall f\in\mathcal R_{25}.
}
\]

The proof rejects a guard hidden inside a conditional branch. The guard must be a direct top-level expression statement and must precede the first mutation-containing statement.

Each registered function must also expose a constitutional_packet input, and the guard endpoint/consequence literals must exactly match the explicit policy registry.

## Consequence mapping

Current exact Hive mapping:

- exchange envelope ingest: APPEND_ONLY;
- exchange bundle ingest: APPEND_ONLY;
- anti-entropy delta apply: APPEND_ONLY;
- place: APPEND_ONLY;
- dispute: APPEND_ONLY;
- closure-gate update: GOVERNANCE;
- latch: GOVERNANCE.

The consequence class determines the constitutional gate requirements; callers cannot reduce the required gate set.

## Bestiary composition

The typed gateway requires both:

\[
\operatorname{require\_access}(\cdots)=ALLOW
\]

and

\[
\operatorname{RequireConstitutionalAdmission}(\cdots)=ADMITTED.
\]

The constitutional admission must report \(\sigma_C=+1\).

Capability enforcement and constitutional admission remain distinct non-substitutable layers.

## RAPHAEL ordering

The runtime ordering is

\[
\boxed{
\text{decree verification}
\to
\text{authorization verification}
\to
\text{current-state read}
\to
\text{constitutional admission}
\to
\text{state-drift/live tether/triple-pulse checks}
\to
\text{single-use ledger consume}
\to
\text{reservation}
\to
\text{mutation}.
}
\]

This ordering matters because burn-and-abort consumes single-use authorization on stale/live-admission failure. Constitutional admission therefore precedes every declared governance mutation, including ledger consumption.

RAPHAEL executes admitted mutations; it does not define or override constitutional admissibility.

## Exact claims

Theorem 1 — exact-request non-replay:
different canonical request payloads produce different SHA-256 commitments except under a SHA-256 collision. Collision resistance is an explicit cryptographic assumption, not a theorem proved here.

Theorem 2 — endpoint non-replay:
the endpoint participates in the action ID and binding commitment, so a packet for endpoint \(e_1\) cannot validate for \(e_2\neq e_1\).

Theorem 3 — declared-surface pre-mutation guard:
for every function in the explicit registry, AST tests require one unconditional top-level guard and \(g(f)<m(f)\).

Theorem 4 — missing packet fail-closed:
constitutional_packet=None fails packet validation. No compatibility fallback converts missing evidence into ALLOW.

## Scope firewall

v0.1 does not yet prove:
- that the 25-function registry is exhaustive for every mutation reachable anywhere in the repository;
- cryptographic identity of every ethics-gate producer;
- distributed revocation or expiry of all packets;
- external IAM;
- physical interpretation of the action geometry;
- canon authority.

The stronger next theorem is repository-wide mutation reachability:

\[
\boxed{
\text{all mutation sinks}
\leftarrow
\text{all reachable call paths}
\leftarrow
\text{constitutional guard}.
}
\]

Implementation:
gremlin_mcp/constitutional_runtime.py

Structural coverage tests:
tests/test_gremlin_runtime_constitutional_coverage_v01.py

Runtime binding tests:
tests/test_gremlin_constitutional_runtime_v01.py

Authority:
CHYBA / CANDIDATE_ONLY / CANON_ALLOWED FALSE
