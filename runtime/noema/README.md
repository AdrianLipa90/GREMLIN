# NOEMA resident GREMLIN source

This directory source-controls the resident `gremlind.py` implementation embedded into NOEMA autoboot bundles.

## Synchronization invariant

A resident GREMLIN change is complete only when all of the following are bound by provenance:

1. edit `runtime/noema/gremlind.py`;
2. pass repository regressions for the changed semantic contract;
3. embed the exact source bytes into the candidate NOEMA autoboot bundle;
4. update the bundle manifest hash for `extensions/gremlin_phase36d_rt/gremlind.py`;
5. boot the candidate with a fresh ACTIVE NOEMA↔AUX guard;
6. execute the same regression vector through the live resident daemon and Terminal36D/PhaseNav path;
7. record source SHA-256, bundle SHA-256, source/audit event IDs, authority and promotion state in an append-only validation receipt.

Repository tests alone do not establish live-runtime parity. A live candidate alone does not establish source-control parity.

The runtime remains `CANDIDATE_ONLY`; this source path grants no canon, external-effect, or automatic promotion authority.
