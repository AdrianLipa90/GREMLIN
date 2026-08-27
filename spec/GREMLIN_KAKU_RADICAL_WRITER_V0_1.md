# GREMLIN KAKU/RADICAL Writer v0.1

Status: `IMPLEMENTED_CANDIDATE / CONTENT_ADDRESSED / IMMUTABLE_STORE`

## Goal

Give GREMLIN a durable coding surface for the first two PNCS levels:

```text
L0 KAKU
L1 RADICAL
```

The writer path is:

```text
KAKU scalar packet
-> KAKU persistence record
-> ordered KAKU record sequence
-> Radical scalar/admission payload
-> Radical persistence record
-> canonical JSONL bundle
-> immutable store receipt
```

## KAKU record

Schema:

```text
GREMLIN_KAKU_PERSISTENCE_RECORD_V0_1
```

A record binds:

```text
kaku_id
kaku_scalar_commitment
operator_kind
operator_classification
full signed KAKU payload
payload schema
content-addressed record_id
```

The content identity is BLAKE2b-256 over the complete canonical record body.

A changed scalar receipt, evidence lineage, direction, polarity, operator identity, source/target binding or KAKU commitment therefore changes the persistence identity.

## Radical record

Schema:

```text
GREMLIN_RADICAL_PERSISTENCE_RECORD_V0_1
```

A Radical record binds:

```text
radical_id
candidate_id
radical_scalar_commitment
ordered_kaku_record_ids
ordered_kaku_ids
relation_ids
pre_vector_status
vector_synthesis_allowed
full signed Radical payload
```

The ordered KAKU persistence sequence must match the Radical admission lineage exactly across:

```text
kaku_id
kaku_scalar_commitment
operator_kind
operator_classification
order
```

This makes a Radical an explicit reusable word/program fragment over exact KAKU atoms.

## Persistence bundle

Schema:

```text
GREMLIN_KAKU_RADICAL_PERSISTENCE_BUNDLE_V0_1
```

Canonical record order:

```text
KAKU_0
KAKU_1
...
KAKU_n
RADICAL
JSONL_BUNDLE_RECEIPT
```

Serialization:

```text
CANONICAL_JSONL_UTF8_LF
```

The bundle commitment binds the complete records and their ordering.

## Immutable store

The authoritative store helper is:

```text
tools/gremlin_kaku_radical_store_v01.py
write_immutable_bundle_jsonl(...)
```

Write semantics:

```text
new path + valid bundle
  -> atomic fsync + rename
  -> NEW_IMMUTABLE_OBJECT

existing path + identical bytes
  -> validate existing bundle
  -> IDEMPOTENT_EXISTING_BYTES

existing path + different bytes
  -> fail closed with immutable path collision
```

This allows reproducible content-addressed storage while preserving exact lineage.

## PNV representation

Native contract:

```text
native/GREMLIN_KAKU_RADICAL_WRITER_V0_1.pnv
```

It uses the existing PNV/1 vocabulary:

```text
SOURCE
IDENTITY
CONDITION
ORDER
TRANSFORM
COMPOSITION
RETURN
```

and introduces zero new PNV opcodes.

The native sequence expresses:

```text
KAKU source
-> KAKU validation
-> KAKU persistence transform

ordered KAKU records
+ Radical admission source
-> exact lineage condition
-> Radical persistence transform

ordered records
-> persistence composition
-> immutable store transform
-> receipt
```

## Authority boundary

Persistence records carry:

```text
execution_admitted = false
canon_allowed = false
storage_role = CONTENT_ADDRESSED_PERSISTENCE_OBJECT
```

The native contract carries:

```text
EXECUTION_AUTHORITY FALSE
CANON_ALLOWED FALSE
PRODUCTION_RUNTIME_WRITE FALSE
STORAGE_ROLE PERSISTENCE_ARTIFACT_ONLY
PHASENAV_REALIZATION_REQUIRED_LATER TRUE
```

The next coding layer can therefore consume a persisted Radical and create an `OPERATOR` candidate while preserving the exact KAKU/Radical provenance chain.

## Next gate

```text
persisted RADICAL
-> scalar-admitted PhaseNav IR
-> GREMLIN OPERATOR persistence record
-> exact T^36 realization
-> post-realization scalar receipt
```

The OPERATOR record will bind both the Radical persistence identity and the PhaseNav operator/IR commitment.
