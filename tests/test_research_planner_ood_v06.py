from gremlin_mcp.research_planner_v02 import build_research_plan_v02
from gremlin_mcp.router import route


def _has(plan, species):
    return species in plan["species_union"]


def test_ood_english_paraphrases_recover_specialists():
    cases = {
        "SPIDER": "Show how these components fit together and trace their structural connections.",
        "MOLE": "Work out the mathematics and obtain an expression for the coupling.",
        "HOUND": "Challenge the assumptions, look for inconsistencies and stress-check the result.",
        "RAVEN": "Bring back the context from earlier work and retrieve what we used before.",
        "ANT": "Explore all possible configurations and alternative candidates.",
        "MANTIS": "Clean up repeated branches and remove equivalent candidates.",
    }
    for species, query in cases.items():
        plan = build_research_plan_v02(query)
        assert _has(plan, species), (species, plan["species_union"], plan["query_router_scores"])
        assert plan["all_stage_routes_match_targets"] is True


def test_ood_polish_intent_routes_by_unicode_normalized_semantics():
    cases = {
        "SPIDER": "Zmapuj powiązania i zależności między elementami.",
        "MOLE": "Wyprowadź wzór i policz wynik.",
        "HOUND": "Sprawdź sprzeczności i niezgodności.",
        "RAVEN": "Przywołaj wcześniejszy kontekst z pamięci.",
        "ANT": "Przeszukaj wszystkie warianty i możliwości.",
        "MANTIS": "Usuń duplikaty i zbędne powtórzenia.",
    }
    for species, query in cases.items():
        plan = build_research_plan_v02(query)
        assert _has(plan, species), (species, plan["species_union"], plan["query_router_scores"])


def test_ambiguity_traps_do_not_use_raw_substring_matching():
    traps = (
        ("Summarize the contest results and leaderboard.", "HOUND"),
        ("Explain merge sort complexity.", "MANTIS"),
        ("Compare the previous generation GPU with the current one.", "RAVEN"),
        ("Describe a deep learning model at a high level.", "MOLE"),
        ("Explain a network socket and port numbers.", "SPIDER"),
    )
    for query, forbidden in traps:
        plan = build_research_plan_v02(query)
        assert forbidden not in plan["species_union"], (query, forbidden, plan["species_union"])


def test_direct_router_blocks_contest_to_test_false_positive():
    decision = route({"query": "The contest leaderboard was published yesterday."}, max_species=7)
    assert "HOUND" not in decision["route_mask"]


def test_query_router_commitment_is_exposed_and_deterministic():
    query = "Work out the mathematics and check for inconsistencies."
    a = build_research_plan_v02(query)
    b = build_research_plan_v02(query)
    assert a["query_route_commitment"] == b["query_route_commitment"]
    assert a["plan_commitment"] == b["plan_commitment"]
    assert {"MOLE", "HOUND"} <= set(a["species_union"])
