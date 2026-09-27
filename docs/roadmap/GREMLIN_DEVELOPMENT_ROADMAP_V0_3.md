# GREMLIN Development Roadmap v0.3

**Date:** 2026-09-27  
**Repository:** `AdrianLipa90/GREMLIN`  
**Source main:** `ce0504a05ec371c40d51c3d535c08e588d9249e4`  
**Status:** `POST-CONSOLIDATION / EVIDENCE-FIRST / EXACT-HEAD-CI-PENDING`  
**Canonical constant:** `kappa = ln(2)/(24*pi)`

## 1. Scope

Roadmap v0.3 starts after the lossless 2026-09-27 consolidation.

Roadmap v0.2 is preserved as the dated 2026-09-18/post-promotion record. This file supersedes it only as the active forward plan; it does not rewrite its historical claims.

## 2. Current engineering baseline

The current baseline has:

- standalone package `gremlin-mcp 0.5.0`;
- 20 registered Bestiary roles;
- Worker ABI v0.2.6;
- 20-role PhaseNav v0.2 software-carrier surface;
- legacy frozen 18-role scalar/vector/continuous validation scope;
- deterministic OCTOPUS routing;
- external worker lifecycle and durable state;
- geometry/phase/state scheduling;
- phase-memory integrity hardening;
- residual-preserving and recursive-residual analysis surfaces;
- FERRET astronomy/FITS source preparation;
- NOEMA runtime material and reflexive routing tests;
- consolidated formalism/dynamics/calibration reports.

The current main merge is `ce0504a05ec371c40d51c3d535c08e588d9249e4`.

## 3. Closed in the 2026-09-27 consolidation

### Closed A — branch ancestry

All 26 named source branches in the final reverse-audit had `ahead_by=0` relative to the integration head before promotion.

After merge, representative source tips and the staging head had `ahead_by=0` relative to `main`.

### Closed B — conflict preservation

The ARPL report conflict was resolved by advancing staging to the newer source-tip report content before merging source ancestry.

The phase-memory conflict was resolved by preserving the stricter integration runtime while merging the original audit ancestry through an explicit resolution branch.

### Closed C — documentation provenance split

Historical v0.2 documentation remains frozen. Current state is recorded in new v0.3/post-2026-09-27 artifacts.

## 4. Open gate 1 — exact-head CI

This is the highest-priority blocker.

The final staging head showed 19 failed workflow runs. Representative failed jobs contained zero executed steps, consistent with runner-admission/infrastructure failure.

The final main merge commit had no combined statuses and no workflow runs in the post-merge query.

Required closure:

1. restore workflow runner admission;
2. execute the required suite on one exact current head;
3. record individual workflow outcomes;
4. distinguish test failure from infrastructure failure;
5. freeze a machine-readable exact-head validation receipt;
6. do not use historical green ancestors as substitutes.

## 5. Open gate 2 — repository-wide conformance after consolidation

After runner admission is restored, execute at minimum:

- MCP contract and registry tests;
- fail-loud repository audit;
- standalone runtime tests;
- installation and packaging tests;
- memory integrity/consolidation/anti-entropy tests;
- geometry scheduler tests;
- residual spectroscopy/decomposition tests;
- FERRET astronomy source-data tests;
- visual client tests;
- security and constitutional non-bypass tests.

The target is not "green by assumption". The target is an exact-head receipt from actual execution.

## 6. Open gate 3 — model-level operational benchmark

Run a preregistered A/B:

```text
A = same base model, same tasks, GREMLIN disabled
B = same base model, same tasks, GREMLIN enabled
```

Measure:

- final task success;
- human correction count;
- retries;
- context-loss incidents;
- regressions;
- provenance completeness;
- recovery after injected failure;
- wall-clock latency;
- token/model use;
- tool-call count.

Repeat across more than one backend before making a broad performance claim.

## 7. Open gate 4 — residual and spectroscopy validation

The consolidated residual stack must be evaluated without treating residuals as disposable noise and without promoting every residual structure to physics.

Required practice:

- preserve raw observations;
- separate nuisance-correlated structure from stable residual structure;
- retain signed/polarity information where the method requires it;
- preregister domain-specific controls;
- report negative results;
- distinguish computational feature utility from physical attribution.

## 8. Open gate 5 — formalism-to-physics boundary

The new coframe, Lorentz, Einstein, GL(3)/GL(4), defect and continuum reports provide mathematical/reference structure.

They do not automatically establish:

- empirical physical calibration;
- unique source binding;
- continuum normalization;
- quantum/field-theoretic renormalization;
- hardware realization;
- independent replication.

Every physical promotion requires an explicit source-to-observable chain and the evidence tier appropriate to that claim.

## 9. Software-v1 readiness

The software-v1 target now requires:

- reproducible Linux installation;
- reproducible Windows installation;
- stable standalone MCP startup;
- 20-role Bestiary manifest;
- deterministic OCTOPUS routing;
- external worker lifecycle;
- durable restart-safe state;
- geometry/phase/state scheduler;
- phase-memory integrity;
- context packing;
- licensing/readiness checks;
- fail-loud audit;
- exact-head CI closure;
- signed/frozen release provenance;
- preregistered model-solo versus GREMLIN benchmark;
- at least one independent external installation.

The legacy 18-role three-way PhaseNav suite remains historical evidence until a genuine 20-role three-way suite is executed.

## 10. Research-v1 readiness

Research-v1 remains separate from software-v1.

It requires, where claimed:

- live substrate binding;
- measured live input/output;
- explicit continuous operators;
- source-bound physical interpretation;
- independent replication;
- no substitution of computational compatibility for physical evidence.

## 11. Documentation discipline

Current documents may be updated or superseded by newer versions.

Historical receipts and dated reports are immutable evidence and must not be silently rewritten.

Required pattern:

```text
old frozen artifact
+ new state report
+ new provenance receipt
+ explicit supersession relation
```

## 12. Immediate execution order

1. Restore GitHub Actions runner admission.
2. Execute exact-head CI on the current repository state.
3. Freeze the exact-head validation receipt.
4. Re-run the full post-consolidation repository conformance suite.
5. Run the preregistered model-solo versus GREMLIN benchmark.
6. Validate residual/spectroscopy surfaces on external or instrumental data where available.
7. Keep physical/formalism promotions behind explicit evidence gates.
8. Update release documentation only from the resulting receipts.
