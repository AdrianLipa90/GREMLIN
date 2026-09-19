from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

ACTION_SCHEMA = "PHASENAV_ACTION_PACKET_V1"
ATTESTATION_SCHEMA = "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1"
EXECUTION_RECEIPT_SCHEMA = "PHASENAV_EXECUTION_RECEIPT_V1"
CAPABILITY_SCHEMA = "GREMLIN_PHASENAV_MCP_VCS_CAPABILITY_V0_1"

_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,180}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_FORBIDDEN_OPS = {"delete", "move", "rename", "force_push", "reset", "rebase"}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(value: Any, domain: str) -> str:
    h = hashlib.sha256()
    h.update(domain.encode("utf-8"))
    h.update(b"\x00")
    h.update(_canon(value))
    return h.hexdigest()


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _validate_head(value: str, name: str) -> str:
    text = _require_text(value, name).lower()
    if not _HEX40_RE.fullmatch(text):
        raise ValueError(f"{name} must be a 40-character lowercase hexadecimal commit SHA")
    return text


def _validate_action_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema") != ACTION_SCHEMA:
        raise ValueError(f"action_packet.schema must be {ACTION_SCHEMA}")
    # The repository currently names PHASENAV_ACTION_PACKET_V1 but does not publish
    # a canonical field schema. Preserve the packet opaquely and bind its exact bytes.
    # Operational authority is therefore never inferred from unknown fields.
    packet_dict = dict(packet)
    return {
        "schema": ACTION_SCHEMA,
        "packet": packet_dict,
        "packet_commitment": _commit(packet_dict, ACTION_SCHEMA),
    }


def _validate_attestation(attestation: Mapping[str, Any]) -> dict[str, Any]:
    if attestation.get("schema") != ATTESTATION_SCHEMA:
        raise ValueError(f"gremlin_attestation.schema must be {ATTESTATION_SCHEMA}")
    generation = _require_text(attestation.get("generation"), "gremlin_attestation.generation")
    normalized: dict[str, Any] = {
        "schema": ATTESTATION_SCHEMA,
        "generation": generation,
    }
    for pulse in ("identity", "domain", "authority"):
        receipt = _require_mapping(attestation.get(f"{pulse}_receipt"), f"{pulse}_receipt")
        if receipt.get("generation") != generation:
            raise ValueError(f"{pulse}_receipt generation mismatch")
        if receipt.get("status") not in {"VERIFIED", "ACTIVE", "PASS"}:
            raise ValueError(f"{pulse}_receipt is not verified")
        normalized[f"{pulse}_receipt"] = dict(receipt)
    normalized["attestation_commitment"] = _commit(normalized, ATTESTATION_SCHEMA)
    return normalized


def validate_preflight(
    *,
    action_packet: Mapping[str, Any],
    gate_receipt: str,
    tether_status: str,
    gremlin_attestation: Mapping[str, Any],
    shell_used: bool,
    copy_only: bool,
) -> dict[str, Any]:
    action = _validate_action_packet(_require_mapping(action_packet, "action_packet"))
    gate = _require_text(gate_receipt, "gate_receipt")
    if tether_status != "ACTIVE":
        raise ValueError("tether_status must be ACTIVE")
    if shell_used is not False:
        raise ValueError("shell_used must be false")
    if copy_only is not True:
        raise ValueError("copy_only must be true for this v0.1 capability")
    attestation = _validate_attestation(
        _require_mapping(gremlin_attestation, "gremlin_attestation")
    )
    envelope = {
        "schema": CAPABILITY_SCHEMA,
        "status": "PREFLIGHT_PASS",
        "action_packet_commitment": action["packet_commitment"],
        "gate_receipt": gate,
        "tether_status": "ACTIVE",
        "gremlin_attestation_commitment": attestation["attestation_commitment"],
        "shell_used": False,
        "copy_only": True,
        "production_runtime_write": False,
        "canon_allowed": False,
    }
    envelope["preflight_commitment"] = _commit(envelope, "GREMLIN_VCS_PREFLIGHT_V0_1")
    return envelope


