from __future__ import annotations

import pytest

import gremlin_mcp.relational_research as rr


def _parsed_relation(*, complete: bool = True):
    return {
        "status": "REFERENCE_RULE_MATCH",
        "relations": [
            {
                "operator": "CONNECTED_WITH",
                "complete": complete,
                "bindings": [
                    {"case": "NOM", "operator_role": "subject", "entity": "Zosia"},
                    {"case": "INS", "operator_role": "counterpart", "entity": "Adrianem"},
                ],
            }
        ],
        "parse_commitment": "p" * 64,
    }


def _base_result():
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "execution_commitment": "e" * 64,
        "stage_executions": [
            {
                "stage_id": "MAP_RELATIONS",
                "results": [
                    {
                        "species": "SPIDER",
                        "candidate": {"relation_predicates": []},
                    }
                ],
            },
            {
                "stage_id": "ADVERSARIAL_CHECK",
                "results": [{"species": "HOUND", "candidate": {}}],
            },
        ],
        "synthesis": {
            "state": "DONE",
            "species": "BELZEBUB",
            "result": {"answer": "Candidate synthesis."},
        },
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def test_non_string_species_is_rejected_instead_of_stringified(monkeypatch) -> None:
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: _parsed_relation())
    payload = _base_result()
    payload["stage_executions"][0]["results"][0]["species"] = 7
    with pytest.raises(ValueError, match="species must be a string"):
        rr.enrich_research_with_case_frames(payload, "Zosia jest związana z Adrianem.")


def test_non_mapping_candidate_is_rejected_instead_of_skipped(monkeypatch) -> None:
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: _parsed_relation())
    payload = _base_result()
    payload["stage_executions"][0]["results"][0]["candidate"] = "not-an-object"
    with pytest.raises(ValueError, match="candidate must be an object"):
        rr.enrich_research_with_case_frames(payload, "Zosia jest związana z Adrianem.")


def test_relation_complete_requires_literal_boolean(monkeypatch) -> None:
    malformed = _parsed_relation()
    malformed["relations"][0]["complete"] = 1
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: malformed)
    with pytest.raises(ValueError, match="relation frame complete must be boolean"):
        rr.enrich_research_with_case_frames(_base_result(), "Zosia jest związana z Adrianem.")


def test_synthesis_answer_is_not_silently_stringified(monkeypatch) -> None:
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: _parsed_relation())
    payload = _base_result()
    payload["synthesis"]["result"]["answer"] = 123
    with pytest.raises(ValueError, match="synthesis answer must be a string"):
        rr.enrich_research_with_case_frames(payload, "Zosia jest związana z Adrianem.")


def test_non_list_stage_results_fail_loud(monkeypatch) -> None:
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: _parsed_relation())
    payload = _base_result()
    payload["stage_executions"][0]["results"] = {"species": "SPIDER"}
    with pytest.raises(ValueError, match=r"stage_executions\[0\]\.results must be a list"):
        rr.enrich_research_with_case_frames(payload, "Zosia jest związana z Adrianem.")


def test_execute_relational_research_rejects_non_mapping_executor_output(monkeypatch) -> None:
    monkeypatch.setattr(rr, "execute_research", lambda *args, **kwargs: ["invalid"])
    with pytest.raises(RuntimeError, match="research executor returned a non-object result"):
        rr.execute_relational_research("public query", relation_text="relation")


def test_invalid_execution_commitment_type_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(rr, "extract_relations", lambda *args, **kwargs: _parsed_relation())
    payload = _base_result()
    payload["execution_commitment"] = 123
    with pytest.raises(ValueError, match="execution_commitment must be a string or None"):
        rr.enrich_research_with_case_frames(payload, "Zosia jest związana z Adrianem.")
