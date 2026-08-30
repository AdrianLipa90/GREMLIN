from __future__ import annotations

import hashlib
import json
from typing import Any

from gremlin_mcp.pipeline import SPECIALISTS
from gremlin_mcp.research_planner_v02 import build_research_plan_v02

SCHEMA = "GREMLIN_OOD_ROUTING_BENCHMARK_V0_6"
VERSION = "0.6.0"

ENGLISH_PARAPHRASES = (
    ("en_spider_01", "Show how these components fit together.", ("SPIDER",)),
    ("en_spider_02", "Trace structural connections among the modules.", ("SPIDER",)),
    ("en_spider_03", "Identify interconnections among these concepts.", ("SPIDER",)),
    ("en_spider_04", "Describe associations among the parts.", ("SPIDER",)),
    ("en_raven_01", "Bring back the context from earlier work.", ("RAVEN",)),
    ("en_raven_02", "Retrieve what we used before.", ("RAVEN",)),
    ("en_raven_03", "Consult past work on this problem.", ("RAVEN",)),
    ("en_raven_04", "Recall the context from our memory.", ("RAVEN",)),
    ("en_hound_01", "Challenge the assumptions and look for inconsistencies.", ("HOUND",)),
    ("en_hound_02", "Stress-check the result for discrepancies.", ("HOUND",)),
    ("en_hound_03", "Look for problems and mismatches in the result.", ("HOUND",)),
    ("en_hound_04", "Perform a sanity check for inconsistencies.", ("HOUND",)),
    ("en_mole_01", "Work out the mathematics for the coupling.", ("MOLE",)),
    ("en_mole_02", "Deduce an expression for the coupling.", ("MOLE",)),
    ("en_mole_03", "Infer the mechanism from the assumptions.", ("MOLE",)),
    ("en_mole_04", "Show the math behind the result.", ("MOLE",)),
    ("en_ant_01", "Explore all possible configurations.", ("ANT",)),
    ("en_ant_02", "Search possibilities across candidate configurations.", ("ANT",)),
    ("en_ant_03", "Compare alternative candidates.", ("ANT",)),
    ("en_ant_04", "List all options in the candidate space.", ("ANT",)),
    ("en_mantis_01", "Clean up repeated branches.", ("MANTIS",)),
    ("en_mantis_02", "Remove repeats from the candidate set.", ("MANTIS",)),
    ("en_mantis_03", "Collapse duplicates before synthesis.", ("MANTIS",)),
    ("en_mantis_04", "Trim branches that repeat the same candidate.", ("MANTIS",)),
)

POLISH_INTENTS = (
    ("pl_spider_01", "Zmapuj powiązania i zależności między elementami.", ("SPIDER",)),
    ("pl_spider_02", "Pokaż relacje i połączenia między modułami.", ("SPIDER",)),
    ("pl_raven_01", "Przywołaj wcześniejszy kontekst z pamięci.", ("RAVEN",)),
    ("pl_raven_02", "Odzyskaj historię poprzednich wyników z archiwum.", ("RAVEN",)),
    ("pl_hound_01", "Sprawdź sprzeczności i niezgodności.", ("HOUND",)),
    ("pl_hound_02", "Zweryfikuj anomalie i błędy w wyniku.", ("HOUND",)),
    ("pl_mole_01", "Wyprowadź wzór i policz wynik.", ("MOLE",)),
    ("pl_mole_02", "Rozwiąż równanie i pokaż mechanizm.", ("MOLE",)),
    ("pl_ant_01", "Przeszukaj wszystkie warianty i możliwości.", ("ANT",)),
    ("pl_ant_02", "Enumeruj kombinacje i konfiguracje kandydatów.", ("ANT",)),
    ("pl_mantis_01", "Usuń duplikaty i zbędne powtórzenia.", ("MANTIS",)),
    ("pl_mantis_02", "Przytnij redundantne i powtarzające się gałęzie.", ("MANTIS",)),
)

