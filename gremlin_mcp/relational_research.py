from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Iterable

from gremlin_mcp.relational_cases import extract_relations
from gremlin_mcp.research_executor import execute_research

SCHEMA = "GREMLIN_RELATIONAL_RESEARCH_V0_1"
VERSION = "0.1.0"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(value: Any) -> str:
    return hashlib.blake2b(
        b"GREMLIN-RELATIONAL-RESEARCH/v0.1\0" + _canonical(value),
        digest_size=32,
    ).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _frame_expression(frame: dict[str, Any]) -> str:
    slots = ", ".join(
        f"{row['case']}:{row['operator_role']}={row['entity']}"
        for row in frame.get("bindings", [])
    )
    return f"{frame.get('operator')}[{slots}]"


def enrich_research_with_case_frames(
    research_result: dict[str, Any],
    relation_text: str,
    *,
    language: str = "pl",
) -> dict[str, Any]:
    """Attach grammar-bound relation frames to GREMLIN specialist outputs.

    Case frames are stronger than term co-occurrence for argument orientation, but
    remain candidate evidence from a bounded deterministic reference parser.
    Scientific entailment, physical causality and equation-level promotion remain
    separate validation steps.
    """
    result = deepcopy(research_result)
    parsed = extract_relations(relation_text, language=language)
    frames = [deepcopy(row) for row in parsed.get("relations", [])]
    expressions = [_frame_expression(frame) for frame in frames]
    operators = []
    for frame in frames:
        operator = str(frame.get("operator") or "")
        if operator and operator not in operators:
            operators.append(operator)

    for stage in result.get("stage_executions", []):
        for row in stage.get("results", []):
            species = str(row.get("species") or "").upper()
            candidate = row.get("candidate")
            if not isinstance(candidate, dict):
                continue
            if species == "SPIDER":
                candidate["case_typed_relations"] = deepcopy(frames)
                candidate["case_relation_expressions"] = list(expressions)
                candidate["case_typing_basis"] = "GRAMMATICAL_CASE_PORT_PLUS_OPERATOR_LOCAL_ROLE"
                existing = list(candidate.get("relation_predicates") or [])
                existing_names = {str(item.get("operator") or "") for item in existing if isinstance(item, dict)}
                for operator in operators:
                    if operator not in existing_names:
                        existing.append({
                            "operator": operator,
                            "source_count": 0,
                            "support_source_ids": [],
                            "origin": "QUERY_OR_CALLER_RELATION_TEXT_CASE_PARSE",
                        })
                candidate["relation_predicates"] = existing
            elif species == "MOLE":
                candidate["case_constraints"] = deepcopy(frames)
                candidate["case_constraint_count"] = len(frames)
                candidate["case_constraint_status"] = (
                    "GRAMMAR_BOUND_RELATION_CONSTRAINTS_AVAILABLE" if frames else "NO_CASE_FRAME_AVAILABLE"
                )
            elif species == "HOUND":
                candidate["case_frame_audit"] = {
                    "frame_count": len(frames),
                    "complete_frame_count": sum(bool(frame.get("complete")) for frame in frames),
                    "status": "GRAMMAR_BOUND_RELATIONS_TO_VALIDATE_AGAINST_SOURCE_CLAIMS" if frames else "NO_CASE_FRAME_AVAILABLE",
                }

    synthesis = result.get("synthesis")
    if isinstance(synthesis, dict) and isinstance(synthesis.get("result"), dict):
        candidate = synthesis["result"]
        candidate["case_typed_relations"] = deepcopy(frames)
        candidate["case_relation_expressions"] = list(expressions)
        candidate["case_relation_status"] = (
            "GRAMMAR_BOUND_RELATION_CANDIDATES" if frames else "NO_CASE_FRAME_AVAILABLE"
        )
        if expressions:
            existing_answer = str(candidate.get("answer") or "").strip()
            relation_note = " Case-typed relation frame(s): " + "; ".join(expressions) + "."
            candidate["answer"] = existing_answer + relation_note

    result["relational_case_parse"] = parsed
    result["relational_case_expressions"] = expressions
    result["relational_case_frame_count"] = len(frames)
    result["relational_case_typing_applied"] = bool(frames)
    result["relational_case_authority"] = _authority()
    result["relational_execution_schema"] = SCHEMA
    result["relational_execution_version"] = VERSION
    result["relational_execution_commitment"] = _commit({
        "base_execution_commitment": result.get("execution_commitment"),
        "relation_parse_commitment": parsed.get("parse_commitment"),
        "case_expressions": expressions,
        "authority": _authority(),
    })
    return result


def execute_relational_research(
    query: str,
    *,
    relation_text: str | None = None,
    language: str = "pl",
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    base = execute_research(
        query,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    return enrich_research_with_case_frames(
        base,
        relation_text if relation_text is not None else query,
        language=language,
    )
