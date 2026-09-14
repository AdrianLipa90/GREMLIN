from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Iterable, Mapping

from gremlin_mcp.relational_cases import extract_relations
from gremlin_mcp.research_executor import execute_research

SCHEMA = "GREMLIN_RELATIONAL_RESEARCH_V0_1"
VERSION = "0.1.0"


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
        raise ValueError("relational research data must be finite JSON") from exc


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


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text and not allow_empty:
        raise ValueError(f"{field} must be non-empty")
    return text


def _mapping_list(value: Any, field: str, *, missing_ok: bool = False) -> list[Mapping[str, Any]]:
    if value is None and missing_ok:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{field} must contain only objects")
    return value


def _frame_expression(frame: Mapping[str, Any]) -> str:
    if not isinstance(frame, Mapping):
        raise ValueError("relation frame must be an object")
    operator = _text(frame.get("operator"), "relation frame operator")
    bindings = _mapping_list(frame.get("bindings"), "relation frame bindings", missing_ok=True)
    slots: list[str] = []
    for row in bindings:
        case = _text(row.get("case"), "relation binding case")
        role = _text(row.get("operator_role"), "relation binding operator_role")
        entity = _text(row.get("entity"), "relation binding entity")
        slots.append(f"{case}:{role}={entity}")
    return f"{operator}[{', '.join(slots)}]"


def enrich_research_with_case_frames(
    research_result: Mapping[str, Any],
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
    if not isinstance(research_result, Mapping):
        raise ValueError("research_result must be an object")
    relation = _text(relation_text, "relation_text", allow_empty=True)
    lang = _text(language, "language")
    result = deepcopy(dict(research_result))
    parsed = extract_relations(relation, language=lang)
    if not isinstance(parsed, Mapping):
        raise RuntimeError("relation parser returned a non-object result")
    raw_frames = parsed.get("relations")
    frames = [deepcopy(dict(row)) for row in _mapping_list(raw_frames, "relation parser relations", missing_ok=True)]
    expressions = [_frame_expression(frame) for frame in frames]
    operators: list[str] = []
    for frame in frames:
        operator = _text(frame.get("operator"), "relation frame operator")
        if operator not in operators:
            operators.append(operator)

    stage_executions = _mapping_list(result.get("stage_executions"), "stage_executions", missing_ok=True)
    for stage_index, stage in enumerate(stage_executions):
        stage_results = _mapping_list(stage.get("results"), f"stage_executions[{stage_index}].results", missing_ok=True)
        for row_index, row in enumerate(stage_results):
            species_raw = row.get("species")
            if species_raw is None:
                continue
            species = _text(species_raw, f"stage result {stage_index}:{row_index} species").upper()
            candidate = row.get("candidate")
            if candidate is None:
                continue
            if not isinstance(candidate, dict):
                raise ValueError(f"stage result {stage_index}:{row_index} candidate must be an object")
            if species == "SPIDER":
                candidate["case_typed_relations"] = deepcopy(frames)
                candidate["case_relation_expressions"] = list(expressions)
                candidate["case_typing_basis"] = "GRAMMATICAL_CASE_PORT_PLUS_OPERATOR_LOCAL_ROLE"
                raw_existing = candidate.get("relation_predicates")
                if raw_existing is None:
                    existing: list[dict[str, Any]] = []
                else:
                    existing = [dict(item) for item in _mapping_list(raw_existing, "SPIDER relation_predicates")]
                existing_names: set[str] = set()
                for item in existing:
                    raw_operator = item.get("operator")
                    if raw_operator is None:
                        continue
                    existing_names.add(_text(raw_operator, "SPIDER relation predicate operator"))
                for operator in operators:
                    if operator not in existing_names:
                        existing.append(
                            {
                                "operator": operator,
                                "source_count": 0,
                                "support_source_ids": [],
                                "origin": "QUERY_OR_CALLER_RELATION_TEXT_CASE_PARSE",
                            }
                        )
                candidate["relation_predicates"] = existing
            elif species == "MOLE":
                candidate["case_constraints"] = deepcopy(frames)
                candidate["case_constraint_count"] = len(frames)
                candidate["case_constraint_status"] = (
                    "GRAMMAR_BOUND_RELATION_CONSTRAINTS_AVAILABLE" if frames else "NO_CASE_FRAME_AVAILABLE"
                )
            elif species == "HOUND":
                complete_count = 0
                for frame in frames:
                    complete = frame.get("complete")
                    if type(complete) is not bool:
                        raise ValueError("relation frame complete must be boolean")
                    complete_count += 1 if complete else 0
                candidate["case_frame_audit"] = {
                    "frame_count": len(frames),
                    "complete_frame_count": complete_count,
                    "status": "GRAMMAR_BOUND_RELATIONS_TO_VALIDATE_AGAINST_SOURCE_CLAIMS" if frames else "NO_CASE_FRAME_AVAILABLE",
                }

    synthesis = result.get("synthesis")
    if synthesis is not None:
        if not isinstance(synthesis, dict):
            raise ValueError("synthesis must be an object or None")
        candidate = synthesis.get("result")
        if candidate is not None:
            if not isinstance(candidate, dict):
                raise ValueError("synthesis.result must be an object or None")
            candidate["case_typed_relations"] = deepcopy(frames)
            candidate["case_relation_expressions"] = list(expressions)
            candidate["case_relation_status"] = (
                "GRAMMAR_BOUND_RELATION_CANDIDATES" if frames else "NO_CASE_FRAME_AVAILABLE"
            )
            if expressions:
                raw_answer = candidate.get("answer")
                if raw_answer is None:
                    existing_answer = ""
                else:
                    existing_answer = _text(raw_answer, "synthesis answer", allow_empty=True)
                relation_note = " Case-typed relation frame(s): " + "; ".join(expressions) + "."
                candidate["answer"] = existing_answer + relation_note

    parse_commitment = parsed.get("parse_commitment")
    if parse_commitment is not None and (not isinstance(parse_commitment, str) or not parse_commitment.strip()):
        raise RuntimeError("relation parser returned invalid parse_commitment")
    base_execution_commitment = result.get("execution_commitment")
    if base_execution_commitment is not None and (
        not isinstance(base_execution_commitment, str) or not base_execution_commitment.strip()
    ):
        raise ValueError("execution_commitment must be a string or None")

    result["relational_case_parse"] = dict(parsed)
    result["relational_case_expressions"] = expressions
    result["relational_case_frame_count"] = len(frames)
    result["relational_case_typing_applied"] = bool(frames)
    result["relational_case_authority"] = _authority()
    result["relational_execution_schema"] = SCHEMA
    result["relational_execution_version"] = VERSION
    result["relational_execution_commitment"] = _commit(
        {
            "base_execution_commitment": base_execution_commitment,
            "relation_parse_commitment": parse_commitment,
            "case_expressions": expressions,
            "authority": _authority(),
        }
    )
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
    query_text = _text(query, "query")
    if relation_text is not None and not isinstance(relation_text, str):
        raise ValueError("relation_text must be a string or None")
    relation = query_text if relation_text is None else relation_text
    lang = _text(language, "language")
    base = execute_research(
        query_text,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
        max_sources=max_sources,
    )
    if not isinstance(base, Mapping):
        raise RuntimeError("research executor returned a non-object result")
    return enrich_research_with_case_frames(
        base,
        relation,
        language=lang,
    )
