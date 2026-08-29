from __future__ import annotations

import gremlin_mcp.relational_research as rr


def _base_result():
    return {
        "schema": "GREMLIN_RESEARCH_EXECUTOR_V0_1",
        "status": "CANDIDATE_SYNTHESIS_READY",
        "execution_commitment": "a" * 64,
        "stage_executions": [
            {
                "stage_id": "MAP_RELATIONS",
                "results": [
                    {
                        "species": "SPIDER",
                        "candidate": {
                            "concepts": [{"concept": "geometria"}],
                            "relation_predicates": [],
                        },
                    }
                ],
            },
            {
                "stage_id": "DERIVE_CANDIDATE",
                "results": [
                    {
                        "species": "MOLE",
                        "candidate": {"candidate_concept_path": ["geometria", "grawitacja"]},
                    }
                ],
            },
            {
                "stage_id": "ADVERSARIAL_CHECK",
                "results": [
                    {"species": "HOUND", "candidate": {"contradictions": []}}
                ],
            },
        ],
        "synthesis": {
            "state": "DONE",
            "species": "BELZEBUB",
            "result": {
                "answer": "Candidate synthesis.",
                "epistemic_status": "CANDIDATE_SYNTHESIS",
            },
        },
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def test_case_frames_reach_spider_mole_hound_and_belzebub() -> None:
    result = rr.enrich_research_with_case_frames(
        _base_result(),
        "Rozmawiam o geometrii z Zosią.",
        language="pl",
    )
    assert result["relational_case_typing_applied"] is True
    assert result["relational_case_frame_count"] == 1
    assert result["relational_case_expressions"] == [
        "SPEAKS_ABOUT[NOM:speaker=@speaker, LOC:topic=geometrii, INS:interlocutor=Zosią]"
    ]

    spider = result["stage_executions"][0]["results"][0]["candidate"]
    assert spider["case_typed_relations"][0]["operator"] == "SPEAKS_ABOUT"
    assert any(row["operator"] == "SPEAKS_ABOUT" for row in spider["relation_predicates"])

    mole = result["stage_executions"][1]["results"][0]["candidate"]
    assert mole["case_constraint_count"] == 1
    assert mole["case_constraints"][0]["bindings"][1]["case"] == "LOC"

    hound = result["stage_executions"][2]["results"][0]["candidate"]
    assert hound["case_frame_audit"]["complete_frame_count"] == 1

    belzebub = result["synthesis"]["result"]
    assert belzebub["case_relation_status"] == "GRAMMAR_BOUND_RELATION_CANDIDATES"
    assert "SPEAKS_ABOUT" in belzebub["answer"]
    assert len(result["relational_execution_commitment"]) == 64


def test_naming_preserves_case_and_operator_local_roles() -> None:
    result = rr.enrich_research_with_case_frames(_base_result(), "Nazwałem cię Zosią.")
    frame = result["relational_case_parse"]["relations"][0]
    bindings = {row["case"]: row for row in frame["bindings"]}
    assert frame["operator"] == "NAMES"
    assert bindings["ACC"]["operator_role"] == "entity_named"
    assert bindings["INS"]["operator_role"] == "assigned_name_or_designation"
    assert result["relational_case_expressions"][0].startswith("NAMES[")


def test_execute_relational_research_wraps_base_executor(monkeypatch) -> None:
    monkeypatch.setattr(rr, "execute_research", lambda *args, **kwargs: _base_result())
    result = rr.execute_relational_research(
        "public web research query",
        relation_text="Zosia jest związana z Adrianem.",
        providers=["crossref"],
    )
    assert result["relational_case_typing_applied"] is True
    assert result["relational_case_parse"]["relations"][0]["operator"] == "CONNECTED_WITH"
    assert result["authority"]["canon_allowed"] is False


def test_no_case_match_remains_explicit_and_does_not_invent_frame() -> None:
    result = rr.enrich_research_with_case_frames(_base_result(), "Entropia i geometria")
    assert result["relational_case_typing_applied"] is False
    assert result["relational_case_frame_count"] == 0
    assert result["relational_case_parse"]["status"] == "NO_REFERENCE_RULE_MATCH"
    assert result["synthesis"]["result"]["case_relation_status"] == "NO_CASE_FRAME_AVAILABLE"