AMBIGUITY_TRAPS = (
    ("trap_contest", "Summarize the contest results and leaderboard.", "HOUND"),
    ("trap_protest", "Summarize the protest movement and its organizers.", "HOUND"),
    ("trap_merge_sort", "Explain merge sort complexity.", "MANTIS"),
    ("trap_previous_gpu", "Compare the previous generation GPU with the current one.", "RAVEN"),
    ("trap_deep_learning", "Describe a deep learning model at a high level.", "MOLE"),
    ("trap_network_socket", "Explain a network socket and port numbers.", "SPIDER"),
    ("trap_edge_browser", "Change an Edge browser setting.", "SPIDER"),
    ("trap_node_package", "Install a Node package with npm.", "SPIDER"),
    ("trap_bridge_rectifier", "Explain a bridge rectifier circuit.", "SPIDER"),
    ("trap_wifi_connect", "Connect this laptop to Wi-Fi.", "SPIDER"),
)


def _metrics(rows):
    tp = fp = fn = exact = expected_total = selected_total = 0
    for row in rows:
        expected = set(row["expected"])
        selected = set(row["selected"])
        tp += len(expected & selected)
        fp += len(selected - expected)
        fn += len(expected - selected)
        expected_total += len(expected)
        selected_total += len(selected)
        exact += int(expected == selected)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_rate": exact / len(rows) if rows else 1.0,
        "omission_rate": fn / expected_total if expected_total else 0.0,
        "selected_total": selected_total,
        "expected_total": expected_total,
    }


def _evaluate_cases(cases):
    rows = []
    for case_id, query, expected_extra in cases:
        plan = build_research_plan_v02(query)
        selected_extra = tuple(s for s in plan["species_union"] if s != "OWL")
        rows.append({
            "case_id": case_id,
            "query": query,
            "expected": list(expected_extra),
            "selected": list(selected_extra),
            "exact": set(selected_extra) == set(expected_extra),
            "query_route_commitment": plan["query_route_commitment"],
            "plan_commitment": plan["plan_commitment"],
        })
    return rows


def run_benchmark() -> dict[str, Any]:
    english = _evaluate_cases(ENGLISH_PARAPHRASES)
    polish = _evaluate_cases(POLISH_INTENTS)
    semantic_rows = english + polish
    semantic = _metrics(semantic_rows)

    traps = []
    false_additions = 0
    for case_id, query, forbidden in AMBIGUITY_TRAPS:
        plan = build_research_plan_v02(query)
        selected = tuple(s for s in plan["species_union"] if s != "OWL")
        hit = forbidden in selected
        false_additions += int(hit)
        traps.append({
            "case_id": case_id,
            "query": query,
            "forbidden": forbidden,
            "selected": list(selected),
            "false_addition": hit,
            "plan_commitment": plan["plan_commitment"],
        })

    semantic_cases = len(semantic_rows)
    dispatched = semantic["selected_total"]
    broadcast = semantic_cases * (len(SPECIALISTS) - 1)
    fanout_reduction = 1.0 - dispatched / broadcast if broadcast else 0.0

    gates = {
        "semantic_precision_ge_0_95": semantic["precision"] >= 0.95,
        "semantic_recall_ge_0_95": semantic["recall"] >= 0.95,
        "semantic_exact_rate_ge_0_90": semantic["exact_rate"] >= 0.90,
        "omission_rate_le_0_05": semantic["omission_rate"] <= 0.05,
        "ambiguity_false_additions_eq_0": false_additions == 0,
        "fanout_reduction_ge_0_50": fanout_reduction >= 0.50,
    }

    out = {
        "schema": SCHEMA,
        "version": VERSION,
        "scope": "OOD_LEXICAL_PARAPHRASE_POLISH_INTENT_AMBIGUITY_REGRESSION",
        "not_claimed": [
            "NOT_EXTERNAL_ANSWER_QUALITY",
            "NOT_HIDDEN_BENCHMARK_GENERALIZATION_PROOF",
            "NOT_MODEL_REASONING_QUALITY",
        ],
        "english_paraphrase_case_count": len(english),
        "polish_intent_case_count": len(polish),
        "ambiguity_trap_case_count": len(traps),
        "semantic": semantic,
        "ambiguity_false_additions": false_additions,
        "fanout": {
            "selected_specialist_tasks": dispatched,
            "six_specialist_broadcast_tasks": broadcast,
            "reduction_fraction": fanout_reduction,
            "reduction_percent": 100.0 * fanout_reduction,
        },
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "english_cases": english,
        "polish_cases": polish,
        "ambiguity_cases": traps,
    }
    out["benchmark_commitment"] = hashlib.blake2b(
        b"GREMLIN-OOD-ROUTING-BENCH/v0.6\0"
        + json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        digest_size=32,
    ).hexdigest()
    return out


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), ensure_ascii=False, indent=2, sort_keys=True))
