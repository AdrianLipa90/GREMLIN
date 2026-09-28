# GREMLIN Residual Red-Team v0.17 — Externally Attested Chronology

Status: ORCHESTRATION CANDIDATE / NO PURE-PYTHON TRUST CLAIM / NO CANON PROMOTION

Date: 2026-09-28

## Why v0.17 exists

v0.16 can validate the internal consistency of a candidate-bank seal, but a
caller can forge the supplied timestamp and verification booleans.

Therefore chronology must be observed from an authority outside the statistical
function.

The current v0.17 witness uses NOEMA Library metadata as that external authority.

## Required live verification

At evaluation time the orchestrator must re-query the current Library object and
bind:

- stable library_file_id;
- current backing file_id;
- current content/manifest commitment;
- server-side created_at;
- current version metadata when available.

Path/name alone is non-authoritative.

Cached historical metadata alone is non-authoritative.

The candidate-bank object must have server-side created_at strictly earlier
than the independently stored target-access object.

## Positive chronology witness

Original bank:

- library_file_id: libfile_981621b52854819190b7813fdcc985c1
- current file_id after rename: file_00000000752081f4ae926c725b548877
- server created_at: 2026-09-28T05:00:52Z
- manifest SHA256: 9ff44054e94226d6b94986c59afe978759fe1bda60a3d38de06bdf24211d26ee

Target-access witness:

- library_file_id: libfile_5221ac4e8c3081918c168a37a8870083
- file_id: file_0000000021ac81f4915eb5078dbac52a
- server created_at: 2026-09-28T05:01:06Z
- manifest SHA256: 95c4ec90ba3fff6880aff535d1a72643ccc237ade76a657b761a48a8cff03580

Thus the externally observed order is bank before target.

## Overwrite attack

A prior candidate-bank object was created before its target witness and then
overwritten after target access.

The stable library_file_id remained the same, but the current backing file_id
changed, version_id advanced, and the current created_at moved after target
access.

Therefore a live re-query rejects the overwritten bank.

A cached pre-overwrite timestamp would be unsafe.

## Path-replacement attack

The valid pre-target bank was renamed after target access.

Its stable library_file_id and content remained attached to the original object
and its server created_at remained pre-target.

A new malicious object was then uploaded under the old path.

The replacement received a new library_file_id and a post-target created_at.

Therefore:

[
\boxed{\text{library_file_id is authoritative; path is not}.}
]

## Remaining trust root

GREMLIN code does not prove that the Library service itself is truthful.

The Library service is an external trust root for this orchestration gate.

Any future editable-in-place mutation path must be red-teamed separately. The
verifier must always bind current content/version metadata, never only creation
time.

## Claim boundary

Chronology evidence is not causal independence.

A pre-target candidate may still share a hidden source with the target.

A v0.17 chronology PASS does not establish physical mechanism, new physics or
time fluctuations.
