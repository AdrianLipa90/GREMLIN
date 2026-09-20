from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_BESTIARY_MEMORY_CAPABILITY_V0_1"
VERSION = "0.1.0"
TOKEN_SCHEMA = "GREMLIN_MEMORY_SCOPE_TOKEN_V0_1"
REQUEST_SCHEMA = "GREMLIN_MEMORY_ACCESS_REQUEST_V0_1"
RECEIPT_SCHEMA = "GREMLIN_MEMORY_ACCESS_RECEIPT_V0_1"
AUTHENTICATION = "UNSIGNED_CONTENT_COMMITMENT"
EPISTEMIC = "CHYBA"
AUTHORITY = "SHARED_COGNITION_ONLY"
DEFAULT_POLICY = "DENY"

SHARED_LAYERS = ("WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL")
PRIVATE_LAYER = "PRIVATE_SCRATCH"
ALL_LAYERS = (PRIVATE_LAYER, *SHARED_LAYERS)

FORBIDDEN_MEMORY_OPERATIONS = frozenset({
    "DELETE",
    "OVERWRITE",
    "EDIT_IN_PLACE",
    "TRUNCATE",
    "PURGE",
})

VISIBILITY_ORDER = {
    "NONE": 0,
    "COMMITMENT": 1,
    "FEATURE_VIEW": 2,
    "METADATA": 3,
    "FULL": 4,
}

READLIKE_OPERATIONS = frozenset({"READ", "QUERY", "COMPARE", "AUDIT"})

BESTIARY_PRINCIPALS = (
    "HUMMINGBIRD",
    "OCTOPUS",
    "SPIDER",
    "RAVEN",
    "HOUND",
    "MOLE",
    "OWL",
    "ANT",
    "MANTIS",
    "FOX",
    "BEAVER",
    "BAT",
    "CANARY",
    "SERPENT",
    "CHAMELEON",
    "BELZEBUB",
    "FERRET",
    "GREMLIN",
)
GOVERNANCE_PRINCIPALS = ("RAPHAEL",)
ALL_PRINCIPALS = (*BESTIARY_PRINCIPALS, *GOVERNANCE_PRINCIPALS)


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
        raise ValueError("memory capability values must be finite JSON data") from exc


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


