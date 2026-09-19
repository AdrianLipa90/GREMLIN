from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

RAPHAEL_SCHEMA = "GREMLIN_RAPHAEL_WISDOM_MUTATION_V0_1"
RAPHAEL_VERSION = "0.1.0"
EPISTEMIC_MODE = "CHYBA"

EYE_SCHEMA = "GREMLIN_RAPHAEL_EYE_OBSERVATION_V0_1"
DECISION_SCHEMA = "GREMLIN_RAPHAEL_WISDOM_DECISION_V0_1"
DECREE_SCHEMA = "GREMLIN_RAPHAEL_MUTATION_DECREE_V0_1"
AUTHORIZATION_SCHEMA = "GREMLIN_RAPHAEL_MUTATION_AUTHORIZATION_V0_1"
RECEIPT_SCHEMA = "GREMLIN_RAPHAEL_MUTATION_RECEIPT_V0_1"

ACCEPT = "ACCEPT"
REJECT = "REJECT"
DEFER = "DEFER"
REQUIRE_MORE_EVIDENCE = "REQUIRE_MORE_EVIDENCE"
_DECISIONS = frozenset({ACCEPT, REJECT, DEFER, REQUIRE_MORE_EVIDENCE})

REQUIRED_WISDOM_PRODUCERS = ("GREMLIN", "OWL", "HOUND")
_ACCEPTING_EVIDENCE = frozenset({
    "PASS", "SUPPORT", "SURVIVED", "VALIDATED", "VALIDATED_PROTOTYPE", "READY", "ACCEPT"
})
_BLOCKING_EVIDENCE = frozenset({
    "FAIL", "REJECT", "CONTRADICT", "QUARANTINED", "UNRESOLVED", "DEFER", "REQUIRE_MORE_EVIDENCE"
})
_ALLOWED_OPERATIONS = frozenset({
    "CREATE_FILE", "UPDATE_FILE", "DELETE_FILE", "MOVE_FILE", "MERGE_BRANCH"
})

_HEX40_64 = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RaphaelError(RuntimeError):
    pass


class RaphaelWisdomError(RaphaelError):
    pass


class RaphaelAuthorizationError(RaphaelError):
    pass