def checkpoint_prepare(
    *,
    preflight: Mapping[str, Any],
    repository: str,
    base_ref: str,
    expected_head: str,
) -> dict[str, Any]:
    if preflight.get("status") != "PREFLIGHT_PASS":
        raise ValueError("preflight must be PREFLIGHT_PASS")
    repo = _require_text(repository, "repository")
    ref = _require_text(base_ref, "base_ref")
    head = _validate_head(expected_head, "expected_head")
    record = {
        "schema": "PHASENAV_VCS_CHECKPOINT_PREPARE_V0_1",
        "repository": repo,
        "base_ref": ref,
        "expected_head": head,
        "preflight_commitment": _require_text(
            preflight.get("preflight_commitment"), "preflight_commitment"
        ),
        "shell_used": False,
        "writes_performed": False,
    }
    record["checkpoint_commitment"] = _commit(record, record["schema"])
    return record


def branch_prepare(
    *,
    checkpoint: Mapping[str, Any],
    branch_name: str,
) -> dict[str, Any]:
    branch = _require_text(branch_name, "branch_name")
    if branch in {"main", "master"}:
        raise ValueError("direct main/master mutation is forbidden")
    if not _BRANCH_RE.fullmatch(branch) or ".." in branch or branch.startswith("/"):
        raise ValueError("branch_name is not a safe bounded ref name")
    record = {
        "schema": "PHASENAV_VCS_BRANCH_PREPARE_V0_1",
        "branch_name": branch,
        "base_head": _validate_head(checkpoint.get("expected_head"), "checkpoint.expected_head"),
        "checkpoint_commitment": _require_text(
            checkpoint.get("checkpoint_commitment"), "checkpoint_commitment"
        ),
        "shell_used": False,
        "writes_performed": False,
    }
    record["branch_commitment"] = _commit(record, record["schema"])
    return record


def writes_prepare(
    *,
    branch: Mapping[str, Any],
    writes: Sequence[Mapping[str, Any]],
    copy_only: bool = True,
) -> dict[str, Any]:
    if copy_only is not True:
        raise ValueError("copy_only must remain true")
    if isinstance(writes, (str, bytes, bytearray)) or not isinstance(writes, Sequence):
        raise ValueError("writes must be a sequence")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(writes):
        entry = _require_mapping(item, f"writes[{index}]")
        operation = _require_text(entry.get("operation", "create"), f"writes[{index}].operation").lower()
        if operation in _FORBIDDEN_OPS or operation != "create":
            raise ValueError("v0.1 COPY_ONLY accepts create operations only")
        path = _require_text(entry.get("path"), f"writes[{index}].path")
        if path.startswith("/") or ".." in path.split("/") or path in seen:
            raise ValueError(f"unsafe or duplicate path: {path}")
        content = entry.get("content")
        if not isinstance(content, str):
            raise ValueError(f"writes[{index}].content must be UTF-8 text")
        seen.add(path)
        normalized.append(
            {
                "operation": "create",
                "path": path,
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content_bytes": len(content.encode("utf-8")),
            }
        )
    if not normalized:
        raise ValueError("at least one write is required")
    record = {
        "schema": "PHASENAV_VCS_WRITES_PREPARE_V0_1",
        "branch_name": _require_text(branch.get("branch_name"), "branch.branch_name"),
        "branch_commitment": _require_text(branch.get("branch_commitment"), "branch_commitment"),
        "copy_only": True,
        "writes": normalized,
        "shell_used": False,
        "writes_performed": False,
    }
    record["writes_commitment"] = _commit(record, record["schema"])
    return record


def commit_prepare(
    *,
    prepared_writes: Mapping[str, Any],
    message: str,
) -> dict[str, Any]:
    record = {
        "schema": "PHASENAV_VCS_COMMIT_PREPARE_V0_1",
        "branch_name": _require_text(prepared_writes.get("branch_name"), "branch_name"),
        "writes_commitment": _require_text(
            prepared_writes.get("writes_commitment"), "writes_commitment"
        ),
        "message": _require_text(message, "message"),
        "shell_used": False,
        "writes_performed": False,
    }
    record["commit_commitment"] = _commit(record, record["schema"])
    return record