def _strings(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be a sequence")
    out = tuple(sorted({_text(item, field) for item in value}))
    if not allow_empty and not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _upper_strings(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    return tuple(item.upper() for item in _strings(value, field, allow_empty=allow_empty))


def _rule(
    rule_id: str,
    *,
    layer: str,
    operations: Sequence[str],
    artifacts: Sequence[str],
    visibility: str,
    scope_mode: str = "TASK_SCOPED",
) -> dict[str, Any]:
    layer_u = _upper(layer, "layer")
    if layer_u not in ALL_LAYERS:
        raise ValueError(f"unsupported layer: {layer_u}")
    visibility_u = _upper(visibility, "visibility")
    if visibility_u not in VISIBILITY_ORDER:
        raise ValueError(f"unsupported visibility: {visibility_u}")
    return {
        "rule_id": _text(rule_id, "rule_id"),
        "layer": layer_u,
        "operations": sorted({_upper(op, "operation") for op in operations}),
        "artifact_types": sorted({_upper(artifact, "artifact_type") for artifact in artifacts}),
        "visibility": visibility_u,
        "scope_mode": _upper(scope_mode, "scope_mode"),
    }


PRIVATE_SCRATCH_PROFILE = {
    "layer": PRIVATE_LAYER,
    "source_of_truth": False,
    "synchronized": False,
    "shared": False,
    "append_only_export_boundary": True,
    "operations": ["READ", "QUERY", "COMPARE", "DERIVE"],
    "note": "Local scratch may be overwritten internally; only exported shared-memory artifacts enter append-only policy.",
}


POLICY: dict[str, tuple[dict[str, Any], ...]] = {
    "HUMMINGBIRD": (
        _rule("HUM-WORK-READ", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("HUM-WORK-CAPTURE", layer="WORKING", operations=["OBSERVE_APPEND"], artifacts=["RAW_CAPTURE", "TASK_CAPTURE"], visibility="NONE"),
        _rule("HUM-EPI-CAPTURE", layer="EPISODIC", operations=["OBSERVE_APPEND"], artifacts=["OBSERVATION_EVENT"], visibility="NONE"),
    ),
    "OCTOPUS": (
        _rule("OCT-WORK-META", layer="WORKING", operations=["READ", "QUERY", "ROUTE"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("OCT-EPI-META", layer="EPISODIC", operations=["READ", "QUERY", "ROUTE"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("OCT-SEM-META", layer="SEMANTIC", operations=["READ", "QUERY", "ROUTE"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("OCT-REL-META", layer="RELATIONAL", operations=["READ", "QUERY", "ROUTE"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("OCT-REL-ROUTE", layer="RELATIONAL", operations=["ROUTE_APPEND"], artifacts=["ROUTE_RECEIPT", "DISPATCH_STATE"], visibility="NONE"),
    ),
    "SPIDER": (
        _rule("SPI-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("SPI-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("SPI-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("SPI-REL-GRAPH", layer="RELATIONAL", operations=["GRAPH_APPEND"], artifacts=["RELATION_EDGE", "GRAPH_SNAPSHOT", "DEPENDENCY_LINK", "ISOMORPHISM_LINK"], visibility="NONE"),
    ),
    "RAVEN": (
        _rule("RAV-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("RAV-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("RAV-SEM-INDEX", layer="SEMANTIC", operations=["INDEX_APPEND"], artifacts=["MEMORY_INDEX", "SIMILARITY_LINK", "RETRIEVAL_TRACE"], visibility="NONE"),
        _rule("RAV-ARC-LOOKUP", layer="ARCHIVAL", operations=["QUERY", "READ"], artifacts=["*"], visibility="METADATA"),
    ),
    "HOUND": (
        _rule("HOU-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("HOU-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("HOU-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("HOU-REL-FLAG", layer="RELATIONAL", operations=["FLAG_APPEND"], artifacts=["CONTRADICTION", "ANOMALY", "TEST_TARGET"], visibility="NONE"),
        _rule("HOU-REL-QUAR", layer="RELATIONAL", operations=["QUARANTINE_REQUEST"], artifacts=["QUARANTINE_REQUEST"], visibility="NONE"),
    ),
    "MOLE": (
        _rule("MOL-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("MOL-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("MOL-SEM-DERIVE", layer="SEMANTIC", operations=["DERIVATION_APPEND"], artifacts=["DERIVATION", "LEMMA_CANDIDATE", "CAUSAL_CHAIN"], visibility="NONE"),
        _rule("MOL-REL-DERIVE", layer="RELATIONAL", operations=["DERIVATION_APPEND"], artifacts=["DERIVATION", "LEMMA_CANDIDATE", "CAUSAL_CHAIN"], visibility="NONE"),
    ),
    "OWL": (
        _rule("OWL-EPI-AUDIT", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE", "AUDIT"], artifacts=["*"], visibility="FULL"),
        _rule("OWL-SEM-AUDIT", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE", "AUDIT"], artifacts=["*"], visibility="FULL"),
        _rule("OWL-REL-AUDIT", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE", "AUDIT"], artifacts=["*"], visibility="FULL"),
        _rule("OWL-ARC-AUDIT", layer="ARCHIVAL", operations=["READ", "QUERY", "AUDIT"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("OWL-REL-FINDING", layer="RELATIONAL", operations=["AUDIT_APPEND", "FLAG_APPEND"], artifacts=["AUDIT_RECEIPT", "EPISTEMIC_FINDING"], visibility="NONE"),
        _rule("OWL-REL-PROMOTE", layer="RELATIONAL", operations=["PROMOTE_REQUEST"], artifacts=["PROMOTION_REVIEW"], visibility="NONE"),
    ),
    "ANT": (
        _rule("ANT-WORK-READ", layer="WORKING", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FEATURE_VIEW"),
        _rule("ANT-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FEATURE_VIEW"),
        _rule("ANT-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FEATURE_VIEW"),
        _rule("ANT-SEM-ENUM", layer="SEMANTIC", operations=["ENUMERATION_APPEND"], artifacts=["ENUMERATION_RESULT", "COVERAGE_REPORT"], visibility="NONE"),
    ),
    "MANTIS": (
        _rule("MAN-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("MAN-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("MAN-REL-FLAG", layer="RELATIONAL", operations=["FLAG_APPEND"], artifacts=["DUPLICATE_FLAG", "DEAD_BRANCH_FLAG"], visibility="NONE"),
        _rule("MAN-REL-SUPERSEDE", layer="RELATIONAL", operations=["SUPERSEDE_REQUEST"], artifacts=["SUPERSEDE_REQUEST"], visibility="NONE"),
    ),
    "FOX": (
        _rule("FOX-WORK-READ", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("FOX-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("FOX-WORK-PLAN", layer="WORKING", operations=["PLAN_APPEND"], artifacts=["PLAN_CANDIDATE", "DECOMPOSITION"], visibility="NONE"),
        _rule("FOX-SEM-PLAN", layer="SEMANTIC", operations=["PLAN_APPEND"], artifacts=["PLAN_CANDIDATE", "DECOMPOSITION"], visibility="NONE"),
    ),
    "BEAVER": (
        _rule("BEA-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("BEA-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("BEA-SEM-BUILD", layer="SEMANTIC", operations=["PROTOTYPE_APPEND"], artifacts=["PROTOTYPE", "CONSTRUCTION_CANDIDATE"], visibility="NONE"),
        _rule("BEA-REL-BUILD", layer="RELATIONAL", operations=["PROTOTYPE_APPEND"], artifacts=["PROTOTYPE", "CONSTRUCTION_CANDIDATE"], visibility="NONE"),
    ),
    "BAT": (
        _rule("BAT-WORK-READ", layer="WORKING", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BAT-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BAT-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BAT-SEM-PATTERN", layer="SEMANTIC", operations=["PATTERN_APPEND"], artifacts=["PHASE_PATTERN", "WEAK_SIGNAL_PATTERN"], visibility="NONE"),
    ),
    "CANARY": (
        _rule("CAN-WORK-META", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="METADATA", scope_mode="GLOBAL_METADATA"),
        _rule("CAN-EPI-ALERT", layer="EPISODIC", operations=["ALERT_APPEND"], artifacts=["RUNTIME_ALERT", "DRIFT_ALERT"], visibility="NONE"),
        _rule("CAN-REL-QUAR", layer="RELATIONAL", operations=["QUARANTINE_REQUEST"], artifacts=["QUARANTINE_REQUEST"], visibility="NONE"),
    ),
    "SERPENT": (
        _rule("SER-WORK-READ", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("SER-WORK-OBSERVE", layer="WORKING", operations=["OBSERVE_APPEND"], artifacts=["NOVELTY_OBSERVATION", "LATENT_FIELD_OBSERVATION"], visibility="NONE"),
        _rule("SER-EPI-OBSERVE", layer="EPISODIC", operations=["OBSERVE_APPEND"], artifacts=["NOVELTY_OBSERVATION", "LATENT_FIELD_OBSERVATION"], visibility="NONE"),
    ),
    "CHAMELEON": (
        _rule("CHA-WORK-READ", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("CHA-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("CHA-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("CHA-WORK-XFORM", layer="WORKING", operations=["TRANSFORM_APPEND"], artifacts=["REPRESENTATION_TRANSFORM", "PROFILE_TRANSFORM"], visibility="NONE"),
        _rule("CHA-EPI-XFORM", layer="EPISODIC", operations=["TRANSFORM_APPEND"], artifacts=["REPRESENTATION_TRANSFORM", "PROFILE_TRANSFORM"], visibility="NONE"),
        _rule("CHA-SEM-XFORM", layer="SEMANTIC", operations=["TRANSFORM_APPEND"], artifacts=["REPRESENTATION_TRANSFORM", "PROFILE_TRANSFORM"], visibility="NONE"),
    ),
    "BELZEBUB": (
        _rule("BEL-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BEL-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BEL-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("BEL-REL-SYNTH", layer="RELATIONAL", operations=["SYNTHESIS_APPEND"], artifacts=["SYNTHESIS_CANDIDATE", "DEFENSIVE_THREAT_MODEL"], visibility="NONE"),
        _rule("BEL-REL-FLAG", layer="RELATIONAL", operations=["FLAG_APPEND", "QUARANTINE_REQUEST"], artifacts=["THREAT_FLAG", "QUARANTINE_REQUEST"], visibility="NONE"),
    ),
    "FERRET": (
        _rule("FER-WORK-META", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="METADATA", scope_mode="EXPLICIT_GRANT"),
        _rule("FER-REL-META", layer="RELATIONAL", operations=["READ", "QUERY"], artifacts=["*"], visibility="METADATA", scope_mode="EXPLICIT_GRANT"),
        _rule("FER-REL-RECEIPT", layer="RELATIONAL", operations=["ACTUATION_RECEIPT_APPEND"], artifacts=["ACTUATION_RECEIPT"], visibility="NONE", scope_mode="EXPLICIT_GRANT"),
    ),
    "GREMLIN": (
        _rule("GRE-WORK-READ", layer="WORKING", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("GRE-EPI-READ", layer="EPISODIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("GRE-SEM-READ", layer="SEMANTIC", operations=["READ", "QUERY"], artifacts=["*"], visibility="FULL"),
        _rule("GRE-REL-READ", layer="RELATIONAL", operations=["READ", "QUERY", "COMPARE"], artifacts=["*"], visibility="FULL"),
        _rule("GRE-ARC-READ", layer="ARCHIVAL", operations=["READ", "QUERY"], artifacts=["*"], visibility="METADATA"),
        _rule("GRE-REL-AGG", layer="RELATIONAL", operations=["AGGREGATE_APPEND"], artifacts=["AGGREGATE_CANDIDATE", "ORCHESTRATION_RECEIPT"], visibility="NONE"),
        _rule("GRE-REL-ACK", layer="RELATIONAL", operations=["ACK"], artifacts=["EXCHANGE_ACK"], visibility="NONE"),
        _rule("GRE-REL-PROMOTE", layer="RELATIONAL", operations=["PROMOTE_REQUEST", "RETENTION_REQUEST"], artifacts=["PROMOTION_REQUEST", "RETENTION_REQUEST"], visibility="NONE"),
    ),
    "RAPHAEL": (
        _rule("RAP-WORK-GOV", layer="WORKING", operations=["READ", "QUERY", "AUDIT"], artifacts=["*"], visibility="METADATA", scope_mode="GOVERNANCE_METADATA"),
        _rule("RAP-EPI-GOV", layer="EPISODIC", operations=["READ", "QUERY", "AUDIT"], artifacts=["*"], visibility="METADATA", scope_mode="GOVERNANCE_METADATA"),
        _rule("RAP-SEM-GOV", layer="SEMANTIC", operations=["READ", "QUERY", "AUDIT"], artifacts=["*"], visibility="METADATA", scope_mode="GOVERNANCE_METADATA"),
        _rule("RAP-REL-GOV", layer="RELATIONAL", operations=["READ", "QUERY", "AUDIT", "COMPARE"], artifacts=["*"], visibility="METADATA", scope_mode="GOVERNANCE_METADATA"),
        _rule("RAP-ARC-GOV", layer="ARCHIVAL", operations=["READ", "QUERY", "AUDIT"], artifacts=["*"], visibility="METADATA", scope_mode="GOVERNANCE_METADATA"),
        _rule("RAP-REL-DECREE", layer="RELATIONAL", operations=["GOVERNANCE_APPEND", "QUARANTINE_REQUEST", "PROMOTE_REQUEST"], artifacts=["ADMISSION_DECREE", "MEMORY_GOVERNANCE_RECEIPT", "QUARANTINE_DECREE", "PROMOTION_DECREE"], visibility="NONE", scope_mode="GOVERNANCE"),
        _rule("RAP-ARC-RECEIPT", layer="ARCHIVAL", operations=["GOVERNANCE_APPEND"], artifacts=["MEMORY_GOVERNANCE_RECEIPT"], visibility="NONE", scope_mode="GOVERNANCE"),
    ),
}


def _validate_policy_static() -> None:
    if set(POLICY) != set(ALL_PRINCIPALS):
        raise RuntimeError("memory capability policy must cover every Bestiary principal and RAPHAEL")
    seen_ids: set[str] = set()
    for principal, rules in POLICY.items():
        if not rules:
            raise RuntimeError(f"{principal} has no memory capability rules")
        for rule in rules:
            rule_id = rule["rule_id"]
            if rule_id in seen_ids:
                raise RuntimeError(f"duplicate memory capability rule_id: {rule_id}")
            seen_ids.add(rule_id)
            forbidden = set(rule["operations"]) & FORBIDDEN_MEMORY_OPERATIONS
            if forbidden:
                raise RuntimeError(f"policy attempted forbidden memory operations: {sorted(forbidden)}")
            write_like = [
                operation
                for operation in rule["operations"]
                if operation.endswith("_APPEND") or operation.endswith("_REQUEST") or operation == "ACK"
            ]
            if write_like and rule["artifact_types"] == ["*"]:
                raise RuntimeError(f"write-like rule must use typed artifacts: {rule_id}")


_validate_policy_static()


def principal_profile(principal: str) -> dict[str, Any]:
    name = _upper(principal, "principal")
    if name not in POLICY:
        raise ValueError(f"unknown memory-capability principal: {name}")
    rules = [dict(rule) for rule in POLICY[name]]
    return {
        "principal": name,
        "class": "ANGELIC_FUNCTION" if name == "RAPHAEL" else "BESTIARY_SPECIES",
        "private_scratch": dict(PRIVATE_SCRATCH_PROFILE),
        "rules": rules,
        "default_policy": DEFAULT_POLICY,
        "forbidden_memory_operations": sorted(FORBIDDEN_MEMORY_OPERATIONS),
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }


def memory_capability_manifest() -> dict[str, Any]:
    principals = {name: principal_profile(name) for name in ALL_PRINCIPALS}
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "default_policy": DEFAULT_POLICY,
        "layers": list(ALL_LAYERS),
        "shared_layers": list(SHARED_LAYERS),
        "private_scratch": dict(PRIVATE_SCRATCH_PROFILE),
        "forbidden_memory_operations": sorted(FORBIDDEN_MEMORY_OPERATIONS),
        "principals": principals,
        "invariants": [
            "DENY_BY_DEFAULT",
            "NO_SHARED_MEMORY_DELETE",
            "NO_SHARED_MEMORY_OVERWRITE",
            "NO_EDIT_IN_PLACE",
            "WRITE_REQUIRES_TYPED_ARTIFACT",
            "READ_SCOPE_PRECEDES_RETRIEVAL",
            "COMPARE_DOES_NOT_IMPLY_FULL_READ",
            "FLAG_DOES_NOT_IMPLY_QUARANTINE",
            "SUPERSEDE_REQUEST_DOES_NOT_DELETE_SOURCE",
            "RETENTION_TIER_DOES_NOT_GRANT_DELETION",
            "PRIVATE_SCRATCH_NOT_SOURCE_OF_TRUTH",
            "EVERY_ACCESS_DECISION_EMITS_RECEIPT",
        ],
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "canon_allowed": False,
    }
    return {**core, "manifest_sha256": _sha256(core)}


def build_scope_token(
    *,
    principal: str,
    task_id: str,
    subject_ids: Sequence[str],
    generation_ids: Sequence[str],
    operations: Sequence[str],
    artifact_types: Sequence[str],
    dependency_ids: Sequence[str] = (),
    governance: bool = False,
) -> dict[str, Any]:
    name = _upper(principal, "principal")
    if name not in POLICY:
        raise ValueError(f"unknown principal: {name}")
    core = {
        "schema": TOKEN_SCHEMA,
        "version": VERSION,
        "principal": name,
        "task_id": _text(task_id, "task_id"),
        "subject_ids": list(_strings(subject_ids, "subject_ids")),
        "generation_ids": list(_strings(generation_ids, "generation_ids")),
        "operations": list(_upper_strings(operations, "operations")),
        "artifact_types": list(_upper_strings(artifact_types, "artifact_types")),
        "dependency_ids": list(_strings(dependency_ids, "dependency_ids", allow_empty=True)),
        "governance": bool(governance),
        "authentication": AUTHENTICATION,
        "grant_authority": False,
        "mutation_authority": False,
        "delete_authority": False,
        "overwrite_authority": False,
        "canon_allowed": False,
    }
    return {**core, "token_sha256": _sha256(core)}


def validate_scope_token(token: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(token, Mapping):
        raise ValueError("scope token must be a mapping")
    row = dict(token)
    if row.get("schema") != TOKEN_SCHEMA or row.get("version") != VERSION:
        raise ValueError("unsupported scope token")
    principal = _upper(row.get("principal"), "principal")
    if principal not in POLICY:
        raise ValueError("unknown scope-token principal")
    core = {
        "schema": TOKEN_SCHEMA,
        "version": VERSION,
        "principal": principal,
        "task_id": _text(row.get("task_id"), "task_id"),
        "subject_ids": list(_strings(row.get("subject_ids"), "subject_ids")),
        "generation_ids": list(_strings(row.get("generation_ids"), "generation_ids")),
        "operations": list(_upper_strings(row.get("operations"), "operations")),
        "artifact_types": list(_upper_strings(row.get("artifact_types"), "artifact_types")),
        "dependency_ids": list(_strings(row.get("dependency_ids", ()), "dependency_ids", allow_empty=True)),
        "governance": bool(row.get("governance")),
        "authentication": AUTHENTICATION,
        "grant_authority": False,
        "mutation_authority": False,
        "delete_authority": False,
        "overwrite_authority": False,
        "canon_allowed": False,
    }
    for field in (
        "authentication",
        "grant_authority",
        "mutation_authority",
        "delete_authority",
        "overwrite_authority",
        "canon_allowed",
    ):
        if row.get(field) != core[field]:
            raise ValueError(f"scope token authority boundary mismatch: {field}")
    expected = _sha256(core)
    if row.get("token_sha256") != expected:
        raise ValueError("scope token commitment mismatch")
    return {**core, "token_sha256": expected}


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason_code: str
    rule_id: str | None
    visibility: str


def _scope_contains(values: Sequence[str], requested: str) -> bool:
    return "*" in values or requested in values


def _find_rule(
    principal: str,
    *,
    layer: str,
    operation: str,
    artifact_type: str,
) -> dict[str, Any] | None:
    for rule in POLICY[principal]:
        if rule["layer"] != layer:
            continue
        if operation not in rule["operations"]:
            continue
        if "*" not in rule["artifact_types"] and artifact_type not in rule["artifact_types"]:
            continue
        return rule
    return None


def _decide(
    *,
    principal: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_id: str,
    generation_id: str,
    requested_visibility: str,
    token: Mapping[str, Any] | None,
) -> AccessDecision:
    if operation in FORBIDDEN_MEMORY_OPERATIONS:
        return AccessDecision(False, "GLOBAL_DESTRUCTIVE_MEMORY_OPERATION_DENIED", None, "NONE")

    if layer == PRIVATE_LAYER:
        if operation in PRIVATE_SCRATCH_PROFILE["operations"]:
            return AccessDecision(True, "PRIVATE_SCRATCH_LOCAL_ONLY", "PRIVATE_SCRATCH_LOCAL", "FULL")
        return AccessDecision(False, "PRIVATE_SCRATCH_OPERATION_DENIED", None, "NONE")

    rule = _find_rule(
        principal,
        layer=layer,
        operation=operation,
        artifact_type=artifact_type,
    )
    if rule is None:
        return AccessDecision(False, "NO_MATCHING_TYPED_CAPABILITY_RULE", None, "NONE")

    if token is None:
        return AccessDecision(False, "SHARED_MEMORY_SCOPE_TOKEN_REQUIRED", rule["rule_id"], "NONE")
    try:
        normalized = validate_scope_token(token)
    except ValueError:
        return AccessDecision(False, "INVALID_SCOPE_TOKEN", rule["rule_id"], "NONE")
    if normalized["principal"] != principal:
        return AccessDecision(False, "SCOPE_TOKEN_PRINCIPAL_MISMATCH", rule["rule_id"], "NONE")
    if operation not in normalized["operations"]:
        return AccessDecision(False, "OPERATION_OUTSIDE_SCOPE_TOKEN", rule["rule_id"], "NONE")
    if "*" not in normalized["artifact_types"] and artifact_type not in normalized["artifact_types"]:
        return AccessDecision(False, "ARTIFACT_OUTSIDE_SCOPE_TOKEN", rule["rule_id"], "NONE")

    scope_mode = rule["scope_mode"]
    if scope_mode in {"TASK_SCOPED", "EXPLICIT_GRANT"}:
        if not _scope_contains(normalized["subject_ids"], subject_id):
            return AccessDecision(False, "SUBJECT_OUTSIDE_SCOPE_TOKEN", rule["rule_id"], "NONE")
        if not _scope_contains(normalized["generation_ids"], generation_id):
            return AccessDecision(False, "GENERATION_OUTSIDE_SCOPE_TOKEN", rule["rule_id"], "NONE")
        if "*" in normalized["subject_ids"] or "*" in normalized["generation_ids"]:
            return AccessDecision(False, "WILDCARD_FORBIDDEN_FOR_PAYLOAD_SCOPE", rule["rule_id"], "NONE")
    elif scope_mode == "GLOBAL_METADATA":
        if requested_visibility not in {"NONE", "COMMITMENT", "FEATURE_VIEW", "METADATA"}:
            return AccessDecision(False, "GLOBAL_SCOPE_LIMITED_TO_METADATA", rule["rule_id"], "NONE")
    elif scope_mode in {"GOVERNANCE", "GOVERNANCE_METADATA"}:
        if principal != "RAPHAEL" or normalized["governance"] is not True:
            return AccessDecision(False, "GOVERNANCE_SCOPE_REQUIRED", rule["rule_id"], "NONE")
        if scope_mode == "GOVERNANCE_METADATA" and requested_visibility == "FULL":
            return AccessDecision(False, "GOVERNANCE_READ_LIMITED_TO_METADATA", rule["rule_id"], "NONE")
    else:
        return AccessDecision(False, "UNKNOWN_POLICY_SCOPE_MODE", rule["rule_id"], "NONE")

    max_visibility = rule["visibility"]
    if operation in READLIKE_OPERATIONS:
        if requested_visibility not in VISIBILITY_ORDER:
            return AccessDecision(False, "UNSUPPORTED_REQUESTED_VISIBILITY", rule["rule_id"], "NONE")
        if VISIBILITY_ORDER[requested_visibility] > VISIBILITY_ORDER[max_visibility]:
            return AccessDecision(False, "REQUESTED_VISIBILITY_EXCEEDS_RULE", rule["rule_id"], max_visibility)
    return AccessDecision(True, "ALLOW_TYPED_CAPABILITY", rule["rule_id"], max_visibility)


def evaluate_memory_access(
    *,
    principal: str,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_id: str,
    generation_id: str,
    requested_visibility: str = "NONE",
    token: Mapping[str, Any] | None = None,
    dependency_id: str | None = None,
) -> dict[str, Any]:
    name = _upper(principal, "principal")
    if name not in POLICY:
        raise ValueError(f"unknown memory-capability principal: {name}")
    layer_u = _upper(layer, "layer")
    if layer_u not in ALL_LAYERS:
        raise ValueError(f"unknown memory layer: {layer_u}")
    operation_u = _upper(operation, "operation")
    artifact_u = _upper(artifact_type, "artifact_type")
    subject = _text(subject_id, "subject_id")
    generation = _text(generation_id, "generation_id")
    visibility = _upper(requested_visibility, "requested_visibility")
    dependency = None if dependency_id is None else _text(dependency_id, "dependency_id")

    request_core = {
        "schema": REQUEST_SCHEMA,
        "version": VERSION,
        "principal": name,
        "layer": layer_u,
        "operation": operation_u,
        "artifact_type": artifact_u,
        "subject_id": subject,
        "generation_id": generation,
        "requested_visibility": visibility,
        "dependency_id": dependency,
        "token_sha256": None if token is None else token.get("token_sha256"),
    }
    request_sha = _sha256(request_core)
    decision = _decide(
        principal=name,
        layer=layer_u,
        operation=operation_u,
        artifact_type=artifact_u,
        subject_id=subject,
        generation_id=generation,
        requested_visibility=visibility,
        token=token,
    )

    if decision.allowed and dependency is not None and token is not None:
        normalized = validate_scope_token(token)
        dependencies = normalized["dependency_ids"]
        if dependencies and "*" not in dependencies and dependency not in dependencies:
            decision = AccessDecision(
                False,
                "DEPENDENCY_OUTSIDE_SCOPE_TOKEN",
                decision.rule_id,
                "NONE",
            )

    receipt_core = {
        "schema": RECEIPT_SCHEMA,
        "version": VERSION,
        "request_sha256": request_sha,
        "decision": "ALLOW" if decision.allowed else "DENY",
        "reason_code": decision.reason_code,
        "principal": name,
        "rule_id": decision.rule_id,
        "layer": layer_u,
        "operation": operation_u,
        "artifact_type": artifact_u,
        "subject_id": subject,
        "generation_id": generation,
        "visibility": decision.visibility,
        "dependency_id": dependency,
        "token_sha256": None if token is None else token.get("token_sha256"),
        "default_policy": DEFAULT_POLICY,
        "authentication": AUTHENTICATION,
        "epistemic": EPISTEMIC,
        "authority": AUTHORITY,
        "mutation_authority": False,
        "delete_authority": False,
        "overwrite_authority": False,
        "canon_allowed": False,
    }
    return {
        **receipt_core,
        "receipt_sha256": _sha256(receipt_core),
    }


def require_memory_access(**kwargs: Any) -> dict[str, Any]:
    receipt = evaluate_memory_access(**kwargs)
    if receipt["decision"] != "ALLOW":
        raise PermissionError(
            f"GREMLIN memory access denied: {receipt['reason_code']} "
            f"(principal={receipt['principal']}, layer={receipt['layer']}, "
            f"operation={receipt['operation']}, artifact={receipt['artifact_type']})"
        )
    return receipt


__all__ = [
    "ALL_LAYERS",
    "ALL_PRINCIPALS",
    "AUTHENTICATION",
    "BESTIARY_PRINCIPALS",
    "DEFAULT_POLICY",
    "FORBIDDEN_MEMORY_OPERATIONS",
    "GOVERNANCE_PRINCIPALS",
    "PRIVATE_LAYER",
    "PRIVATE_SCRATCH_PROFILE",
    "POLICY",
    "RECEIPT_SCHEMA",
    "SCHEMA",
    "SHARED_LAYERS",
    "TOKEN_SCHEMA",
    "VERSION",
    "build_scope_token",
    "evaluate_memory_access",
    "memory_capability_manifest",
    "principal_profile",
    "require_memory_access",
    "validate_scope_token",
]