class RaphaelExecutionError(RaphaelError):
    def __init__(self, message: str, *, receipt: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.receipt = dict(receipt) if isinstance(receipt, Mapping) else None


class MutationBackend(Protocol):
    def current_state(self) -> Mapping[str, Any]: ...
    def prepare(self, decree: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def apply_operation(self, operation: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def rollback(
        self,
        rollback_state: Mapping[str, Any],
        applied_results: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]: ...


class MutationLedger(Protocol):
    def cancel(self, decree_commitment: str) -> bool: ...
    def is_cancelled(self, decree_commitment: str) -> bool: ...
    def consume(self, decree_commitment: str, authorization_commitment: str) -> bool: ...


class InMemoryMutationLedger:
    """Reference single-use ledger. Production adapters should provide durable storage."""

    def __init__(self) -> None:
        self._cancelled: set[str] = set()
        self._decrees: set[str] = set()
        self._authorizations: set[str] = set()

    def cancel(self, decree_commitment: str) -> bool:
        decree = _hash64(decree_commitment, "decree_commitment")
        if decree in self._decrees:
            return False
        self._cancelled.add(decree)
        return True

    def is_cancelled(self, decree_commitment: str) -> bool:
        return _hash64(decree_commitment, "decree_commitment") in self._cancelled

    def consume(self, decree_commitment: str, authorization_commitment: str) -> bool:
        decree = _hash64(decree_commitment, "decree_commitment")
        authorization = _hash64(authorization_commitment, "authorization_commitment")
        if decree in self._cancelled or decree in self._decrees or authorization in self._authorizations:
            return False
        self._decrees.add(decree)
        self._authorizations.add(authorization)
        return True


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("RAPHAEL data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must be non-empty")
    return value


def _hash40_64(value: Any, field: str) -> str:
    value = _text(value, field).lower()
    if not _HEX40_64.fullmatch(value):
        raise ValueError(f"{field} must be lowercase 40..64 hexadecimal")
    return value


def _hash64(value: Any, field: str) -> str:
    value = _text(value, field).lower()
    if not _HEX64.fullmatch(value):
        raise ValueError(f"{field} must be lowercase 64 hexadecimal")
    return value


def _strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    rows = [_text(item, field) for item in value]
    if not allow_empty and not rows:
        raise ValueError(f"{field} must be non-empty")
    if len(rows) != len(set(rows)):
        raise ValueError(f"{field} contains duplicates")
    return rows


def _authority(*, mutation_authorized: bool = False) -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "mutation_authorized": bool(mutation_authorized),
    }


def _require_closed_authority(record: Mapping[str, Any], field: str) -> None:
    if record.get("authority") != _authority():
        raise RaphaelWisdomError(f"{field} attempted authority widening")


def _path(value: Any, field: str) -> str:
    value = _text(value, field).replace("\\", "/")
    if value.startswith("/") or value.startswith("../") or "/../" in f"/{value}/":
        raise ValueError(f"{field} must be repository-relative and traversal-free")
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if not parts:
        raise ValueError(f"{field} is empty after normalization")
    return "/".join(parts)


def _normalize_operation(operation: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(operation, Mapping):
        raise ValueError(f"operations[{index}] must be an object")
    kind = _text(operation.get("operation"), f"operations[{index}].operation").upper()
    if kind not in _ALLOWED_OPERATIONS:
        raise ValueError(f"unsupported RAPHAEL operation: {kind}")

    out: dict[str, Any] = {"operation": kind}
    if kind in {"CREATE_FILE", "UPDATE_FILE", "DELETE_FILE"}:
        out["path"] = _path(operation.get("path"), f"operations[{index}].path")
    elif kind == "MOVE_FILE":
        out["source_path"] = _path(operation.get("source_path"), f"operations[{index}].source_path")
        out["destination_path"] = _path(operation.get("destination_path"), f"operations[{index}].destination_path")
        if out["source_path"] == out["destination_path"]:
            raise ValueError("MOVE_FILE source and destination must differ")
    else:
        out["source_ref"] = _text(operation.get("source_ref"), f"operations[{index}].source_ref")
        out["target_ref"] = _text(operation.get("target_ref"), f"operations[{index}].target_ref")
        out["expected_head_sha"] = _hash40_64(
            operation.get("expected_head_sha"), f"operations[{index}].expected_head_sha"
        )

    if kind in {"CREATE_FILE", "UPDATE_FILE"}:
        content = operation.get("content")
        if not isinstance(content, str):
            raise ValueError(f"operations[{index}].content must be a string")
        out["content"] = content
        out["content_commitment"] = _commit(b"GREMLIN-RAPHAEL-CONTENT/v0.1", content)

    if kind in {"UPDATE_FILE", "DELETE_FILE", "MOVE_FILE"} and operation.get("expected_blob_sha") is not None:
        out["expected_blob_sha"] = _hash40_64(
            operation.get("expected_blob_sha"), f"operations[{index}].expected_blob_sha"
        )

    out["operation_commitment"] = _commit(b"GREMLIN-RAPHAEL-OPERATION/v0.1", out)
    return out


def _paths(operation: Mapping[str, Any]) -> set[str]:
    kind = operation["operation"]
    if kind in {"CREATE_FILE", "UPDATE_FILE", "DELETE_FILE"}:
        return {str(operation["path"])}
    if kind == "MOVE_FILE":
        return {str(operation["source_path"]), str(operation["destination_path"])}
    return set()


def _verified(record: Mapping[str, Any], field: str, domain: bytes) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("record must be an object")
    body = dict(record)
    supplied = _hash64(body.pop(field, None), field)
    expected = _commit(domain, body)
    if not secrets.compare_digest(supplied, expected):
        raise ValueError(f"{field} mismatch")
    return body


def angelic_manifest() -> dict[str, Any]:
    return {
        "schema": RAPHAEL_SCHEMA,
        "version": RAPHAEL_VERSION,
        "name": "RAPHAEL",
        "title": "Lord of Wisdom",
        "class": "ANGELIC_FUNCTION",
        "stage": "wisdom_governed_mutation",
        "role": "observe, reconcile, decree and execute exact-state mutation under external admission",
        "phases": ["EYE", "WORD", "HAND", "POST_AUDIT"],
        "bestiary_species": False,
        "epistemic": EPISTEMIC_MODE,
        "authority": _authority(),
        "invariants": [
            "NO_AUTHORIZATION_NO_MUTATION",
            "NO_DECREE_NO_MUTATION",
            "STATE_DRIFT_ABORT",
            "UNDECLARED_PATH_FORBIDDEN",
            "UNDECLARED_OPERATION_FORBIDDEN",
            "TEST_FAILURE_NO_COMPLETION",
            "POSTCONDITION_FAILURE_ROLLBACK_OR_QUARANTINE",
            "NO_SILENT_RECOVERY",
            "EVERY_MUTATION_EMITS_RECEIPT",
            "DECREE_MAY_BE_REJECTED_BEFORE_FIRST_WRITE",
            "SCOPE_IMMUTABLE_AFTER_FIRST_WRITE",
            "MUTATION_AUTHORITY_EXPIRES_AFTER_RECEIPT",
        ],
    }


def observe(
    *,
    objective: str,
    target_repository: str,
    target_branch: str,
    target_sha: str,
    operations: Sequence[Mapping[str, Any]],
    evidence_receipts: Sequence[Mapping[str, Any]],
    required_producers: Sequence[str] = REQUIRED_WISDOM_PRODUCERS,
) -> dict[str, Any]:
    """RAPHAEL.EYE: bind target state, mutation scope and epistemic receipts."""

    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        raise ValueError("operations must be a sequence")
    ops = [_normalize_operation(op, i) for i, op in enumerate(operations)]
    if not ops or len(ops) > 256:
        raise ValueError("RAPHAEL v0.1 requires 1..256 operations")

    if not isinstance(evidence_receipts, Sequence) or isinstance(evidence_receipts, (str, bytes)):
        raise ValueError("evidence_receipts must be a sequence")

    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    blockers: list[str] = []
    for i, receipt in enumerate(evidence_receipts):
        if not isinstance(receipt, Mapping):
            raise ValueError(f"evidence_receipts[{i}] must be an object")
        producer = _text(receipt.get("producer"), f"evidence_receipts[{i}].producer").upper()
        if producer in seen:
            raise ValueError(f"duplicate evidence producer: {producer}")
        seen.add(producer)
        status = _text(receipt.get("status"), f"evidence_receipts[{i}].status").upper()
        row = {
            "producer": producer,
            "status": status,
            "receipt_commitment": _hash64(
                receipt.get("receipt_commitment"),
                f"evidence_receipts[{i}].receipt_commitment",
            ),
        }
        evidence.append(row)
        if status in _BLOCKING_EVIDENCE:
            blockers.append(f"{producer}:{status}")
        elif status not in _ACCEPTING_EVIDENCE:
            blockers.append(f"{producer}:UNKNOWN_STATUS_FAIL_CLOSED")

    required = sorted({_text(item, "required_producer").upper() for item in required_producers})
    omitted_mandatory = sorted(set(REQUIRED_WISDOM_PRODUCERS) - set(required))
    if omitted_mandatory:
        raise RaphaelWisdomError(
            f"required_producers cannot remove mandatory wisdom producers: {omitted_mandatory}"
        )
    missing = [producer for producer in required if producer not in seen]

    repository = _text(target_repository, "target_repository")
    branch = _text(target_branch, "target_branch")
    sha = _hash40_64(target_sha, "target_sha")
    allowed_paths = sorted({p for operation in ops for p in _paths(operation)})
    scope_core = {
        "target_repository": repository,
        "target_branch": branch,
        "target_sha": sha,
        "allowed_paths": allowed_paths,
        "operations": ops,
    }
    core = {
        "schema": EYE_SCHEMA,
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "EYE",
        "epistemic": EPISTEMIC_MODE,
        "objective": _text(objective, "objective"),
        **scope_core,
        "scope_commitment": _commit(b"GREMLIN-RAPHAEL-SCOPE/v0.1", scope_core),
        "evidence_receipts": sorted(evidence, key=lambda row: row["producer"]),
        "required_producers": required,
        "missing_required_producers": missing,
        "blocking_evidence": sorted(blockers),
        "evidence_ready": not missing and not blockers,
        "authority": _authority(),
    }
    return {**core, "observation_commitment": _commit(b"GREMLIN-RAPHAEL-EYE/v0.1", core)}


def _verify_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    body = _verified(observation, "observation_commitment", b"GREMLIN-RAPHAEL-EYE/v0.1")
    if body.get("schema") != EYE_SCHEMA or body.get("phase") != "EYE":
        raise RaphaelWisdomError("RAPHAEL observation schema/phase mismatch")
    if body.get("epistemic") != EPISTEMIC_MODE:
        raise RaphaelWisdomError("RAPHAEL epistemic mode mismatch")
    _require_closed_authority(body, "RAPHAEL observation")
    return body


def judge(
    observation: Mapping[str, Any],
    *,
    decision: str,
    rationale_codes: Sequence[str],
    required_tests: Sequence[str] = (),
    postconditions: Sequence[str] = (),
    rollback_strategy: str = "ROLLBACK_OR_QUARANTINE",
) -> dict[str, Any]:
    """RAPHAEL.WORD: issue a committed decision and, on ACCEPT, an immutable decree."""

    obs = _verify_observation(observation)
    selected = _text(decision, "decision").upper()
    if selected not in _DECISIONS:
        raise RaphaelWisdomError(f"unsupported RAPHAEL decision: {selected}")
    rationale = sorted(set(_strings(rationale_codes, "rationale_codes")))
    tests = sorted(set(_strings(required_tests, "required_tests", allow_empty=True)))
    conditions = sorted(set(_strings(postconditions, "postconditions", allow_empty=True)))

    evidence_ready = bool(obs.get("evidence_ready"))
    if selected == ACCEPT and not evidence_ready:
        raise RaphaelWisdomError(
            "ACCEPT is forbidden while required evidence is missing, blocked or unknown"
        )

    core = {
        "schema": DECISION_SCHEMA,
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "WORD",
        "epistemic": EPISTEMIC_MODE,
        "observation_commitment": observation["observation_commitment"],
        "decision": selected,
        "rationale_codes": rationale,
        "evidence_ready": evidence_ready,
        "authority": _authority(),
    }
    decision_record = {
        **core,
        "decision_commitment": _commit(b"GREMLIN-RAPHAEL-WISDOM-DECISION/v0.1", core),
    }
    if selected != ACCEPT:
        return decision_record

    decree_core = {
        "schema": DECREE_SCHEMA,
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "WORD",
        "epistemic": EPISTEMIC_MODE,
        "decision_commitment": decision_record["decision_commitment"],
        "observation_commitment": observation["observation_commitment"],
        "objective": obs["objective"],
        "target_repository": obs["target_repository"],
        "target_branch": obs["target_branch"],
        "target_sha": obs["target_sha"],
        "scope_commitment": obs["scope_commitment"],
        "allowed_paths": list(obs["allowed_paths"]),
        "operations": list(obs["operations"]),
        "required_tests": tests,
        "postconditions": conditions,
        "rollback_strategy": _text(rollback_strategy, "rollback_strategy").upper(),
        "scope_immutable_after_first_write": True,
        "requires_external_authorization": True,
        "single_use": True,
        "authority": _authority(),
    }
    decree = {
        **decree_core,
        "decree_commitment": _commit(b"GREMLIN-RAPHAEL-MUTATION-DECREE/v0.1", decree_core),
    }
    return {**decision_record, "decree": decree}


def _verify_decree(decree: Mapping[str, Any]) -> dict[str, Any]:
    body = _verified(decree, "decree_commitment", b"GREMLIN-RAPHAEL-MUTATION-DECREE/v0.1")
    if body.get("schema") != DECREE_SCHEMA or body.get("phase") != "WORD":
        raise RaphaelWisdomError("RAPHAEL decree schema/phase mismatch")
    if body.get("scope_immutable_after_first_write") is not True:
        raise RaphaelWisdomError("RAPHAEL decree must freeze mutation scope")
    if body.get("requires_external_authorization") is not True or body.get("single_use") is not True:
        raise RaphaelWisdomError("RAPHAEL decree authority contract mismatch")
    _require_closed_authority(body, "RAPHAEL decree")
    return body


def cancel_decree(
    decree: Mapping[str, Any],
    *,
    reason_codes: Sequence[str],
    ledger: MutationLedger,
) -> dict[str, Any]:
    _verify_decree(decree)
    reasons = sorted(set(_strings(reason_codes, "reason_codes")))
    if not ledger.cancel(decree["decree_commitment"]):
        raise RaphaelAuthorizationError(
            "decree already consumed; cancellation is only admitted before mutation"
        )
    core = {
        "schema": "GREMLIN_RAPHAEL_DECREE_CANCELLATION_V0_1",
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "WORD",
        "decree_commitment": decree["decree_commitment"],
        "reason_codes": reasons,
        "status": "CANCELLED_BEFORE_MUTATION",
        "authority": _authority(),
    }
    return {
        **core,
        "cancellation_commitment": _commit(
            b"GREMLIN-RAPHAEL-DECREE-CANCELLATION/v0.1", core
        ),
    }


def authorize(
    decree: Mapping[str, Any],
    *,
    actor: str,
    approved: bool,
    observed_target_sha: str,
    authority_receipt_commitment: str,
) -> dict[str, Any]:
    """External authority binds one exact decree to one exact target state."""

    if type(approved) is not bool or not approved:
        raise RaphaelAuthorizationError("explicit mutation approval is required")
    body = _verify_decree(decree)
    actor_name = _text(actor, "actor")
    if actor_name.upper() == "RAPHAEL":
        raise RaphaelAuthorizationError("RAPHAEL cannot self-authorize mutation")
    external_receipt = _hash64(
        authority_receipt_commitment, "authority_receipt_commitment"
    )
    observed = _hash40_64(observed_target_sha, "observed_target_sha")
    if observed != body["target_sha"]:
        raise RaphaelAuthorizationError("STATE_DRIFT: target SHA differs from decree")

    core = {
        "schema": AUTHORIZATION_SCHEMA,
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "HAND_GATE",
        "authorization_id": secrets.token_hex(16),
        "authorized_unix_ns": time.time_ns(),
        "actor": actor_name,
        "authority_receipt_commitment": external_receipt,
        "authority_source": "EXTERNAL_TO_RAPHAEL",
        "decree_commitment": decree["decree_commitment"],
        "target_repository": body["target_repository"],
        "target_branch": body["target_branch"],
        "target_sha": body["target_sha"],
        "scope_commitment": body["scope_commitment"],
        "single_use": True,
        "authorization_scope": "EXACT_DECREE_AND_EXACT_TARGET_STATE",
        "authority": _authority(mutation_authorized=True),
    }
    return {
        **core,
        "authorization_commitment": _commit(
            b"GREMLIN-RAPHAEL-MUTATION-AUTHORIZATION/v0.1", core
        ),
    }


def _verify_authorization(
    decree: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, Any]:
    decree_body = _verify_decree(decree)
    auth = _verified(
        authorization,
        "authorization_commitment",
        b"GREMLIN-RAPHAEL-MUTATION-AUTHORIZATION/v0.1",
    )
    if auth.get("schema") != AUTHORIZATION_SCHEMA or auth.get("single_use") is not True:
        raise RaphaelAuthorizationError("RAPHAEL authorization contract mismatch")
    if auth.get("decree_commitment") != decree["decree_commitment"]:
        raise RaphaelAuthorizationError("authorization belongs to another decree")
    for field in ("target_repository", "target_branch", "target_sha", "scope_commitment"):
        if auth.get(field) != decree_body.get(field):
            raise RaphaelAuthorizationError(f"authorization {field} does not match decree")
    authority = auth.get("authority")
    if not isinstance(authority, Mapping) or authority.get("mutation_authorized") is not True:
        raise RaphaelAuthorizationError("mutation authority was not admitted")
    for field in ("production_runtime_write", "execution_admitted", "canon_allowed"):
        if authority.get(field) is not False:
            raise RaphaelAuthorizationError(f"global authority boundary opened: {field}")
    return auth


def _state_sha(state: Mapping[str, Any]) -> str:
    if not isinstance(state, Mapping):
        raise RaphaelExecutionError("backend current_state must be an object")
    try:
        return _hash40_64(state.get("target_sha"), "backend target_sha")
    except ValueError as exc:
        raise RaphaelExecutionError(str(exc)) from exc


def _receipt(
    *,
    decree: Mapping[str, Any],
    authorization: Mapping[str, Any],
    before_sha: str,
    after_sha: str | None,
    applied_results: Sequence[Mapping[str, Any]],
    tests: Mapping[str, str],
    postconditions: Mapping[str, str],
    status: str,
    rollback: Mapping[str, Any] | None,
    failure_code: str | None,
    mutation_started: bool,
) -> dict[str, Any]:
    core = {
        "schema": RECEIPT_SCHEMA,
        "raphael_schema": RAPHAEL_SCHEMA,
        "phase": "POST_AUDIT",
        "decree_commitment": decree["decree_commitment"],
        "authorization_commitment": authorization["authorization_commitment"],
        "before_target_sha": before_sha,
        "after_target_sha": after_sha,
        "applied_results": [dict(item) for item in applied_results],
        "tests": dict(tests),
        "postconditions": dict(postconditions),
        "status": status,
        "failure_code": failure_code,
        "rollback": None if rollback is None else dict(rollback),
        "mutation_started": bool(mutation_started),
        "authorization_consumed": True,
        "mutation_authority_expired": True,
        "authority": _authority(),
    }
    return {
        **core,
        "receipt_commitment": _commit(b"GREMLIN-RAPHAEL-MUTATION-RECEIPT/v0.1", core),
    }


def execute(
    decree: Mapping[str, Any],
    authorization: Mapping[str, Any],
    *,
    backend: MutationBackend,
    ledger: MutationLedger,
    test_runner: Callable[[str], bool] | None = None,
    postcondition_checker: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """RAPHAEL.HAND: exact mutation only; any failure rolls back or quarantines."""

    body = _verify_decree(decree)
    _verify_authorization(decree, authorization)
    if ledger.is_cancelled(decree["decree_commitment"]):
        raise RaphaelAuthorizationError("decree was cancelled before mutation")

    before_sha = _state_sha(backend.current_state())
    if before_sha != body["target_sha"]:
        if not ledger.consume(decree["decree_commitment"], authorization["authorization_commitment"]):
            raise RaphaelAuthorizationError("decree or authorization is cancelled/already consumed")
        receipt = _receipt(
            decree=decree,
            authorization=authorization,
            before_sha=before_sha,
            after_sha=before_sha,
            applied_results=[],
            tests={},
            postconditions={},
            status="ABORTED",
            rollback=None,
            failure_code="STATE_DRIFT",
            mutation_started=False,
        )
        raise RaphaelExecutionError(
            "STATE_DRIFT: backend target SHA differs from decree",
            receipt=receipt,
        )

    try:
        rollback_state = backend.prepare(body)
    except Exception as exc:
        raise RaphaelExecutionError(
            f"ROLLBACK_PREPARATION_FAILED: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(rollback_state, Mapping):
        raise RaphaelExecutionError("ROLLBACK_PREPARATION_FAILED: non-object rollback state")

    if not ledger.consume(decree["decree_commitment"], authorization["authorization_commitment"]):
        raise RaphaelAuthorizationError("decree or authorization is cancelled/already consumed")

    allowed_paths = set(body["allowed_paths"])
    applied: list[Mapping[str, Any]] = []
    tests: dict[str, str] = {}
    postconditions: dict[str, str] = {}
    mutation_started = False

    def fail(code: str, message: str) -> None:
        rollback_result: Mapping[str, Any] | None = None
        status = "ABORTED"
        if mutation_started:
            status = "QUARANTINED"
            try:
                rollback_result = backend.rollback(rollback_state, applied)
                if isinstance(rollback_result, Mapping) and rollback_result.get("status") == "ROLLED_BACK":
                    status = "ROLLED_BACK"
            except Exception as exc:
                rollback_result = {
                    "status": "ROLLBACK_FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                }
        try:
            after_sha = _state_sha(backend.current_state())
        except RaphaelExecutionError:
            after_sha = None
        receipt = _receipt(
            decree=decree,
            authorization=authorization,
            before_sha=before_sha,
            after_sha=after_sha,
            applied_results=applied,
            tests=tests,
            postconditions=postconditions,
            status=status,
            rollback=rollback_result,
            failure_code=code,
            mutation_started=mutation_started,
        )
        raise RaphaelExecutionError(message, receipt=receipt)

    for index, operation in enumerate(body["operations"]):
        if not _paths(operation) <= allowed_paths:
            fail("UNDECLARED_PATH", f"operation {index} escapes frozen scope")
        if operation.get("operation") not in _ALLOWED_OPERATIONS:
            fail("UNDECLARED_OPERATION", f"operation {index} is not admitted")
        if not mutation_started and _state_sha(backend.current_state()) != before_sha:
            fail("STATE_DRIFT", "target state changed before first mutation")

        mutation_started = True
        try:
            result = backend.apply_operation(operation)
        except Exception as exc:
            fail("MUTATION_OPERATION_FAILED", f"operation {index} failed: {type(exc).__name__}: {exc}")
        if not isinstance(result, Mapping):
            fail("MALFORMED_MUTATION_RESULT", f"operation {index} returned non-object result")
        if result.get("operation_commitment") != operation["operation_commitment"]:
            fail("OPERATION_RECEIPT_MISMATCH", f"operation {index} receipt does not bind exact decree operation")
        applied.append(dict(result))

    if body["required_tests"] and test_runner is None:
        fail("TEST_RUNNER_MISSING", "required tests exist but no test runner was supplied")
    for name in body["required_tests"]:
        try:
            raw_test_result = test_runner(name) if test_runner is not None else None
        except Exception as exc:
            fail("TEST_EXECUTION_FAILED", f"test {name!r} raised {type(exc).__name__}: {exc}")
        if type(raw_test_result) is not bool:
            fail("MALFORMED_TEST_RESULT", f"test {name!r} must return an exact boolean")
        ok = raw_test_result
        tests[name] = "PASS" if ok else "FAIL"
        if not ok:
            fail("TEST_FAILURE", f"required test failed: {name}")

    if body["postconditions"] and postcondition_checker is None:
        fail("POSTCONDITION_CHECKER_MISSING", "postconditions exist but no checker was supplied")
    for condition in body["postconditions"]:
        try:
            raw_postcondition_result = (
                postcondition_checker(condition) if postcondition_checker is not None else None
            )
        except Exception as exc:
            fail(
                "POSTCONDITION_EXECUTION_FAILED",
                f"postcondition {condition!r} raised {type(exc).__name__}: {exc}",
            )
        if type(raw_postcondition_result) is not bool:
            fail(
                "MALFORMED_POSTCONDITION_RESULT",
                f"postcondition {condition!r} must return an exact boolean",
            )
        ok = raw_postcondition_result
        postconditions[condition] = "PASS" if ok else "FAIL"
        if not ok:
            fail("POSTCONDITION_FAILURE", f"postcondition failed: {condition}")

    try:
        final_sha = _state_sha(backend.current_state())
    except RaphaelExecutionError as exc:
        fail("FINAL_STATE_UNVERIFIABLE", f"final backend state is not verifiable: {exc}")

    return _receipt(
        decree=decree,
        authorization=authorization,
        before_sha=before_sha,
        after_sha=final_sha,
        applied_results=applied,
        tests=tests,
        postconditions=postconditions,
        status="PASS",
        rollback=None,
        failure_code=None,
        mutation_started=mutation_started,
    )
