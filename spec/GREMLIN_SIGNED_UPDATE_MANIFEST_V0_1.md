# GREMLIN Signed Update Manifest v0.1

Status: IMPLEMENTATION CANDIDATE / OFFLINE VERIFICATION ONLY

## 1. Purpose

This contract binds one GREMLIN release artifact to an Ed25519-signed manifest without adding any network download, installer execution or self-update authority.

The v0.1 boundary is:

```text
release artifact
  -> SHA-256 + exact byte size
  -> typed release metadata
  -> Ed25519 signature
  -> offline customer verification
  -> entitlement eligibility check
```

It is intentionally **not**:

```text
download
install
replace runtime files
elevate privileges
restart services
write production/canon state
```

## 2. Domain separation

Update manifests use:

```text
GREMLIN-UPDATE-MANIFEST/v0.1\0
```

before canonical JSON bytes are signed.

The same Ed25519 issuer key may be used operationally for product entitlements and release manifests, but the cryptographic domains are distinct. A valid license signature is therefore not a valid update-manifest signature and vice versa.

## 3. Manifest schema

```text
GREMLIN_UPDATE_MANIFEST_V0_1
```

Required fields:

```text
schema
product = GREMLIN
version
release_sequence
channel = PREVIEW | EARLY_ACCESS | STABLE
platform = windows | linux
architecture = amd64
artifact_name
artifact_sha256
artifact_size
released_on
```

`release_sequence` is an issuer-controlled monotonic integer for later availability ordering. v0.1 verifies and reports it but does not automatically compare or install releases.

`artifact_name` is a safe basename only. Paths, path traversal and directory separators are rejected.

`artifact_sha256` is exactly 64 lowercase hexadecimal characters.

`artifact_size` is the exact byte count and is verified separately from SHA-256.

## 4. Envelope schema

```text
GREMLIN_UPDATE_ENVELOPE_V0_1
```

The envelope contains:

```json
{
  "schema": "GREMLIN_UPDATE_ENVELOPE_V0_1",
  "manifest": { "...": "normalized manifest" },
  "signature": {
    "algorithm": "Ed25519",
    "key_id": "ed25519:...",
    "value": "canonical-unpadded-base64url"
  }
}
```

Unknown keys fail closed.

Duplicate JSON keys fail closed.

The configured public-key ID must exactly match the signed envelope key ID.

## 5. Issuance

Issuer-side command:

```text
gremlin-license update-issue \
  --private issuer-private.pem \
  --artifact GREMLIN-Early-Access-Linux-amd64.deb \
  --out GREMLIN-Early-Access-Linux-amd64.update.json \
  --version 0.5.0-ea.2 \
  --release-sequence 2 \
  --channel EARLY_ACCESS \
  --platform linux \
  --architecture amd64 \
  --released-on 2026-09-19
```

The command computes artifact SHA-256 and byte size itself. The operator does not provide them manually.

## 6. Customer verification

Customer-side command:

```text
gremlinctl update verify \
  --manifest GREMLIN-Early-Access-Linux-amd64.update.json \
  --artifact GREMLIN-Early-Access-Linux-amd64.deb \
  --platform linux \
  --architecture amd64 \
  --json
```

Verification order:

1. parse JSON with duplicate-key rejection;
2. reject unknown fields;
3. normalize typed manifest fields;
4. verify Ed25519 key ID and signature;
5. reject future-dated release metadata;
6. check platform and architecture eligibility;
7. check signed-license `updates_until` entitlement;
8. when an artifact is supplied, verify filename, exact byte size and SHA-256.

A manifest can be cryptographically valid while the customer is not entitled to that release. Those states remain distinct.

## 7. Authority contract

Every v0.1 verification receipt carries the effective boundary:

```text
download_performed = false
installation_performed = false
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

No v0.1 function executes or installs the verified artifact.

## 8. Validation gates

Required tests:

- signed round-trip PASS;
- payload tamper -> signature FAIL;
- duplicate JSON key -> FAIL;
- future release date -> FAIL;
- path traversal artifact name -> FAIL;
- exact size mismatch -> FAIL;
- SHA-256 mismatch -> FAIL;
- platform mismatch -> NOT_ELIGIBLE;
- expired `updates_until` -> NOT_ELIGIBLE;
- issuer CLI computes digest/size and produces a verifiable envelope.

Promotion beyond offline verification requires a separate design and authorization surface for trusted download and installer execution.
