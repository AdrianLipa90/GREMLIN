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

When a site inserts a CAPTCHA, MFA prompt, or comparable human-verification gate, the state machine branches without granting any extra authority:

```text
OBSERVE
  -> HUMAN_GATE_DETECTED
  -> HANDOFF_RECEIPT
  -> USER COMPLETES SITE CHALLENGE IN THE SAME VISIBLE BROWSER SESSION
  -> GATE_CLEAR_OBSERVED
  -> PRIVATE STORAGE STATE PERSISTED LOCALLY
  -> STORAGE STATE SHA-256 BOUND TO RESUME RECEIPT
  -> REOBSERVE
  -> PREPARE A NEW EXACT ACTION PREVIEW
```

The human-handoff branch never authorizes form submission by itself.

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

A step may mark a value as secret. The preview commitment is calculated over the redacted representation rather than storing the secret value in the receipt. Concrete browser backends must obtain secrets from an ephemeral credential channel or local browser session and must not copy them into FERRET receipts.

Browser storage state is treated as secret material. The human-handoff implementation writes it only to a local file, changes its mode to owner-only (`0600`) when supported, and places only its SHA-256, byte count and local path in the non-secret receipt. Raw cookies, local-storage values and authentication tokens are not returned in handoff or resume receipts.

## CAPTCHA and MFA

FERRET detects CAPTCHA/MFA/anti-bot surfaces from bounded browser metadata but does not solve or bypass them. Detection may identify signals such as hCaptcha, reCAPTCHA, Imperva and common MFA prompts.

The policy is fixed:

```text
CAPTCHA_OR_MFA
  -> STOP_AUTOMATION
  -> USER_ACTION_REQUIRED
  -> OBSERVE_ONLY_UNTIL_CLEAR
```

During the wait loop FERRET does not click the challenge, answer it, inject response tokens, call solver services, enable stealth plugins, or modify anti-bot controls.

A resume receipt is valid only when:

- the exact handoff commitment verifies;
- the user explicitly reports completion;
- the resumed page remains on the same origin;
- the local storage-state SHA-256 matches the receipt;
- no secret browser state is embedded in the receipt.

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

## Human handoff receipts

`detect_human_gate()` emits committed gate evidence without attempting a solution.

`prepare_human_handoff()` binds the exact preview, detected gate, current URL and target origin into `GREMLIN_FERRET_HUMAN_HANDOFF_V0_1` with status `USER_ACTION_REQUIRED`.

After the user clears the challenge, `persist_storage_state()` writes the Playwright context state to a private local file. `complete_human_handoff()` then binds only the storage-state SHA-256 into `GREMLIN_FERRET_HANDOFF_RESUME_V0_1` with status `READY_TO_RESUME`.

`verify_storage_state_for_resume()` fails closed when the local file hash differs from the resume receipt.

## Playwright browser surface

`gremlin_mcp.ferret_playwright` provides:

- a receipt-bearing Playwright execution backend;
- bounded page observation for CAPTCHA/MFA detection;
- a visible Chromium human-handoff session;
- an observe-only gate-clear wait loop;
- owner-only storage-state persistence and SHA-256 verification.

The optional package extra is:

```text
pip install -e '.[ferret]'
python -m playwright install chromium
```

The local helper command is:

```text
gremlin-ferret handoff \
  --url https://example.com/complaints \
  --actor USER \
  --state-path ~/.local/state/gremlin/ferret-session.json
```

It opens visible Chromium, pauses while the human completes a challenge, saves the resulting browser state locally, and emits committed resume metadata. It does not submit the target form.

## Execution receipt

`execute_authorized_action()` verifies preview and authorization commitments before dispatching a concrete browser backend. The backend returns a bounded result which FERRET wraps in a committed execution receipt containing:

- exact preview lineage;
- exact authorization lineage;
- start and finish timestamps;
- terminal status;
- resolved URL;
- backend evidence;
- `execution_commitment`.

The Playwright adapter includes screenshot hashes and confirmation-page evidence where requested by the preview. It does not store passwords, authentication tokens or raw cookies in execution receipts.

## Intended first integration

The first end-to-end target is a consumer complaint/contact workflow such as:

```text
find official complaint form
  -> open FERRET browser session
  -> human clears any site verification gate
  -> persist + hash resumed session
  -> reobserve target form
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
