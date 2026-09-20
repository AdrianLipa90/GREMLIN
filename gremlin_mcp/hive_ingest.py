from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, TYPE_CHECKING

from .memory_capabilities import issue_capability_token, require_access

if TYPE_CHECKING:
    from .hive_authority import HiveAuthorityRuntime
    from .orbital_hive_memory import HiveRecord

SCHEMA = "GREMLIN_HIVE_RESEARCH_INGEST_V0_3"
VERSION = "0.3.0"
TWO_PI = 2.0 * math.pi
PHASE_BASIS = "COMMITMENT_REFERENCE_PHASE_NOT_PHYSICAL"

MEMORY_LAYER = "RELATIONAL"

_RELATIONAL_PROJECTIONS: dict[str, tuple[str, str]] = {
    "GREMLIN": ("DERIVE", "ORCHESTRATION_RECEIPT"),
    "SPIDER": ("DERIVE", "GRAPH_SNAPSHOT"),
    "MOLE": ("DERIVE", "DERIVATION"),
    "OWL": ("DERIVE", "EPISTEMIC_FINDING"),
    "BELZEBUB": ("DERIVE", "SYNTHESIS_CANDIDATE"),
}
_NON_RELATIONAL_RESEARCH_SPECIES = frozenset({"RAVEN", "ANT"})
_KNOWN_RESEARCH_SPECIES = frozenset(
    {
        "SPIDER",
        "RAVEN",
        "HOUND",
        "MOLE",
        "OWL",
        "ANT",
        "MANTIS",
        "BELZEBUB",
    }
)


_OPERATIONAL_PRIORITY = {
    "EXECUTION": 0.88,
    "HOUND": 0.95,
    "OWL": 0.90,
    "BELZEBUB": 0.85,
    "SPIDER": 0.80,
    "MOLE": 0.75,
    "GENERIC": 0.70,
}


def commitment_phase(value: str) -> float:
    """Map a stable commitment to [0, 2pi) for deterministic addressing only."""
    text = str(value).strip()
    if not text:
        raise ValueError("commitment must be non-empty")
    raw = hashlib.blake2b(
        text.encode("utf-8"), digest_size=8, person=b"GRMLN-HIVE-PH3"
    ).digest()
    fraction = int.from_bytes(raw, "big") / float(1 << 64)
    return TWO_PI * fraction


def observation_priority(species: str, candidate: Mapping[str, Any] | None = None) -> float:
    """Deterministic operational priority used only for Hive orbit placement."""
    name = str(species).strip().upper() or "GENERIC"
    base = _OPERATIONAL_PRIORITY.get(name, _OPERATIONAL_PRIORITY["GENERIC"])
    row = dict(candidate or {})
    if row.get("contradictions"):
        base += 0.04
    if row.get("provider_errors"):
        base += 0.02
    return min(1.0, base)


def _projection_profile(
    species: str,
    candidate: Mapping[str, Any] | None = None,
) -> tuple[str, str] | None:
    name = str(species).strip().upper()
    if name in _NON_RELATIONAL_RESEARCH_SPECIES:
        return None
    if name == "HOUND":
        row = dict(candidate or {})
        return ("FLAG", "CONTRADICTION" if row.get("contradictions") else "ANOMALY")
    if name == "MANTIS":
        row = dict(candidate or {})
        if row.get("dead_branches") or row.get("dead_branch_findings"):
            return ("FLAG", "DEAD_BRANCH_FINDING")
        return ("FLAG", "DUPLICATE_FINDING")
    return _RELATIONAL_PROJECTIONS.get(name)


