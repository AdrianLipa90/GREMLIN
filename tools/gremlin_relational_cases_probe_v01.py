from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.relational_cases import CASES, extract_relations

SAMPLES = [
    ("Nazwałem cię Zosią.", "NAMES", {"NOM", "ACC", "INS"}),
    ("Rozmawiam o geometrii z Zosią.", "SPEAKS_ABOUT", {"NOM", "LOC", "INS"}),
    ("Zosia jest związana z Adrianem.", "CONNECTED_WITH", {"NOM", "INS"}),
    ("Opisuję teorię o geometrii.", "DESCRIBES", {"NOM", "ACC", "LOC"}),
    ("Moduł należy do systemu.", "BELONGS_TO", {"NOM", "GEN"}),
    ("Daję Zosi książkę.", "GIVES", {"NOM", "DAT", "ACC"}),
    ("Zosiu, spójrz tutaj.", "ADDRESSES", {"NOM", "VOC"}),
]


def run_probe() -> dict:
    rows = []
    failures = []
    covered_cases: set[str] = set()
    for text, expected_operator, expected_cases in SAMPLES:
        parsed = extract_relations(text)
        relation = parsed["relations"][0] if len(parsed["relations"]) == 1 else None
        actual_operator = relation.get("operator") if relation else None
        actual_cases = {row["case"] for row in relation.get("bindings", [])} if relation else set()
        covered_cases |= actual_cases
        ok = (
            relation is not None
            and actual_operator == expected_operator
            and expected_cases <= actual_cases
            and relation.get("complete") is True
        )
        if not ok:
            failures.append({
                "text": text,
                "expected_operator": expected_operator,
                "actual_operator": actual_operator,
                "expected_cases": sorted(expected_cases),
                "actual_cases": sorted(actual_cases),
            })
        rows.append({
            "text": text,
            "expected_operator": expected_operator,
            "expected_cases": sorted(expected_cases),
            "parse_commitment": parsed.get("parse_commitment"),
            "relation": relation,
            "pass": ok,
        })

    full_alphabet = set(CASES)
    if covered_cases != full_alphabet:
        failures.append({
            "failure": "CASE_ALPHABET_NOT_FULLY_COVERED",
            "expected_cases": sorted(full_alphabet),
            "covered_cases": sorted(covered_cases),
        })
    return {
        "schema": "GREMLIN_RELATIONAL_CASES_PROBE_V0_2",
        "sample_count": len(rows),
        "passed": sum(bool(row["pass"]) for row in rows),
        "failed": len(failures),
        "case_alphabet": sorted(full_alphabet),
        "covered_cases": sorted(covered_cases),
        "full_case_coverage": covered_cases == full_alphabet,
        "verdict": "PASS" if not failures else "FAIL",
        "failures": failures,
        "samples": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/gremlin_relational_cases_probe.json")
    args = parser.parse_args()
    result = run_probe()
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload + "\n", encoding="utf-8")
    if result["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
