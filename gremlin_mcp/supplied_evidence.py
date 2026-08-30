from __future__ import annotations

from typing import Any, Iterable, Mapping

from .relational_research import enrich_research_with_case_frames
from .research_executor import (
    EXECUTOR_SCHEMA,
    EXECUTOR_VERSION,
    _authority,
    _belzebub,
    _commit,
    _prepare_sources,
    _run_species,
)

SCHEMA = "GREMLIN_SUPPLIED_EVIDENCE_RESEARCH_V0_1"
VERSION = "0.1.0"
DEFAULT_ROLES = ("OWL", "SPIDER", "MOLE", "HOUND")


def _normalized_roles(roles: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for raw in roles:
        role = str(raw).strip().upper()
        if not role:
            continue
        if role == "BELZEBUB":
            raise ValueError("BELZEBUB is reserved for synthesis")
        if role not in out:
            out.append(role)
    if not out:
        raise ValueError("roles must contain at least one specialist")
    return tuple(out)


def execute_supplied_evidence_research(
    query: str,
    evidence_rows: Iterable[Mapping[str, Any]],
    *,
    relation_text: str | None = None,
    language: str = "pl",
    roles: Iterable[str] = DEFAULT_ROLES,
    max_sources: int = 12,
    provider_errors: Iterable[str] = (),
) -> dict[str, Any]:
    """Run GREMLIN bestiary deterministically over caller-supplied evidence.

    This is an additive offline acquisition lane for reproducible benchmarks and
    pre-collected evidence bundles. It exercises the native OWL/SPIDER/MOLE/HOUND
    candidate handlers plus BELZEBUB synthesis, then applies the existing
    relational case-frame enrichment. Supplied evidence remains candidate-only and
    grants no execution or canon authority.
    """
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")
    role_mask = _normalized_roles(roles)
    raw_rows = [dict(row) for row in evidence_rows]
    errors = [str(value) for value in provider_errors]
    sources = _prepare_sources(raw_rows, max_sources=max_sources)

    evidence_core: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "CALLER_SUPPLIED_EVIDENCE",
        "query": q,
        "results": raw_rows,
        "result_count": len(raw_rows),
        "provider_errors": errors,
        "authority": _authority(),
    }
    evidence_core["evidence_commitment"] = _commit(
        b"GREMLIN-SUPPLIED-EVIDENCE/v0.1\0", evidence_core
    )
    acquisition = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "CALLER_SUPPLIED_EVIDENCE",
        "research_plan": {
            "stage_id": "CALLER_SUPPLIED_EVIDENCE_STAGE",
            "route_mask": list(role_mask),
            "candidate_only": True,
        },
        "evidence": evidence_core,
        "authority": _authority(),
    }

    if not sources:
        core: dict[str, Any] = {
            "schema": EXECUTOR_SCHEMA,
            "version": EXECUTOR_VERSION,
            "mode": "CALLER_SUPPLIED_EVIDENCE_REFERENCE_EXECUTOR",
            "query": q,
            "status": "NO_EVIDENCE_FAIL_CLOSED",
            "acquisition": acquisition,
            "stage_executions": [],
            "synthesis": None,
            "citations": [],
            "worker_abi_exercised": False,
            "authority": _authority(),
        }
        core["execution_commitment"] = _commit(
            b"GREMLIN-RESEARCH-EXECUTION/v0.1\0", core
        )
        return enrich_research_with_case_frames(
            core, relation_text if relation_text is not None else q, language=language
        )

    context = {
        "query": q,
        "sources": sources,
        "evidence_commitment": evidence_core["evidence_commitment"],
        "provider_errors": errors,
    }
    specialist_candidates: list[dict[str, Any]] = []
    stage_results: list[dict[str, Any]] = []
    for role in role_mask:
        task_core = {
            "species": role,
            "query": q,
            "evidence_commitment": evidence_core["evidence_commitment"],
        }
        task_commitment = _commit(
            b"GREMLIN-SUPPLIED-TASK/v0.1\0", task_core
        )
        task_id = f"supplied-{role.lower()}-{task_commitment[:16]}"
        candidate = _run_species(role, context)
        result_commitment = _commit(
            b"GREMLIN-SUPPLIED-RESULT/v0.1\0",
            {
                "task_commitment": task_commitment,
                "candidate": candidate,
            },
        )
        specialist_candidates.append({
            "species": role,
            "task_id": task_id,
            "task_commitment": task_commitment,
            "result_commitment": result_commitment,
            "candidate": candidate,
        })
        stage_results.append(dict(specialist_candidates[-1]))

    synthesis_candidate = _belzebub(
        {"specialist_candidates": specialist_candidates}, context
    )
    synthesis_commitment = _commit(
        b"GREMLIN-SUPPLIED-SYNTHESIS/v0.1\0",
        {
            "evidence_commitment": evidence_core["evidence_commitment"],
            "candidate": synthesis_candidate,
        },
    )
    synthesis = {
        "status": "CANDIDATE",
        "result_commitment": synthesis_commitment,
        "result": synthesis_candidate,
    }
    citations = [
        {
            "source_id": row["source_id"],
            "provider": row.get("provider"),
            "title": row.get("title"),
            "url": row.get("url"),
            "doi": row.get("doi"),
            "published": row.get("published"),
        }
        for row in sources
    ]
    core = {
        "schema": EXECUTOR_SCHEMA,
        "version": EXECUTOR_VERSION,
        "mode": "CALLER_SUPPLIED_EVIDENCE_REFERENCE_EXECUTOR",
        "query": q,
        "status": "CANDIDATE_SYNTHESIS_READY",
        "acquisition": acquisition,
        "stage_executions": [{
            "stage_id": "CALLER_SUPPLIED_EVIDENCE_STAGE",
            "status": "CANDIDATE_STAGE_COMPLETE",
            "route_mask": list(role_mask),
            "task_ids": [row["task_id"] for row in stage_results],
            "results": stage_results,
        }],
        "synthesis": synthesis,
        "citations": citations,
        "worker_abi_exercised": False,
        "authority": _authority(),
    }
    core["execution_commitment"] = _commit(
        b"GREMLIN-RESEARCH-EXECUTION/v0.1\0", core
    )
    return enrich_research_with_case_frames(
        core, relation_text if relation_text is not None else q, language=language
    )


__all__ = ["DEFAULT_ROLES", "SCHEMA", "VERSION", "execute_supplied_evidence_research"]
