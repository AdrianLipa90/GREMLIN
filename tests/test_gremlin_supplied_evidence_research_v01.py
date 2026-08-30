from __future__ import annotations

from gremlin_mcp.supplied_evidence import execute_supplied_evidence_research


def _evidence():
    return [
        {
            "provider": "benchmark",
            "title": "Supplier certificate is valid and connected with current compliance",
            "url": "fixture://source-a",
            "summary": "The supplier holds a valid certificate.",
            "published": "2026-08-01",
        },
        {
            "provider": "benchmark",
            "title": "Independent compliance record describes the supplier certificate",
            "url": "fixture://source-b",
            "summary": "Independent evidence confirms the current certificate.",
            "published": "2026-08-02",
        },
    ]


def test_supplied_evidence_runs_native_bestiary_and_relational_enrichment() -> None:
    result = execute_supplied_evidence_research(
        "Daję Zosi książkę", _evidence(), relation_text="Daję Zosi książkę"
    )
    assert result["mode"] == "CALLER_SUPPLIED_EVIDENCE_REFERENCE_EXECUTOR"
    assert result["status"] == "CANDIDATE_SYNTHESIS_READY"
    stage = result["stage_executions"][0]
    assert stage["route_mask"] == ["OWL", "SPIDER", "MOLE", "HOUND"]
    assert {row["species"] for row in stage["results"]} == {"OWL", "SPIDER", "MOLE", "HOUND"}
    assert result["synthesis"]["result"]["species"] == "BELZEBUB"
    assert result["relational_case_typing_applied"] is True
    frame = result["relational_case_parse"]["relations"][0]
    assert frame["operator"] == "GIVES"
    assert frame["complete"] is True
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def test_supplied_evidence_is_deterministic() -> None:
    first = execute_supplied_evidence_research("Daję Zosi książkę", _evidence())
    second = execute_supplied_evidence_research("Daję Zosi książkę", _evidence())
    assert first["execution_commitment"] == second["execution_commitment"]
    assert first["relational_execution_commitment"] == second["relational_execution_commitment"]


def test_empty_supplied_evidence_fails_closed_but_keeps_case_parse() -> None:
    result = execute_supplied_evidence_research("Daję Zosi książkę", [])
    assert result["status"] == "NO_EVIDENCE_FAIL_CLOSED"
    assert result["stage_executions"] == []
    assert result["synthesis"] is None
    assert result["relational_case_typing_applied"] is True
    assert result["relational_execution_commitment"]
