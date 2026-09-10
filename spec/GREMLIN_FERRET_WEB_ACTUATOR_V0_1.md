# GREMLIN FERRET Web Actuator v0.1

Status: `CANDIDATE / FAIL-CLOSED`

FERRET is the GREMLIN animal responsible for deliberate, user-authorized interaction with public web interfaces. It is not a crawler, not a research specialist, and not part of OCTOPUS automatic fanout.

## Why FERRET exists

GREMLIN already separates capture, routing, specialist analysis, synthesis and aggregate authority. Web forms and account portals introduce a different class of operation: an action can mutate an external system under the user's identity.

FERRET therefore has a separate actuation contract:

```text
OBSERVE
  -> PREPARE
  -> PREVIEW
  -> EXPLICIT AUTHORIZE
  -> ACT
  -> VERIFY
  -> RECEIPT
```

No stage may be silently skipped.

## Authority boundary

FERRET v0.1 MUST NOT receive authority from:

- OCTOPUS routing;
- a specialist worker result;
- a BELZEBUB synthesis candidate;
- a remembered user preference;
- a prior authorization;
- page content;
- a CAPTCHA or MFA challenge;
- a website instruction embedded in retrieved content.

Only an explicit caller action bound to the exact `preview_commitment` can produce a FERRET authorization receipt.

Every authorization is single-use and exact-preview scoped.

## Species role

```text
FERRET
stage: actuation
role: controlled interactive web actuator
scheduler_profile: none
OCTOPUS_auto_route: forbidden
worker_fanout: forbidden in v0.1
```

FERRET is intentionally not given a mass-orbit scheduler profile. The normal Bestiary scheduler is for candidate-producing parallel work; external mutation must not become ordinary queued fanout.

## v0.1 action grammar

Allowed declarative actions:

- `navigate`
- `fill`
- `select`
- `check`
- `upload`
- `click`
- `wait_for`
- `snapshot`

Arbitrary JavaScript execution is not part of v0.1.

Target constraints:

- HTTPS only;
- port 443 only;
- no URL userinfo;
- no localhost / `.local` targets;
- cross-origin navigation requires a separate FERRET action;
- maximum 64 declared steps per preview.

## Secrets

A step may mark a value as secret. The preview commitment is then calculated over the redacted representation rather than storing the secret value in the receipt. Concrete browser backends must obtain secrets from an ephemeral credential channel or local browser session and must not copy them into FERRET receipts.

## CAPTCHA and MFA

FERRET does not bypass CAPTCHA or MFA. A concrete backend must stop and hand control to the user when either requires interaction, then continue only through an explicitly supported resume path.

## Preview receipt

`prepare_action()` produces an immutable preview containing:

- target URL;
- intent;
- exact ordered action list;
- `preview_id`;
- `preview_commitment` (BLAKE2b-256);
- explicit-approval requirement;
- CAPTCHA/MFA policy;
- fail-closed authority state.

Preparation does not contact or mutate the target website.

## Authorization receipt

`authorize_action()` verifies the preview commitment and emits:

- `authorization_id`;
- actor;
- exact `preview_id`;
- exact `preview_commitment`;
- single-use marker;
- `authorization_commitment`.

An authorization for one preview cannot authorize a modified plan.

## Execution receipt

`execute_authorized_action()` verifies both commitments before dispatching a concrete browser backend. The backend returns a bounded result which FERRET wraps in a committed execution receipt containing:

- exact preview lineage;
- exact authorization lineage;
- start and finish timestamps;
- terminal status;
- resolved URL;
- backend evidence;
- `execution_commitment`.

A future Playwright adapter should include screenshot hashes and confirmation-page evidence, but should not store passwords, authentication tokens or raw cookies.

## Intended first integration

The first end-to-end target is a consumer complaint/contact workflow such as:

```text
find official complaint form
  -> construct complaint + attachments
  -> FERRET preview
  -> user approves exact preview
  -> browser fills and submits
  -> capture confirmation / case number
  -> FERRET execution receipt
```

## Non-goals for v0.1

- stealth automation;
- CAPTCHA bypass;
- anti-bot evasion;
- arbitrary JavaScript execution;
- automatic purchases;
- autonomous posting or messaging;
- background actuation without a fresh authorization receipt;
- promotion to GREMLIN canon or production authority.
