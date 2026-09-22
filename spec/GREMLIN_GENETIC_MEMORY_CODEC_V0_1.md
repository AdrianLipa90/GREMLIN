# GREMLIN Genetic Memory Codec v0.1

Status: `IMPLEMENTED CANDIDATE / EXACT ROUND-TRIP / READ-ONLY HYPERCRYSTAL EXPRESSION / SHARED_COGNITION_ONLY / CHYBA`

Date: 2026-09-22

## Purpose

This layer adds an exact genetic representation for GREMLIN Hive Memory while preserving the existing append-only Hive record as the canonical logical object.

The genetic representation is a reversible transport and recall-index layer. It does not replace Hive persistence, does not rewrite lineage, and does not grant canon, repository, publication, or production authority.

The intended path is:

```
HiveRecord
  -> exact canonical bytes
  -> 6-bit codon genome
  -> optional 36D hypercrystal expression
  -> read-only recall/index candidate
```

No reverse path may mutate Hive state without the existing append-only authority and admission mechanisms.

## Exact codon transport

The base alphabet is:

```
A C G T
```

Three bases form one codon, so the complete codon space contains

```
4^3 = 64
```

tokens. The codec uses the lexicographic codon order over `A,C,G,T` as an exact bijection with integers `0..63`. Therefore each codon carries exactly six payload bits.

For an input byte string of length `n`, the encoder appends between zero and five zero padding bits so that the bit length is divisible by six. The packet stores the exact padding count. Decode rejects malformed codons, invalid padding, non-zero terminal padding and byte-length mismatch.

This representation has the same information density as direct 2-bit nucleotide encoding. A 288-byte T36 float64 surface therefore requires 1152 nucleotide bases.

## 64-symbol control vocabulary

Every codon also has a stable control-plane label. The labels include state, lineage, geometry, evidence and recall concepts such as:

`START`, `STOP`, `SCHEMA`, `SUBJECT`, `RECORD`, `PARENT`, `GENERATION`, `PAYLOAD`, `RELATION`, `PHASE`, `GEOMETRY`, `EVIDENCE`, `PROVENANCE`, `CONTEXT`, `ACTIVATION`, `REFERENCE`, `WORKING`, `EPISODIC`, `SEMANTIC`, `RELATIONAL`, `ARCHIVAL`, `EXPRESSION`, `COHERENCE`, `RECALL`, `CANDIDATE`, `DERIVE`, `SELECT`, and `RECOMBINE`.

These labels are an address/control vocabulary. They do not change the exact six-bit meaning of a codon and do not constitute a biological or semantic-truth claim.

## Genome packet

A packet binds:

- schema and codec version;
- media type;
- source record id;
- parent record id;
- payload size;
- SHA-256 payload commitment;
- exact padding;
- complete codon sequence;
- `SHARED_COGNITION_ONLY` authority;
- `CHYBA` epistemic status;
- `canon_allowed=false`.

The content address is

```
genome_id = BLAKE2b-256(canonical(packet_core))
```

with a domain-separated personalization string.

Hive memory records are encoded from the same canonical JSON representation used by the existing persistence surface. Decode verifies the packet commitment, payload digest, byte length, canonical JSON representation, `record_id`, and `parent_record_id`.

## Hypercrystal expression

The genome can be projected through an external 36D phase vector without changing the genome or Hive state.

For codon `c`, a deterministic 36D reference anchor `alpha_c` is derived from a domain-separated BLAKE2b address. Given phase vector `phi`, the reference coherence is

```
R_c^2 = | (1/36) sum_j exp(i (phi_j - alpha_c,j)) |^2
```

and the expression score is

```
score_c = frequency_c * R_c^2.
```

The resulting top-k codons form a read-only recall/index surface.

The anchor construction is deterministic reference addressing only. It does not assert semantic truth, biological mechanism, quantum mechanism, or physical hypercrystal realization.

The expression receipt binds the genome id and the SHA-256 commitment of exactly 36 finite little-endian float64 values.

## Hive integration

`HiveAuthorityRuntime` exposes:

- `genetic_snapshot(subject_id)` — exact genetic representation of the current Hive head;
- `genetic_restore_preview(packet)` — validate/decode without persistence;
- `genetic_expression(subject_id, phase36, ...)` — read-only 36D recall projection.

These methods do not call the Hive mutation path and do not touch `hive_records` or `hive_heads`.

No database migration is introduced.

## Fail-closed invariants

1. Exactly 64 codons and 64 unique control labels.
2. Encode/decode must be byte exact.
3. Genome commitment must match before payload acceptance.
4. Payload SHA-256 and exact byte length must match.
5. Hive JSON must decode to its canonical byte representation.
6. Source record and parent lineage bindings must match.
7. Hypercrystal expression requires exactly 36 finite coordinates.
8. Hypercrystal expression is read-only.
9. `canon_allowed` remains false.
10. No genetic operation can overwrite, delete or edit a Hive record in place.

## Evidence boundary

Current evidence establishes software-level exactness, deterministic addressing, tamper rejection, and no-persistence-change tests for the read-only Hive integration.

It does not establish that genetic terminology describes a biological memory substrate, nor that the reference 36D expression operator is a physical mechanism.
