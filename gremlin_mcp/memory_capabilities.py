from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "BESTIARY_MEMORY_CAPABILITY_V0_1"
TOKEN_SCHEMA = "BESTIARY_MEMORY_CAPABILITY_TOKEN_V0_1"
RECEIPT_SCHEMA = "BESTIARY_MEMORY_ACCESS_RECEIPT_V0_1"
TASK_AUTHORIZATION_SCHEMA = "BESTIARY_MEMORY_TASK_AUTHORIZATION_V0_1"
VERSION = "0.1.0"
EPISTEMIC = "CHYBA"
AUTHORITY = "SHARED_COGNITION_ONLY"
AUTHENTICATION = "UNSIGNED_CONTENT_COMMITMENT"

MEMORY_LAYERS = ("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL")
PRIVATE_LAYER = "PRIVATE_SCRATCH"

OPERATIONS = (
    "READ_METADATA",
    "READ_PAYLOAD",
    "QUERY",
    "COMPARE",
    "OBSERVE_APPEND",
    "DERIVE",
    "GRAPH_APPEND",
    "EDGE_APPEND",
    "NODE_LINK",
    "FLAG",
    "ACK",
    "ROUTE",
    "CONSOLIDATE",
    "SUPERSEDE_REQUEST",
    "QUARANTINE_REQUEST",
    "PROMOTE_REQUEST",
    "RETENTION_REQUEST",
    "AUDIT",
    "GOVERNANCE_REVIEW",
)

DESTRUCTIVE_OPERATIONS = ("DELETE", "OVERWRITE", "IN_PLACE_EDIT")

ARTIFACT_TYPES = (
    "RAW_OBSERVATION",
    "OBSERVATION_EVENT",
    "MEMORY_INDEX",
    "SIMILARITY_LINK",
    "RETRIEVAL_TRACE",
    "RELATION_EDGE",
    "GRAPH_SNAPSHOT",
    "DEPENDENCY_LINK",
    "CONTRADICTION",
    "ANOMALY",
    "TEST_TARGET",
    "DERIVATION",
    "LEMMA_CANDIDATE",
    "CAUSAL_CHAIN",
    "AUDIT_RECEIPT",
    "EPISTEMIC_FINDING",
    "ENUMERATION_RESULT",
    "DUPLICATE_FINDING",
    "DEAD_BRANCH_FINDING",
    "SUPERSEDE_PROPOSAL",
    "ROUTE_RECEIPT",
    "DISPATCH_STATE",
    "PATTERN_OBSERVATION",
    "HARMONIC_COMPARISON",
    "HEALTH_ALERT",
    "NOVELTY_OBSERVATION",
    "TRANSFORMED_REPRESENTATION",
    "SYNTHESIS_CANDIDATE",
    "THREAT_MODEL",
    "SEARCH_RECEIPT",
    "AGGREGATE_CANDIDATE",
    "ORCHESTRATION_RECEIPT",
    "RETENTION_PROPOSAL",
    "PROMOTION_PROPOSAL",
    "QUARANTINE_PROPOSAL",
    "GOVERNANCE_DECISION",
)

ALL_ARTIFACTS = "*"


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("memory-capability values must be finite JSON data") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _upper(value: Any, field: str) -> str:
    return _text(value, field).upper()


def _scope_value(value: Any, field: str) -> str:
    text = _text(value, field)
    if text == "*":
        return text
    return text


def _tuple_strings(value: Sequence[str] | str, field: str) -> tuple[str, ...]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        raise ValueError(f"{field} must be a string or sequence")
    out = []
    for item in values:
        text = _upper(item, field)
        if text not in out:
            out.append(text)
    return tuple(sorted(out))


@dataclass(frozen=True)
class CapabilityGrant:
    layers: tuple[str, ...]
    operations: tuple[str, ...]
    artifacts: tuple[str, ...]
    payload_access: bool
    scope_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "layers": list(self.layers),
            "operations": list(self.operations),
            "artifacts": list(self.artifacts),
            "payload_access": self.payload_access,
            "scope_mode": self.scope_mode,
        }


def _grant(
    layers: Sequence[str] | str,
    operations: Sequence[str] | str,
    artifacts: Sequence[str] | str,
    *,
    payload_access: bool = True,
    scope_mode: str = "TASK_SCOPED",
) -> CapabilityGrant:
    normalized_layers = _tuple_strings(layers, "layers")
    for layer in normalized_layers:
        if layer not in MEMORY_LAYERS and layer != PRIVATE_LAYER:
            raise ValueError(f"unknown memory layer: {layer}")
    normalized_operations = _tuple_strings(operations, "operations")
    for operation in normalized_operations:
        if operation not in OPERATIONS:
            raise ValueError(f"unknown memory operation: {operation}")
    normalized_artifacts = _tuple_strings(artifacts, "artifacts")
    for artifact in normalized_artifacts:
        if artifact != ALL_ARTIFACTS and artifact not in ARTIFACT_TYPES:
            raise ValueError(f"unknown artifact type: {artifact}")
    mode = _upper(scope_mode, "scope_mode")
    if mode not in {"TASK_SCOPED", "SUBJECT_SCOPED", "GENERATION_SCOPED", "METADATA_ONLY", "GOVERNANCE_SCOPED"}:
        raise ValueError("unsupported scope_mode")
    return CapabilityGrant(
        layers=normalized_layers,
        operations=normalized_operations,
        artifacts=normalized_artifacts,
        payload_access=bool(payload_access),
        scope_mode=mode,
    )


