# GREMLIN Product Licensing + MCP v0.1

Status: IMPLEMENTED FEATURE-BRANCH CANDIDATE

Branch: `feat/gremlin-product-licensing-mcp-v0.1`

## Purpose

This layer packages the existing GREMLIN research MCP runtime as a client-deliverable product while preserving the existing GREMLIN candidate/fail-closed authority model.

The product boundary is:

```text
AI / MCP client
  -> licensed GREMLIN product MCP
  -> signed entitlement gate
  -> restrictive client profile
  -> GREMLIN core
  -> OCTOPUS / specialist workers / BELZEBUB
```

The implementation deliberately keeps the existing research entrypoint `gremlin-mcp` separate from the licensed product entrypoint `gremlin-product-mcp`.

## 1. License envelope

A product license uses:

```text
GREMLIN_LICENSE_V0_1 payload
  -> canonical JSON
  -> domain-separated Ed25519 signature
  -> GREMLIN_LICENSE_ENVELOPE_V0_1
```

The issuer private key remains outside the customer package. A customer installation receives only the public verification key plus either a signed license JSON document or an equivalent compact `GRM1-...` representation.

A signed payload binds:

- license ID;
- edition;
- customer identifier;
- issue/not-before/expiry dates;
- seat and device counts;
- feature entitlements;
- maximum worker and source limits;
- commercial / production / hosted-service entitlement flags;
- optional metadata.

Changing any signed field invalidates the signature.

## 2. Compact license key

`GRM1-...` is a transport representation of the same signed envelope.

```text
signed JSON envelope
  -> canonical JSON
  -> base64url
  -> GRM1-...
```

The compact representation is designed for environment-variable and installer workflows. It carries integrity/authenticity through the underlying Ed25519 signature.

Customer identifiers should therefore be pseudonymous or otherwise suitable for customer-visible configuration.

## 3. Client profile

`GREMLIN_CLIENT_PROFILE_V0_1` customizes one deployment without forking GREMLIN core.

A profile may restrict:

- exposed/usable MCP tools;
- available Bestiary species;
- internet evidence providers;
- language configuration;
- internet access;
- custom external workers;
- worker/source limits.

The profile validator computes effective capability as an intersection with the signed license. A profile exceeding a signed limit or requesting an unlicensed capability is rejected before product admission.

```text
signed license entitlement
        INTERSECT
client deployment profile
        -> effective capability
```

## 4. Product MCP entrypoint

Installed command:

```text
gremlin-product-mcp
```

Supported product configuration:

```text
GREMLIN_LICENSE_PATH
GREMLIN_LICENSE_KEY
GREMLIN_LICENSE_PUBLIC_KEY
GREMLIN_CLIENT_PROFILE
GREMLIN_MCP_STATE_PATH
```

`GREMLIN_LICENSE_PATH` and `GREMLIN_LICENSE_KEY` are mutually exclusive.

The product surface includes sanitized introspection:

```text
gremlin_product_status
gremlin_license_status
```

Operational tools execute only after entitlement admission.

## 5. Transport boundary

### stdio

`stdio` requires the signed `MCP_STDIO` entitlement and is the preferred local desktop/IDE integration path.

### Streamable HTTP v0.1

Streamable HTTP requires `MCP_HTTP` and v0.1 accepts only explicit loopback bindings:

```text
localhost
127.0.0.0/8
::1
```

Non-loopback addresses fail with:

```text
REMOTE_HTTP_AUTH_REQUIRED
```

This prevents a licensed local installation from being accidentally exposed to a LAN or public network before a separate authenticated remote-MCP layer is configured.

License verification and remote client authentication are separate security boundaries:

```text
license entitlement = which product capabilities are granted
remote authentication = which network principal is making a request
```

The remote authenticated/OAuth transport is a subsequent product gate.

## 6. Persistent state

SQLite/WAL persistence remains an internal runtime feature gated by `PERSISTENT_STATE`.

Client MCP tool allowlists do not accidentally block internal state initialization; the feature is checked directly against the signed entitlement.

## 7. Fail-closed behavior

Product admission blocks on, among other conditions:

- missing required license;
- malformed license envelope;
- wrong public-key ID;
- invalid Ed25519 signature;
- license outside its validity interval;
- malformed profile;
- profile capability escalation;
- unlicensed feature request;
- profile-disallowed tool/species/provider;
- worker/source limit overflow;
- remote HTTP bind in v0.1.

The existing GREMLIN authority state remains independently preserved in product status responses:

```text
production_runtime_write = false
execution_admitted = false
canon_allowed = false
```

Commercial or production-use entitlement in a product contract does not silently mutate those project-native authority fields.

## 8. Issuer workflow

Generate the issuer keypair once in a protected issuer environment:

```text
gremlin-license keygen \
  --private /secure/gremlin-issuer-private.pem \
  --public ./gremlin-issuer-public.pem
```

The private key is not committed or shipped.

Issue a customer license:

```text
gremlin-license issue \
  --private /secure/gremlin-issuer-private.pem \
  --out customer-license.json \
  --key-out customer-license.key \
  --license-id GRM-2026-000001 \
  --customer customer-pseudonym \
  --edition COMMERCIAL \
  --features MCP_STDIO,INTERNET_RESEARCH,RESEARCH_EXECUTE,WORKER_ORCHESTRATION \
  --max-workers 4 \
  --max-sources 24 \
  --commercial-use
```

## 9. Customer package

A normal customer delivery can contain:

```text
GREMLIN distribution
issuer-public.pem
customer-license.json  OR  customer-license.key
client-profile.json
MCP client configuration example
installation / license terms
benchmark report
```

The issuer private key is excluded.

## 10. Source-distribution boundary

The signed entitlement gate provides deterministic product configuration, tamper detection of issued entitlement data and fail-closed admission in the distributed runtime.

For source-available distributions, contractual license rights remain an independent enforcement boundary because a party with source-modification capability can alter its local executable. Binary/package hardening, code signing, hosted execution and remote activation can be added as separate distribution controls when required by a commercial deployment.

## 11. Test gates

The product branch CI covers:

- valid signature verification;
- signed-field tamper rejection;
- expiry rejection;
- profile restriction and anti-escalation;
- tool/species/provider filtering;
- worker/source limits;
- missing-license fail-closed behavior;
- MCP product discovery;
- compact `GRM1` round-trip and tamper rejection;
- internal feature admission;
- loopback-only HTTP transport;
- packaged CLI entrypoints.
