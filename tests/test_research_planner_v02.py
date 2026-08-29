from gremlin_mcp.research_planner_v02 import build_research_plan_v02


def test_full_query_routes_four_core_research_species_by_stage():
    plan = build_research_plan_v02("Audit contradictions dependencies graph and derive equation mechanism")
    assert plan["species_union"] == ["OWL", "SPIDER", "MOLE", "HOUND"]
    assert [x["stage_id"] for x in plan["stages"]] == ["ACQUIRE_EVIDENCE", "MAP_RELATIONS", "DERIVE_CANDIDATE", "ADVERSARIAL_CHECK"]
    assert plan["all_stage_routes_match_targets"] is True


def test_extended_query_activates_ant_mantis_and_raven_without_broadcast():
    plan = build_research_plan_v02("Review prior memory archive, enumerate permutations variants, prune duplicate obsolete overlap")
    assert plan["species_union"] == ["OWL", "RAVEN", "ANT", "MANTIS"]
    assert [x["stage_id"] for x in plan["stages"]] == ["ACQUIRE_EVIDENCE", "MEMORY_CONTEXT", "ENUMERATE_VARIANTS", "PRUNE_REDUNDANCY"]
    assert plan["all_stage_routes_match_targets"] is True


def test_plan_remains_candidate_only():
    plan = build_research_plan_v02("Review evidence")
    assert plan["production_runtime_write"] is False
    assert plan["execution_admitted"] is False
    assert plan["canon_allowed"] is False