PRIVATE_SCRATCH_GRANT = _grant(
    PRIVATE_LAYER,
    ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE", "OBSERVE_APPEND", "DERIVE", "FLAG"),
    ALL_ARTIFACTS,
    payload_access=True,
    scope_mode="TASK_SCOPED",
)


POLICY: dict[str, tuple[CapabilityGrant, ...]] = {
    "HUMMINGBIRD": (
        _grant("WORKING", ("READ_METADATA", "READ_PAYLOAD", "OBSERVE_APPEND"), ("RAW_OBSERVATION", "OBSERVATION_EVENT")),
        _grant("EPISODIC", "OBSERVE_APPEND", "OBSERVATION_EVENT"),
    ),
    "OCTOPUS": (
        _grant(MEMORY_LAYERS, ("READ_METADATA", "QUERY", "ROUTE"), ("ROUTE_RECEIPT", "DISPATCH_STATE", ALL_ARTIFACTS), payload_access=False, scope_mode="METADATA_ONLY"),
        _grant(("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL"), "READ_PAYLOAD", ALL_ARTIFACTS, scope_mode="TASK_SCOPED"),
        _grant("RELATIONAL", "DERIVE", ("ROUTE_RECEIPT", "DISPATCH_STATE")),
    ),
    "SPIDER": (
        _grant(("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", ("GRAPH_APPEND", "EDGE_APPEND", "NODE_LINK", "DERIVE"), ("RELATION_EDGE", "GRAPH_SNAPSHOT", "DEPENDENCY_LINK"), scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", "FLAG", ("ANOMALY", "DEPENDENCY_LINK"), scope_mode="SUBJECT_SCOPED"),
        _grant("ARCHIVAL", "READ_METADATA", ALL_ARTIFACTS, payload_access=False, scope_mode="METADATA_ONLY"),
    ),
    "RAVEN": (
        _grant(("EPISODIC", "SEMANTIC"), ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant("SEMANTIC", "DERIVE", ("MEMORY_INDEX", "SIMILARITY_LINK", "RETRIEVAL_TRACE"), scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", ("READ_METADATA", "QUERY"), ("SIMILARITY_LINK", "MEMORY_INDEX", "DEPENDENCY_LINK"), payload_access=False, scope_mode="METADATA_ONLY"),
        _grant("ARCHIVAL", ("READ_METADATA", "QUERY"), ALL_ARTIFACTS, payload_access=False, scope_mode="METADATA_ONLY"),
    ),
    "HOUND": (
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "COMPARE", "QUERY"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL"), ("FLAG", "QUARANTINE_REQUEST"), ("CONTRADICTION", "ANOMALY", "TEST_TARGET", "QUARANTINE_PROPOSAL"), scope_mode="SUBJECT_SCOPED"),
        _grant("ARCHIVAL", "READ_METADATA", ALL_ARTIFACTS, payload_access=False, scope_mode="METADATA_ONLY"),
    ),
    "MOLE": (
        _grant(("SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant(("SEMANTIC", "RELATIONAL"), "DERIVE", ("DERIVATION", "LEMMA_CANDIDATE", "CAUSAL_CHAIN"), scope_mode="SUBJECT_SCOPED"),
    ),
    "OWL": (
        _grant(MEMORY_LAYERS, ("READ_METADATA", "QUERY", "COMPARE", "AUDIT"), ALL_ARTIFACTS, payload_access=False, scope_mode="METADATA_ONLY"),
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL"), "READ_PAYLOAD", ALL_ARTIFACTS, scope_mode="TASK_SCOPED"),
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL"), ("FLAG", "PROMOTE_REQUEST"), ("AUDIT_RECEIPT", "EPISTEMIC_FINDING", "PROMOTION_PROPOSAL"), scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", "DERIVE", ("AUDIT_RECEIPT", "EPISTEMIC_FINDING"), scope_mode="SUBJECT_SCOPED"),
    ),
    "ANT": (
        _grant(("WORKING", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "QUERY", "COMPARE"), ALL_ARTIFACTS, payload_access=False, scope_mode="TASK_SCOPED"),
        _grant("SEMANTIC", "DERIVE", "ENUMERATION_RESULT", scope_mode="TASK_SCOPED"),
    ),
    "MANTIS": (
        _grant(("SEMANTIC", "RELATIONAL"), ("READ_METADATA", "QUERY", "COMPARE"), ALL_ARTIFACTS, payload_access=False, scope_mode="SUBJECT_SCOPED"),
        _grant(("SEMANTIC", "RELATIONAL"), ("FLAG", "SUPERSEDE_REQUEST"), ("DUPLICATE_FINDING", "DEAD_BRANCH_FINDING", "SUPERSEDE_PROPOSAL"), scope_mode="SUBJECT_SCOPED"),
    ),
    "FOX": (
        _grant(("WORKING", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "QUERY"), ALL_ARTIFACTS, scope_mode="TASK_SCOPED"),
        _grant("WORKING", "DERIVE", ("CAUSAL_CHAIN", "ROUTE_RECEIPT"), scope_mode="TASK_SCOPED"),
    ),
    "BEAVER": (
        _grant(("SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "QUERY"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant(("SEMANTIC", "RELATIONAL"), "DERIVE", ("DERIVATION", "CAUSAL_CHAIN", "SYNTHESIS_CANDIDATE"), scope_mode="SUBJECT_SCOPED"),
    ),
    "BAT": (
        _grant(("WORKING", "EPISODIC", "SEMANTIC"), ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant(("EPISODIC", "SEMANTIC"), "DERIVE", ("PATTERN_OBSERVATION", "HARMONIC_COMPARISON"), scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", "READ_METADATA", ("PATTERN_OBSERVATION", "HARMONIC_COMPARISON"), payload_access=False, scope_mode="METADATA_ONLY"),
    ),
    "CANARY": (
        _grant("WORKING", ("READ_METADATA", "QUERY"), ALL_ARTIFACTS, payload_access=False, scope_mode="METADATA_ONLY"),
        _grant(("WORKING", "EPISODIC"), ("FLAG", "QUARANTINE_REQUEST"), ("HEALTH_ALERT", "ANOMALY", "QUARANTINE_PROPOSAL"), scope_mode="TASK_SCOPED"),
    ),
    "SERPENT": (
        _grant("WORKING", ("READ_METADATA", "READ_PAYLOAD", "OBSERVE_APPEND"), ("RAW_OBSERVATION", "NOVELTY_OBSERVATION"), scope_mode="TASK_SCOPED"),
        _grant("EPISODIC", "OBSERVE_APPEND", ("OBSERVATION_EVENT", "NOVELTY_OBSERVATION"), scope_mode="TASK_SCOPED"),
    ),
    "CHAMELEON": (
        _grant(("WORKING", "EPISODIC", "SEMANTIC"), ("READ_METADATA", "READ_PAYLOAD", "QUERY"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant(("WORKING", "EPISODIC", "SEMANTIC"), "DERIVE", "TRANSFORMED_REPRESENTATION", scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", "READ_METADATA", "TRANSFORMED_REPRESENTATION", payload_access=False, scope_mode="METADATA_ONLY"),
    ),
    "BELZEBUB": (
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "READ_PAYLOAD", "QUERY", "COMPARE"), ALL_ARTIFACTS, scope_mode="SUBJECT_SCOPED"),
        _grant("RELATIONAL", ("DERIVE", "FLAG", "QUARANTINE_REQUEST"), ("SYNTHESIS_CANDIDATE", "THREAT_MODEL", "CONTRADICTION", "QUARANTINE_PROPOSAL"), scope_mode="SUBJECT_SCOPED"),
    ),
    "FERRET": (
        _grant(("WORKING", "SEMANTIC", "RELATIONAL"), ("READ_METADATA", "QUERY"), ALL_ARTIFACTS, payload_access=False, scope_mode="TASK_SCOPED"),
        _grant("EPISODIC", "DERIVE", "SEARCH_RECEIPT", scope_mode="TASK_SCOPED"),
    ),
    "GREMLIN": (
        _grant(MEMORY_LAYERS, ("READ_METADATA", "QUERY"), ALL_ARTIFACTS, payload_access=False, scope_mode="TASK_SCOPED"),
        _grant(("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL"), "READ_PAYLOAD", ALL_ARTIFACTS, scope_mode="TASK_SCOPED"),
        _grant("RELATIONAL", ("DERIVE", "ACK", "ROUTE"), ("AGGREGATE_CANDIDATE", "ORCHESTRATION_RECEIPT", "ROUTE_RECEIPT"), scope_mode="TASK_SCOPED"),
        _grant(("SEMANTIC", "RELATIONAL"), ("PROMOTE_REQUEST", "RETENTION_REQUEST"), ("PROMOTION_PROPOSAL", "RETENTION_PROPOSAL"), scope_mode="TASK_SCOPED"),
    ),
    "RAPHAEL": (
        _grant(MEMORY_LAYERS, ("READ_METADATA", "QUERY", "AUDIT", "GOVERNANCE_REVIEW"), ALL_ARTIFACTS, payload_access=False, scope_mode="GOVERNANCE_SCOPED"),
        _grant(("EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL"), "READ_PAYLOAD", ALL_ARTIFACTS, scope_mode="GOVERNANCE_SCOPED"),
        _grant("RELATIONAL", ("DERIVE", "FLAG", "QUARANTINE_REQUEST", "PROMOTE_REQUEST", "RETENTION_REQUEST"), ("GOVERNANCE_DECISION", "AUDIT_RECEIPT", "EPISTEMIC_FINDING", "QUARANTINE_PROPOSAL", "PROMOTION_PROPOSAL", "RETENTION_PROPOSAL"), scope_mode="GOVERNANCE_SCOPED"),
    ),
}


def policy_manifest() -> dict[str, Any]:
    matrix = {
        beast: [grant.to_dict() for grant in grants]
        for beast, grants in sorted(POLICY.items())
    }
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "default": "DENY",
        "memory_layers": list(MEMORY_LAYERS),
        "private_layer": PRIVATE_LAYER,
        "operations": list(OPERATIONS),
        "destructive_operations": list(DESTRUCTIVE_OPERATIONS),
        "artifact_types": list(ARTIFACT_TYPES),
        "policy": matrix,
        "private_scratch_policy": {
            "principals": sorted(POLICY),
            "grant": PRIVATE_SCRATCH_GRANT.to_dict(),
            "synchronized": False,
            "source_of_truth": False,
        },
        "invariants": {
            "delete_allowed": False,
            "overwrite_allowed": False,
            "in_place_edit_allowed": False,
            "edit_semantics": "DERIVE_OR_SUPERSEDE_REQUEST_ONLY",
            "private_scratch_synchronized": False,
            "difference_detection_grants_disclosure": False,
            "capability_implies_identity_authentication": False,
            "spider_graph_write_is_typed": True,
        },
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "policy_sha256": _sha256(core),
    }


def _grant_matches(
    grant: CapabilityGrant,
    *,
    layer: str,
    operation: str,
    artifact_type: str,
) -> bool:
    return (
        layer in grant.layers
        and operation in grant.operations
        and (ALL_ARTIFACTS in grant.artifacts or artifact_type in grant.artifacts)
    )


def matching_grants(
    beast: str,
    *,
    layer: str,
    operation: str,
    artifact_type: str,
) -> tuple[CapabilityGrant, ...]:
    beast_name = _upper(beast, "beast")
    layer_name = _upper(layer, "layer")
    operation_name = _upper(operation, "operation")
    artifact_name = _upper(artifact_type, "artifact_type")
    if operation_name in DESTRUCTIVE_OPERATIONS:
        return ()
    if layer_name not in MEMORY_LAYERS and layer_name != PRIVATE_LAYER:
        return ()
    if operation_name not in OPERATIONS:
        return ()
    if artifact_name not in ARTIFACT_TYPES:
        return ()
    grants = list(POLICY.get(beast_name, ()))
    if beast_name in POLICY:
        grants.append(PRIVATE_SCRATCH_GRANT)
    return tuple(
        grant
        for grant in grants
        if _grant_matches(
            grant,
            layer=layer_name,
            operation=operation_name,
            artifact_type=artifact_name,
        )
    )


def _grant_scope_compatible(
    grant: CapabilityGrant,
    *,
    subject_scope: str,
    generation_scope: str,
    task_scope: str,
) -> bool:
    mode = grant.scope_mode
    if mode == "METADATA_ONLY":
        return True
    if mode == "TASK_SCOPED":
        return task_scope != "*"
    if mode == "SUBJECT_SCOPED":
        return subject_scope != "*" and task_scope != "*"
    if mode == "GENERATION_SCOPED":
        return generation_scope != "*" and task_scope != "*"
    if mode == "GOVERNANCE_SCOPED":
        return task_scope != "*"
    return False


def issue_capability_token(
    *,
    beast: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_scope: str,
    generation_scope: str,
    task_scope: str,
) -> dict[str, Any]:
    beast_name = _upper(beast, "beast")
    layer_name = _upper(layer, "layer")
    operation_name = _upper(operation, "operation")
    artifact_name = _upper(artifact_type, "artifact_type")
    grants = matching_grants(
        beast_name,
        layer=layer_name,
        operation=operation_name,
        artifact_type=artifact_name,
    )
    if not grants:
        raise PermissionError("deny-by-default memory capability policy rejected token request")

    subject = _scope_value(subject_scope, "subject_scope")
    generation = _scope_value(generation_scope, "generation_scope")
    task = _scope_value(task_scope, "task_scope")
    scoped_grants = tuple(
        grant
        for grant in grants
        if _grant_scope_compatible(
            grant,
            subject_scope=subject,
            generation_scope=generation,
            task_scope=task,
        )
    )
    if not scoped_grants:
        raise PermissionError("requested scope is broader than the matched capability grant")
    payload_access = operation_name == "READ_PAYLOAD"
    if payload_access and not any(grant.payload_access for grant in scoped_grants):
        raise PermissionError("matched capability grants do not permit payload access")
    core = {
        "schema": TOKEN_SCHEMA,
        "version": VERSION,
        "beast": beast_name,
        "layer": layer_name,
        "operation": operation_name,
        "artifact_type": artifact_name,
        "subject_scope": subject,
        "generation_scope": generation,
        "task_scope": task,
        "policy_sha256": policy_manifest()["policy_sha256"],
        "payload_access": payload_access,
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "token_id": "bmc:" + _sha256(core),
        "claims": {
            "identity_authenticated": False,
            "delete_authority": False,
            "overwrite_authority": False,
            "in_place_edit_authority": False,
            "capability_is_scope_bound": True,
        },
    }


def validate_capability_token(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("capability token must be a mapping")
    row = dict(packet)
    if row.get("schema") != TOKEN_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported memory capability token")
    beast = _upper(row.get("beast"), "beast")
    layer = _upper(row.get("layer"), "layer")
    operation = _upper(row.get("operation"), "operation")
    artifact_type = _upper(row.get("artifact_type"), "artifact_type")
    subject = _scope_value(row.get("subject_scope"), "subject_scope")
    generation = _scope_value(row.get("generation_scope"), "generation_scope")
    task = _scope_value(row.get("task_scope"), "task_scope")
    if row.get("policy_sha256") != policy_manifest()["policy_sha256"]:
        raise ValueError("capability token policy commitment mismatch")
    grants = matching_grants(
        beast,
        layer=layer,
        operation=operation,
        artifact_type=artifact_type,
    )
    if not grants:
        raise PermissionError("capability token no longer matches deny-by-default policy")
    payload_access = operation == "READ_PAYLOAD"
    if row.get("payload_access") is not payload_access:
        raise ValueError("capability token payload_access mismatch")
    scoped_grants = tuple(
        grant
        for grant in grants
        if _grant_scope_compatible(
            grant,
            subject_scope=subject,
            generation_scope=generation,
            task_scope=task,
        )
    )
    if not scoped_grants:
        raise PermissionError("capability token scope is broader than current policy")
    if payload_access and not any(grant.payload_access for grant in scoped_grants):
        raise PermissionError("capability token requests payload access beyond policy")
    if row.get("authentication") != AUTHENTICATION:
        raise ValueError("capability authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("capability epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("capability token must remain canon_allowed=false")
    core = {
        "schema": TOKEN_SCHEMA,
        "version": VERSION,
        "beast": beast,
        "layer": layer,
        "operation": operation,
        "artifact_type": artifact_type,
        "subject_scope": subject,
        "generation_scope": generation,
        "task_scope": task,
        "policy_sha256": policy_manifest()["policy_sha256"],
        "payload_access": payload_access,
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    token_id = "bmc:" + _sha256(core)
    if row.get("token_id") != token_id:
        raise ValueError("capability token commitment mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("capability claims must be a mapping")
    if claims.get("capability_is_scope_bound") is not True:
        raise ValueError("capability token must remain scope-bound")
    for key in ("identity_authenticated", "delete_authority", "overwrite_authority", "in_place_edit_authority"):
        if claims.get(key) is not False:
            raise ValueError(f"capability claim must remain false: {key}")
    return {**core, "token_id": token_id, "claims": dict(claims)}


def _scope_matches(scope: str, actual: str) -> bool:
    return scope == "*" or scope == actual


def evaluate_access(
    *,
    beast: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_id: str,
    generation_id: str,
    task_id: str,
    token: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    beast_name = _upper(beast, "beast")
    layer_name = _upper(layer, "layer")
    operation_name = _upper(operation, "operation")
    artifact_name = _upper(artifact_type, "artifact_type")
    subject = _text(subject_id, "subject_id")
    generation = _text(generation_id, "generation_id")
    task = _text(task_id, "task_id")

    reason = "NO_MATCHING_GRANT"
    allowed = False
    token_id = None

    if operation_name in DESTRUCTIVE_OPERATIONS:
        reason = "DESTRUCTIVE_OPERATION_FORBIDDEN"
    else:
        grants = matching_grants(
            beast_name,
            layer=layer_name,
            operation=operation_name,
            artifact_type=artifact_name,
        )
        if grants:
            if token is None:
                reason = "SCOPED_TOKEN_REQUIRED"
            else:
                validated = validate_capability_token(token)
                token_id = validated["token_id"]
                if validated["beast"] != beast_name:
                    reason = "TOKEN_BEAST_MISMATCH"
                elif validated["layer"] != layer_name:
                    reason = "TOKEN_LAYER_MISMATCH"
                elif validated["operation"] != operation_name:
                    reason = "TOKEN_OPERATION_MISMATCH"
                elif validated["artifact_type"] != artifact_name:
                    reason = "TOKEN_ARTIFACT_MISMATCH"
                elif not _scope_matches(validated["subject_scope"], subject):
                    reason = "TOKEN_SUBJECT_SCOPE_MISMATCH"
                elif not _scope_matches(validated["generation_scope"], generation):
                    reason = "TOKEN_GENERATION_SCOPE_MISMATCH"
                elif not _scope_matches(validated["task_scope"], task):
                    reason = "TOKEN_TASK_SCOPE_MISMATCH"
                else:
                    allowed = True
                    reason = "POLICY_AND_SCOPE_MATCH"

    core = {
        "schema": RECEIPT_SCHEMA,
        "version": VERSION,
        "decision": "ALLOW" if allowed else "DENY",
        "reason_code": reason,
        "beast": beast_name,
        "layer": layer_name,
        "operation": operation_name,
        "artifact_type": artifact_name,
        "subject_id": subject,
        "generation_id": generation,
        "task_id": task,
        "token_id": token_id,
        "policy_sha256": policy_manifest()["policy_sha256"],
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "receipt_id": "bmr:" + _sha256(core),
        "claims": {
            "deny_by_default": True,
            "decision_is_auditable": True,
            "difference_detection_grants_disclosure": False,
            "identity_authenticated": False,
            "delete_authority": False,
            "overwrite_authority": False,
            "in_place_edit_authority": False,
        },
    }


def validate_access_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("memory access receipt must be a mapping")
    row = dict(packet)
    if row.get("schema") != RECEIPT_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported memory access receipt")
    decision = _upper(row.get("decision"), "decision")
    if decision not in {"ALLOW", "DENY"}:
        raise ValueError("unsupported memory access decision")
    reason = _text(row.get("reason_code"), "reason_code")
    beast = _upper(row.get("beast"), "beast")
    layer = _upper(row.get("layer"), "layer")
    operation = _upper(row.get("operation"), "operation")
    artifact_type = _upper(row.get("artifact_type"), "artifact_type")
    subject = _text(row.get("subject_id"), "subject_id")
    generation = _text(row.get("generation_id"), "generation_id")
    task = _text(row.get("task_id"), "task_id")
    token_id = row.get("token_id")
    if token_id is not None:
        token_id = _text(token_id, "token_id")
        if not token_id.startswith("bmc:") or len(token_id) != 68:
            raise ValueError("invalid capability token_id in receipt")
        try:
            int(token_id[4:], 16)
        except ValueError as exc:
            raise ValueError("capability token_id must be hexadecimal") from exc
    if row.get("policy_sha256") != policy_manifest()["policy_sha256"]:
        raise ValueError("receipt policy commitment mismatch")
    if row.get("authentication") != AUTHENTICATION:
        raise ValueError("receipt authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("receipt epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("receipt must remain canon_allowed=false")
    core = {
        "schema": RECEIPT_SCHEMA,
        "version": VERSION,
        "decision": decision,
        "reason_code": reason,
        "beast": beast,
        "layer": layer,
        "operation": operation,
        "artifact_type": artifact_type,
        "subject_id": subject,
        "generation_id": generation,
        "task_id": task,
        "token_id": token_id,
        "policy_sha256": policy_manifest()["policy_sha256"],
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    receipt_id = "bmr:" + _sha256(core)
    if row.get("receipt_id") != receipt_id:
        raise ValueError("memory access receipt commitment mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("memory access receipt claims must be a mapping")
    if claims.get("deny_by_default") is not True:
        raise ValueError("receipt must preserve deny-by-default claim")
    if claims.get("decision_is_auditable") is not True:
        raise ValueError("receipt must preserve auditable-decision claim")
    if claims.get("difference_detection_grants_disclosure") is not False:
        raise ValueError("receipt cannot grant disclosure from difference detection")
    for key in ("identity_authenticated", "delete_authority", "overwrite_authority", "in_place_edit_authority"):
        if claims.get(key) is not False:
            raise ValueError(f"memory access receipt claim must remain false: {key}")
    return {**core, "receipt_id": receipt_id, "claims": dict(claims)}


def authorize_memory_requests(
    beast: str,
    requests: Sequence[Mapping[str, Any]],
    *,
    task_id: str,
) -> dict[str, Any]:
    """Issue exact task-scoped tokens for one beast or fail the whole authorization."""
    beast_name = _upper(beast, "beast")
    task = _text(task_id, "task_id")
    if isinstance(requests, (str, bytes)) or not isinstance(requests, Sequence):
        raise ValueError("memory requests must be a sequence of mappings")

    tokens: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    normalized_requests: list[dict[str, str]] = []
    for index, raw in enumerate(requests):
        if not isinstance(raw, Mapping):
            raise ValueError(f"memory request {index} must be a mapping")
        layer = _upper(raw.get("layer"), f"memory request {index}.layer")
        operation = _upper(raw.get("operation"), f"memory request {index}.operation")
        artifact_type = _upper(raw.get("artifact_type"), f"memory request {index}.artifact_type")
        subject = _text(raw.get("subject_id"), f"memory request {index}.subject_id")
        generation = _text(raw.get("generation_id"), f"memory request {index}.generation_id")
        token = issue_capability_token(
            beast=beast_name,
            layer=layer,
            operation=operation,
            artifact_type=artifact_type,
            subject_scope=subject,
            generation_scope=generation,
            task_scope=task,
        )
        receipt = evaluate_access(
            beast=beast_name,
            layer=layer,
            operation=operation,
            artifact_type=artifact_type,
            subject_id=subject,
            generation_id=generation,
            task_id=task,
            token=token,
        )
        if receipt["decision"] != "ALLOW":
            raise PermissionError(
                f"memory authorization failed: {receipt['reason_code']} "
                f"receipt={receipt['receipt_id']}"
            )
        validate_access_receipt(receipt)
        normalized_requests.append(
            {
                "layer": layer,
                "operation": operation,
                "artifact_type": artifact_type,
                "subject_id": subject,
                "generation_id": generation,
            }
        )
        tokens.append(token)
        receipts.append(receipt)

    core = {
        "schema": TASK_AUTHORIZATION_SCHEMA,
        "version": VERSION,
        "beast": beast_name,
        "task_id": task,
        "requests": normalized_requests,
        "token_ids": [token["token_id"] for token in tokens],
        "receipt_ids": [receipt["receipt_id"] for receipt in receipts],
        "policy_sha256": policy_manifest()["policy_sha256"],
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {
        **core,
        "authorization_id": "bma:" + _sha256(core),
        "tokens": tokens,
        "receipts": receipts,
        "claims": {
            "all_requests_allowed": True,
            "task_scope_exact": True,
            "identity_authenticated": False,
            "delete_authority": False,
            "overwrite_authority": False,
        },
    }


def validate_task_authorization_bundle(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one task authorization against the current policy snapshot."""
    if not isinstance(packet, Mapping):
        raise ValueError("task memory authorization must be a mapping")
    row = dict(packet)
    if row.get("schema") != TASK_AUTHORIZATION_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported task memory authorization")
    beast = _upper(row.get("beast"), "beast")
    task = _text(row.get("task_id"), "task_id")
    if row.get("policy_sha256") != policy_manifest()["policy_sha256"]:
        raise ValueError("task authorization policy commitment is stale or mismatched")
    if row.get("authentication") != AUTHENTICATION:
        raise ValueError("task authorization authentication boundary mismatch")
    if row.get("epistemic") != EPISTEMIC or row.get("authority") != AUTHORITY:
        raise ValueError("task authorization epistemic/authority mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("task authorization must remain canon_allowed=false")

    raw_requests = row.get("requests")
    raw_tokens = row.get("tokens")
    raw_receipts = row.get("receipts")
    raw_token_ids = row.get("token_ids")
    raw_receipt_ids = row.get("receipt_ids")
    if not isinstance(raw_requests, Sequence) or isinstance(raw_requests, (str, bytes)):
        raise ValueError("task authorization requests must be a sequence")
    if not isinstance(raw_tokens, Sequence) or isinstance(raw_tokens, (str, bytes)):
        raise ValueError("task authorization tokens must be a sequence")
    if not isinstance(raw_receipts, Sequence) or isinstance(raw_receipts, (str, bytes)):
        raise ValueError("task authorization receipts must be a sequence")
    if not isinstance(raw_token_ids, Sequence) or isinstance(raw_token_ids, (str, bytes)):
        raise ValueError("task authorization token_ids must be a sequence")
    if not isinstance(raw_receipt_ids, Sequence) or isinstance(raw_receipt_ids, (str, bytes)):
        raise ValueError("task authorization receipt_ids must be a sequence")
    if not (
        len(raw_requests)
        == len(raw_tokens)
        == len(raw_receipts)
        == len(raw_token_ids)
        == len(raw_receipt_ids)
    ):
        raise ValueError("task authorization request/token/receipt cardinality mismatch")

    requests: list[dict[str, str]] = []
    tokens: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    token_ids: list[str] = []
    receipt_ids: list[str] = []
    for index, (request_raw, token_raw, receipt_raw) in enumerate(
        zip(raw_requests, raw_tokens, raw_receipts)
    ):
        if not isinstance(request_raw, Mapping):
            raise ValueError(f"task authorization request {index} must be a mapping")
        request = {
            "layer": _upper(request_raw.get("layer"), f"request {index}.layer"),
            "operation": _upper(request_raw.get("operation"), f"request {index}.operation"),
            "artifact_type": _upper(
                request_raw.get("artifact_type"),
                f"request {index}.artifact_type",
            ),
            "subject_id": _text(request_raw.get("subject_id"), f"request {index}.subject_id"),
            "generation_id": _text(
                request_raw.get("generation_id"),
                f"request {index}.generation_id",
            ),
        }
        token = validate_capability_token(token_raw)
        receipt = validate_access_receipt(receipt_raw)
        if token["beast"] != beast or receipt["beast"] != beast:
            raise ValueError("task authorization beast binding mismatch")
        if token["task_scope"] != task or receipt["task_id"] != task:
            raise ValueError("task authorization task binding mismatch")
        if (
            token["layer"] != request["layer"]
            or token["operation"] != request["operation"]
            or token["artifact_type"] != request["artifact_type"]
            or not _scope_matches(token["subject_scope"], request["subject_id"])
            or not _scope_matches(token["generation_scope"], request["generation_id"])
        ):
            raise ValueError("task authorization token/request binding mismatch")
        if (
            receipt["layer"] != request["layer"]
            or receipt["operation"] != request["operation"]
            or receipt["artifact_type"] != request["artifact_type"]
            or receipt["subject_id"] != request["subject_id"]
            or receipt["generation_id"] != request["generation_id"]
            or receipt["token_id"] != token["token_id"]
            or receipt["decision"] != "ALLOW"
            or receipt["reason_code"] != "POLICY_AND_SCOPE_MATCH"
        ):
            raise ValueError("task authorization receipt/request binding mismatch")
        requests.append(request)
        tokens.append(token)
        receipts.append(receipt)
        token_ids.append(token["token_id"])
        receipt_ids.append(receipt["receipt_id"])

    if list(raw_token_ids) != token_ids:
        raise ValueError("task authorization token_ids mismatch")
    if list(raw_receipt_ids) != receipt_ids:
        raise ValueError("task authorization receipt_ids mismatch")

    core = {
        "schema": TASK_AUTHORIZATION_SCHEMA,
        "version": VERSION,
        "beast": beast,
        "task_id": task,
        "requests": requests,
        "token_ids": token_ids,
        "receipt_ids": receipt_ids,
        "policy_sha256": policy_manifest()["policy_sha256"],
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    authorization_id = "bma:" + _sha256(core)
    if row.get("authorization_id") != authorization_id:
        raise ValueError("task authorization commitment mismatch")
    claims = row.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("task authorization claims must be a mapping")
    if claims.get("all_requests_allowed") is not True:
        raise ValueError("task authorization must preserve all_requests_allowed")
    if claims.get("task_scope_exact") is not True:
        raise ValueError("task authorization must preserve exact task scope")
    for key in ("identity_authenticated", "delete_authority", "overwrite_authority"):
        if claims.get(key) is not False:
            raise ValueError(f"task authorization claim must remain false: {key}")
    return {
        **core,
        "authorization_id": authorization_id,
        "tokens": tokens,
        "receipts": receipts,
        "claims": dict(claims),
    }


def require_access(**kwargs: Any) -> dict[str, Any]:
    receipt = evaluate_access(**kwargs)
    if receipt["decision"] != "ALLOW":
        raise PermissionError(
            f"memory capability denied: {receipt['reason_code']} "
            f"receipt={receipt['receipt_id']}"
        )
    return receipt


def beast_capabilities(beast: str) -> dict[str, Any]:
    name = _upper(beast, "beast")
    grants = POLICY.get(name)
    if grants is None:
        raise ValueError(f"unknown Bestiary memory principal: {name}")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "beast": name,
        "grants": [grant.to_dict() for grant in grants],
        "private_scratch_grant": PRIVATE_SCRATCH_GRANT.to_dict(),
        "policy_sha256": policy_manifest()["policy_sha256"],
        "default": "DENY",
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }


__all__ = [
    "ARTIFACT_TYPES",
    "AUTHENTICATION",
    "AUTHORITY",
    "DESTRUCTIVE_OPERATIONS",
    "EPISTEMIC",
    "MEMORY_LAYERS",
    "OPERATIONS",
    "POLICY",
    "PRIVATE_LAYER",
    "PRIVATE_SCRATCH_GRANT",
    "RECEIPT_SCHEMA",
    "SCHEMA",
    "TASK_AUTHORIZATION_SCHEMA",
    "TOKEN_SCHEMA",
    "VERSION",
    "authorize_memory_requests",
    "beast_capabilities",
    "evaluate_access",
    "issue_capability_token",
    "matching_grants",
    "policy_manifest",
    "require_access",
    "validate_access_receipt",
    "validate_capability_token",
    "validate_task_authorization_bundle",
]