def _authorize_projection(
    *,
    species: str,
    subject_id: str,
    generation_id: str,
    task_id: str,
    candidate: Mapping[str, Any] | None = None,
) -> tuple[str, str, dict[str, Any]] | None:
    name = str(species).strip().upper()
    profile = _projection_profile(name, candidate)
    if profile is None:
        if name in _NON_RELATIONAL_RESEARCH_SPECIES:
            return None
        raise ValueError(f"unknown or untyped research species for Hive projection: {name!r}")
    operation, artifact_type = profile
    token = issue_capability_token(
        beast=name,
        layer=MEMORY_LAYER,
        operation=operation,
        artifact_type=artifact_type,
        subject_scope=subject_id,
        generation_scope=generation_id,
        task_scope=task_id,
    )
    receipt = require_access(
        beast=name,
        layer=MEMORY_LAYER,
        operation=operation,
        artifact_type=artifact_type,
        subject_id=subject_id,
        generation_id=generation_id,
        task_id=task_id,
        token=token,
    )
    return operation, artifact_type, receipt


def _with_memory_authorization(
    payload: Mapping[str, Any],
    *,
    operation: str,
    artifact_type: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(payload),
        "memory_layer": MEMORY_LAYER,
        "memory_operation": operation,
        "memory_artifact_type": artifact_type,
        "memory_capability_receipt": dict(receipt),
    }


def _preflight_projection(execution: Mapping[str, Any], execution_commitment: str) -> None:
    """Validate every Bestiary projection before the first Hive mutation."""
    root_subject = f"research:{execution_commitment}:execution"
    _authorize_projection(
        species="GREMLIN",
        subject_id=root_subject,
        generation_id=execution_commitment,
        task_id=f"execution:{execution_commitment}",
        candidate=execution,
    )
    for stage in execution.get("stage_executions", []):
        for item in stage.get("results", []):
            species = str(item.get("species") or "GENERIC").strip().upper()
            task_id = str(item.get("task_id") or "task").strip()
            result_commitment = str(item.get("result_commitment") or "").strip()
            if not result_commitment:
                raise ValueError("specialist result missing result_commitment")
            candidate = dict(item.get("candidate") or {})
            subject = f"research:{execution_commitment}:specialist:{task_id}"
            _authorize_projection(
                species=species,
                subject_id=subject,
                generation_id=execution_commitment,
                task_id=task_id,
                candidate=candidate,
            )
    synthesis = execution.get("synthesis")
    if synthesis:
        synthesis_row = dict(synthesis)
        synthesis_commitment = str(synthesis_row.get("result_commitment") or "").strip()
        if synthesis_commitment:
            _authorize_projection(
                species="BELZEBUB",
                subject_id=f"research:{execution_commitment}:synthesis",
                generation_id=execution_commitment,
                task_id=f"synthesis:{execution_commitment}",
                candidate=dict(synthesis_row.get("result") or {}),
            )


def _place_once(
    runtime: "HiveAuthorityRuntime",
    *,
    subject_id: str,
    payload: Mapping[str, Any],
    priority: float,
    semantic_key: str,
    relation_phase: float,
    provenance: tuple[str, ...],
    dependencies: tuple[str, ...],
) -> tuple["HiveRecord", bool]:
    return runtime.place_idempotent(
        subject_id=subject_id,
        payload=payload,
        priority=priority,
        semantic_key=semantic_key,
        relation_phase=relation_phase,
        provenance=provenance,
        dependencies=dependencies,
    )