def tag_prepare(*, checkpoint: Mapping[str, Any], tag_name: str) -> dict[str, Any]:
    tag = _require_text(tag_name, "tag_name")
    if not _BRANCH_RE.fullmatch(tag) or ".." in tag:
        raise ValueError("tag_name is not a safe bounded ref name")
    record = {
        "schema": "PHASENAV_VCS_TAG_PREPARE_V0_1",
        "tag_name": tag,
        "target_head": _validate_head(checkpoint.get("expected_head"), "expected_head"),
        "checkpoint_commitment": _require_text(
            checkpoint.get("checkpoint_commitment"), "checkpoint_commitment"
        ),
        "shell_used": False,
        "writes_performed": False,
    }
    record["tag_commitment"] = _commit(record, record["schema"])
    return record


def bundle_prepare(
    *,
    checkpoint: Mapping[str, Any],
    tag: Mapping[str, Any],
    branch: Mapping[str, Any],
) -> dict[str, Any]:
    record = {
        "schema": "PHASENAV_VCS_BUNDLE_PREPARE_V0_1",
        "checkpoint_commitment": _require_text(
            checkpoint.get("checkpoint_commitment"), "checkpoint_commitment"
        ),
        "tag_commitment": _require_text(tag.get("tag_commitment"), "tag_commitment"),
        "branch_commitment": _require_text(branch.get("branch_commitment"), "branch_commitment"),
        "shell_used": False,
        "writes_performed": False,
        "native_adapter_evidence_required": True,
    }
    record["bundle_commitment"] = _commit(record, record["schema"])
    return record


def test_receipt_bind(*, logical_step: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    evidence_map = dict(_require_mapping(evidence, "evidence"))
    record = {
        "schema": "PHASENAV_TEST_RECEIPT_BINDING_V0_1",
        "logical_step": _require_text(logical_step, "logical_step"),
        "evidence": evidence_map,
        "evidence_commitment": _commit(evidence_map, "PHASENAV_TEST_EVIDENCE_V0_1"),
    }
    record["test_binding_commitment"] = _commit(record, record["schema"])
    return record


def execution_receipt_build(
    *,
    preflight: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    branch: Mapping[str, Any],
    prepared_writes: Mapping[str, Any],
    prepared_commit: Mapping[str, Any],
    tag: Mapping[str, Any],
    bundle: Mapping[str, Any],
    test_binding: Mapping[str, Any],
    adapter_evidence: Mapping[str, Any],
    before_head: str,
    after_head: str,
) -> dict[str, Any]:
    adapter = dict(_require_mapping(adapter_evidence, "adapter_evidence"))
    if adapter.get("shell_used") is not False:
        raise ValueError("adapter_evidence.shell_used must be false")
    if adapter.get("status") not in {"PASS", "EXECUTED", "VERIFIED"}:
        raise ValueError("adapter_evidence must prove successful native execution")
    receipt = {
        "schema": EXECUTION_RECEIPT_SCHEMA,
        "capability_schema": CAPABILITY_SCHEMA,
        "status": "EXECUTED_NATIVE_ADAPTER_VERIFIED",
        "before_head": _validate_head(before_head, "before_head"),
        "after_head": _validate_head(after_head, "after_head"),
        "preflight_commitment": _require_text(preflight.get("preflight_commitment"), "preflight_commitment"),
        "checkpoint_commitment": _require_text(checkpoint.get("checkpoint_commitment"), "checkpoint_commitment"),
        "branch_commitment": _require_text(branch.get("branch_commitment"), "branch_commitment"),
        "writes_commitment": _require_text(prepared_writes.get("writes_commitment"), "writes_commitment"),
        "commit_commitment": _require_text(prepared_commit.get("commit_commitment"), "commit_commitment"),
        "tag_commitment": _require_text(tag.get("tag_commitment"), "tag_commitment"),
        "bundle_commitment": _require_text(bundle.get("bundle_commitment"), "bundle_commitment"),
        "test_binding_commitment": _require_text(test_binding.get("test_binding_commitment"), "test_binding_commitment"),
        "adapter_evidence_commitment": _commit(adapter, "PHASENAV_NATIVE_ADAPTER_EVIDENCE_V0_1"),
        "shell_used": False,
        "production_runtime_write": False,
        "canon_allowed": False,
    }
    receipt["receipt_commitment"] = _commit(receipt, EXECUTION_RECEIPT_SCHEMA)
    return receipt
