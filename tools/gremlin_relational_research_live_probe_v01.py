from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.relational_research import execute_relational_research

DEFAULT_QUERY = (
    "audit evidence contradictions dependencies graph derive relation between "
    "Shannon entropy information geometry and quantum gravity"
)
DEFAULT_RELATION_TEXT = "Informacja jest związana z geometrią."


def run_probe(query: str, relation_text: str, limit: int) -> dict:
    result = execute_relational_research(
        query,
        relation_text=relation_text,
        language="pl",
        providers=["crossref", "arxiv"],
        limit_per_provider=limit,
        max_species=4,
        max_sources=max(4, min(12, limit * 2)),
    )
    frames = result.get("relational_case_parse", {}).get("relations", [])
    frame = frames[0] if len(frames) == 1 else None
    expression = result.get("relational_case_expressions", [None])[0] if frames else None

    spider_frames = []
    mole_frames = []
    hound_audits = []
    for stage in result.get("stage_executions", []):
        for row in stage.get("results", []):
            candidate = row.get("candidate") or {}
            if row.get("species") == "SPIDER":
                spider_frames.extend(candidate.get("case_typed_relations", []))
            elif row.get("species") == "MOLE":
                mole_frames.extend(candidate.get("case_constraints", []))
            elif row.get("species") == "HOUND":
                hound_audits.append(candidate.get("case_frame_audit"))

    synthesis = result.get("synthesis") or {}
    belzebub = synthesis.get("result") if synthesis.get("state") == "DONE" else None
    checks = {
        "evidence_present": bool(result.get("citations")),
        "case_typing_applied": result.get("relational_case_typing_applied") is True,
        "single_connected_frame": bool(frame and frame.get("operator") == "CONNECTED_WITH"),
        "expression_oriented": bool(expression and "NOM:entity=Informacja" in expression and "INS:counterpart_in_relation=geometrią" in expression),
        "spider_received_frame": any(row.get("operator") == "CONNECTED_WITH" for row in spider_frames),
        "mole_received_constraint": any(row.get("operator") == "CONNECTED_WITH" for row in mole_frames),
        "hound_received_audit": any(isinstance(row, dict) and row.get("frame_count", 0) >= 1 for row in hound_audits),
        "belzebub_received_frame": bool(belzebub and belzebub.get("case_relation_status") == "GRAMMAR_BOUND_RELATION_CANDIDATES"),
        "candidate_only": bool(
            result.get("authority", {}).get("canon_allowed") is False
            and result.get("relational_case_authority", {}).get("canon_allowed") is False
        ),
    }
    return {
        "schema": "GREMLIN_RELATIONAL_RESEARCH_LIVE_PROBE_V0_1",
        "query": query,
        "relation_text": relation_text,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "relational_case_expressions": result.get("relational_case_expressions"),
        "relational_execution_commitment": result.get("relational_execution_commitment"),
        "base_execution_commitment": result.get("execution_commitment"),
        "source_count": len(result.get("citations") or []),
        "providers_completed": result.get("acquisition", {}).get("evidence", {}).get("providers_completed"),
        "provider_errors": result.get("acquisition", {}).get("evidence", {}).get("provider_errors"),
        "belzebub_state": synthesis.get("state"),
        "belzebub_answer": belzebub.get("answer") if isinstance(belzebub, dict) else None,
        "authority": result.get("authority"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--relation-text", default=DEFAULT_RELATION_TEXT)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="artifacts/gremlin_relational_research_live.json")
    args = parser.parse_args()
    result = run_probe(args.query, args.relation_text, args.limit)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload + "\n", encoding="utf-8")
    if result["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