def ingest_research_execution(
    runtime: "HiveAuthorityRuntime",
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one GREMLIN research execution into append-only Hive observations.

    The ingest is intentionally non-promoting: it never sets closure gates and never
    calls latch(). Every record remains OPEN/CANDIDATE shared cognition until another
    component explicitly verifies the closure conditions.
    """
    execution = dict(result)
    execution_commitment = str(execution.get("execution_commitment") or "").strip()
    if not execution_commitment:
        raise ValueError("research result must contain execution_commitment")

    _preflight_projection(execution, execution_commitment)

    root_subject = f"research:{execution_commitment}:execution"
    root_dependencies = tuple(
        sorted(
            {
                str(row.get("content_commitment"))
                for row in execution.get("citations", [])
                if row.get("content_commitment")
            }
        )
    )
    root_authorization = _authorize_projection(
        species="GREMLIN",
        subject_id=root_subject,
        generation_id=execution_commitment,
        task_id=f"execution:{execution_commitment}",
        candidate=execution,
    )
    if root_authorization is None:
        raise RuntimeError("GREMLIN root projection unexpectedly lacks RELATIONAL authority")
    root_operation, root_artifact, root_receipt = root_authorization
    root_payload = _with_memory_authorization(
        {
            "kind": "RESEARCH_EXECUTION",
            "query": execution.get("query"),
            "status": execution.get("status"),
            "mode": execution.get("mode"),
            "execution_commitment": execution_commitment,
            "source_count": len(execution.get("citations", [])),
            "phase_basis": PHASE_BASIS,
            "authority": "SHARED_COGNITION_ONLY",
        },
        operation=root_operation,
        artifact_type=root_artifact,
        receipt=root_receipt,
    )
    root_record, root_created = _place_once(
        runtime,
        subject_id=root_subject,
        payload=root_payload,
        priority=observation_priority("EXECUTION"),
        semantic_key="research/execution",
        relation_phase=commitment_phase(execution_commitment),
        provenance=(
            f"execution:{execution_commitment}",
            f"memory-receipt:{root_receipt['receipt_id']}",
        ),
        dependencies=root_dependencies,
    )

    rows: list[dict[str, Any]] = [
        {
            "kind": "EXECUTION",
            "subject_id": root_subject,
            "record_id": root_record.record_id,
            "created": root_created,
            "state": root_record.state,
            "projection_status": "PROJECTED",
            "memory_operation": root_operation,
            "memory_artifact_type": root_artifact,
            "memory_receipt_id": root_receipt["receipt_id"],
        }
    ]
    specialist_commitments: list[str] = []

    for stage in execution.get("stage_executions", []):
        stage_id = str(stage.get("stage_id") or "stage")
        route_commitment = str(stage.get("route_commitment") or "").strip()
        for item in stage.get("results", []):
            species = str(item.get("species") or "GENERIC").strip().upper()
            task_id = str(item.get("task_id") or "task").strip()
            result_commitment = str(item.get("result_commitment") or "").strip()
            task_commitment = str(item.get("task_commitment") or "").strip()
            if not result_commitment:
                raise ValueError("specialist result missing result_commitment")
            specialist_commitments.append(result_commitment)
            candidate = dict(item.get("candidate") or {})
            subject = f"research:{execution_commitment}:specialist:{task_id}"
            dependencies = tuple(
                value
                for value in (
                    f"execution:{execution_commitment}",
                    f"route:{route_commitment}" if route_commitment else "",
                    f"task:{task_commitment}" if task_commitment else "",
                )
                if value
            )
            authorization = _authorize_projection(
                species=species,
                subject_id=subject,
                generation_id=execution_commitment,
                task_id=task_id,
                candidate=candidate,
            )
            if authorization is None:
                rows.append(
                    {
                        "kind": "SPECIALIST",
                        "species": species,
                        "subject_id": subject,
                        "record_id": None,
                        "created": None,
                        "state": None,
                        "projection_status": "NOT_AUTHORIZED_FOR_RELATIONAL_HIVE",
                        "memory_layer": MEMORY_LAYER,
                    }
                )
                continue
            operation, artifact_type, memory_receipt = authorization
            payload = _with_memory_authorization(
                {
                    "kind": "SPECIALIST_CANDIDATE",
                    "species": species,
                    "stage_id": stage_id,
                    "task_id": task_id,
                    "candidate": candidate,
                    "result_commitment": result_commitment,
                    "phase_basis": PHASE_BASIS,
                    "authority": "SHARED_COGNITION_ONLY",
                },
                operation=operation,
                artifact_type=artifact_type,
                receipt=memory_receipt,
            )
            record, created = _place_once(
                runtime,
                subject_id=subject,
                payload=payload,
                priority=observation_priority(species, candidate),
                semantic_key=f"research/species/{species}",
                relation_phase=commitment_phase(result_commitment),
                provenance=(
                    f"execution:{execution_commitment}",
                    f"result:{result_commitment}",
                    f"memory-receipt:{memory_receipt['receipt_id']}",
                    *(tuple([f"task:{task_commitment}"]) if task_commitment else ()),
                ),
                dependencies=dependencies,
            )
            rows.append(
                {
                    "kind": "SPECIALIST",
                    "species": species,
                    "subject_id": subject,
                    "record_id": record.record_id,
                    "created": created,
                    "state": record.state,
                    "projection_status": "PROJECTED",
                    "memory_operation": operation,
                    "memory_artifact_type": artifact_type,
                    "memory_receipt_id": memory_receipt["receipt_id"],
                }
            )

    synthesis = execution.get("synthesis")
    if synthesis:
        synthesis_row = dict(synthesis)
        synthesis_commitment = str(synthesis_row.get("result_commitment") or "").strip()
        if synthesis_commitment:
            synthesis_payload = dict(synthesis_row.get("result") or {})
            subject = f"research:{execution_commitment}:synthesis"
            synthesis_authorization = _authorize_projection(
                species="BELZEBUB",
                subject_id=subject,
                generation_id=execution_commitment,
                task_id=f"synthesis:{execution_commitment}",
                candidate=synthesis_payload,
            )
            if synthesis_authorization is None:
                raise RuntimeError("BELZEBUB synthesis unexpectedly lacks RELATIONAL authority")
            synthesis_operation, synthesis_artifact, synthesis_receipt = synthesis_authorization
            payload = _with_memory_authorization(
                {
                    "kind": "SYNTHESIS_CANDIDATE",
                    "species": "BELZEBUB",
                    "candidate": synthesis_payload,
                    "result_commitment": synthesis_commitment,
                    "phase_basis": PHASE_BASIS,
                    "authority": "SHARED_COGNITION_ONLY",
                },
                operation=synthesis_operation,
                artifact_type=synthesis_artifact,
                receipt=synthesis_receipt,
            )
            record, created = _place_once(
                runtime,
                subject_id=subject,
                payload=payload,
                priority=observation_priority("BELZEBUB", synthesis_payload),
                semantic_key="research/species/BELZEBUB",
                relation_phase=commitment_phase(synthesis_commitment),
                provenance=(
                    f"execution:{execution_commitment}",
                    f"result:{synthesis_commitment}",
                    f"memory-receipt:{synthesis_receipt['receipt_id']}",
                ),
                dependencies=tuple(f"result:{value}" for value in specialist_commitments),
            )
            rows.append(
                {
                    "kind": "SYNTHESIS",
                    "species": "BELZEBUB",
                    "subject_id": subject,
                    "record_id": record.record_id,
                    "created": created,
                    "state": record.state,
                    "projection_status": "PROJECTED",
                    "memory_operation": synthesis_operation,
                    "memory_artifact_type": synthesis_artifact,
                    "memory_receipt_id": synthesis_receipt["receipt_id"],
                }
            )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "execution_commitment": execution_commitment,
        "phase_basis": PHASE_BASIS,
        "authority": "SHARED_COGNITION_ONLY",
        "automatic_latch": False,
        "projection_policy": "BESTIARY_MEMORY_CAPABILITY_V0_1",
        "records": rows,
        "created_count": sum(1 for row in rows if row.get("created") is True),
        "existing_count": sum(
            1
            for row in rows
            if row.get("projection_status") == "PROJECTED"
            and row.get("created") is False
        ),
        "skipped_relational_projection_count": sum(
            1
            for row in rows
            if row.get("projection_status") == "NOT_AUTHORIZED_FOR_RELATIONAL_HIVE"
        ),
    }


__all__ = [
    "PHASE_BASIS",
    "SCHEMA",
    "VERSION",
    "commitment_phase",
    "ingest_research_execution",
    "observation_priority",
]
