from __future__ import annotations

from dataclasses import asdict
import hashlib
import math
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from .hive_authority import HiveAuthorityRuntime
    from .orbital_hive_memory import HiveRecord

SCHEMA = "GREMLIN_HIVE_RESEARCH_INGEST_V0_3"
VERSION = "0.3.0"
TWO_PI = 2.0 * math.pi
PHASE_BASIS = "COMMITMENT_REFERENCE_PHASE_NOT_PHYSICAL"

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


def _phase_equal(left: float, right: float, *, tol: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tol


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
    try:
        current = runtime.head(subject_id)
    except (KeyError, RuntimeError):
        current = None
    if current is not None:
        if (
            dict(current.payload) == dict(payload)
            and current.semantic_key == semantic_key
            and abs(float(current.priority) - float(priority)) <= 1e-12
            and _phase_equal(current.coordinate.relation_phase, relation_phase)
        ):
            return current, False
        raise RuntimeError(
            "same Hive research subject already exists with different content; "
            "refuse implicit overwrite"
        )
    record = runtime.place(
        subject_id=subject_id,
        payload=dict(payload),
        priority=priority,
        semantic_key=semantic_key,
        relation_phase=relation_phase,
        provenance=provenance,
        dependencies=dependencies,
    )
    return record, True


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
    root_payload = {
        "kind": "RESEARCH_EXECUTION",
        "query": execution.get("query"),
        "status": execution.get("status"),
        "mode": execution.get("mode"),
        "execution_commitment": execution_commitment,
        "source_count": len(execution.get("citations", [])),
        "phase_basis": PHASE_BASIS,
        "authority": "SHARED_COGNITION_ONLY",
    }
    root_record, root_created = _place_once(
        runtime,
        subject_id=root_subject,
        payload=root_payload,
        priority=observation_priority("EXECUTION"),
        semantic_key="research/execution",
        relation_phase=commitment_phase(execution_commitment),
        provenance=(f"execution:{execution_commitment}",),
        dependencies=root_dependencies,
    )

    rows: list[dict[str, Any]] = [
        {
            "kind": "EXECUTION",
            "subject_id": root_subject,
            "record_id": root_record.record_id,
            "created": root_created,
            "state": root_record.state,
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
            payload = {
                "kind": "SPECIALIST_CANDIDATE",
                "species": species,
                "stage_id": stage_id,
                "task_id": task_id,
                "candidate": candidate,
                "result_commitment": result_commitment,
                "phase_basis": PHASE_BASIS,
                "authority": "SHARED_COGNITION_ONLY",
            }
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
                }
            )

    synthesis = execution.get("synthesis")
    if synthesis:
        synthesis_row = dict(synthesis)
        synthesis_commitment = str(synthesis_row.get("result_commitment") or "").strip()
        if synthesis_commitment:
            synthesis_payload = dict(synthesis_row.get("result") or {})
            subject = f"research:{execution_commitment}:synthesis"
            payload = {
                "kind": "SYNTHESIS_CANDIDATE",
                "species": "BELZEBUB",
                "candidate": synthesis_payload,
                "result_commitment": synthesis_commitment,
                "phase_basis": PHASE_BASIS,
                "authority": "SHARED_COGNITION_ONLY",
            }
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
                }
            )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "execution_commitment": execution_commitment,
        "phase_basis": PHASE_BASIS,
        "authority": "SHARED_COGNITION_ONLY",
        "automatic_latch": False,
        "records": rows,
        "created_count": sum(1 for row in rows if row["created"]),
        "existing_count": sum(1 for row in rows if not row["created"]),
    }


__all__ = [
    "PHASE_BASIS",
    "SCHEMA",
    "VERSION",
    "commitment_phase",
    "ingest_research_execution",
    "observation_priority",
]
