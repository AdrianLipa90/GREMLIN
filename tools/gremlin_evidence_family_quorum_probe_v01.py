from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.evidence_quorum import (
    CONFLICT_DEFER_TO_HOUND,
    QUORUM_INSUFFICIENT,
    QUORUM_SUFFICIENT,
    assess_family_quorum,
)
from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT


def _row(evidence_id: str, family: str, stance: str, confidence: float = 1.0) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_family": family,
        "stance": stance,
        "payload_commitment": f"probe:{evidence_id}",
        "credibility": confidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    duplicate_family = assess_family_quorum(
        [
            _row("dup-a", "WORK:10.1234/same", SUPPORT, 0.95),
            _row("dup-b", "WORK:10.1234/same", SUPPORT, 0.99),
        ],
        min_unipolar_families=2,
    )
    distinct_families = assess_family_quorum(
        [
            _row("ind-a", "WORK:10.1234/a", SUPPORT, 0.80),
            _row("ind-b", "WORK:10.5678/b", SUPPORT, 0.81),
        ],
        min_unipolar_families=2,
    )
    high_confidence_single = assess_family_quorum(
        [_row("high", "WORK:10.9999/one", SUPPORT, 0.999)],
        min_unipolar_families=2,
    )
    mixed_conflict = assess_family_quorum(
        [
            _row("s1", "WORK:s1", SUPPORT, 0.90),
            _row("s2", "WORK:s2", SUPPORT, 0.90),
            _row("s3", "WORK:s3", SUPPORT, 0.90),
            _row("c1", "WORK:c1", CONTRADICT, 0.70),
        ],
        min_unipolar_families=2,
    )

    expected_authority = {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    checks = {
        "duplicate_family_rejected": (
            duplicate_family["state"] == QUORUM_INSUFFICIENT
            and duplicate_family["support_family_count"] == 1
            and duplicate_family["quorum_satisfied"] is False
        ),
        "two_distinct_families_accepted": (
            distinct_families["state"] == QUORUM_SUFFICIENT
            and distinct_families["support_family_count"] == 2
            and distinct_families["quorum_satisfied"] is True
        ),
        "confidence_does_not_bypass_diversity": (
            high_confidence_single["state"] == QUORUM_INSUFFICIENT
            and high_confidence_single["quorum_satisfied"] is False
        ),
        "mixed_evidence_defers_to_hound": (
            mixed_conflict["state"] == CONFLICT_DEFER_TO_HOUND
            and mixed_conflict["conflict_present"] is True
            and mixed_conflict["quorum_satisfied"] is None
        ),
        "authority_fail_closed": all(
            result["authority"] == expected_authority
            for result in (
                duplicate_family,
                distinct_families,
                high_confidence_single,
                mixed_conflict,
            )
        ),
    }

    receipt = {
        "schema": "GREMLIN_EVIDENCE_FAMILY_QUORUM_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "profile": {
            "minimum_unipolar_provenance_families": 2,
            "family_semantics": "PROVENANCE_DIVERSITY_HEURISTIC_NOT_INDEPENDENCE_PROOF",
            "conflict_policy": "SUPPORT_CONTRADICT_CONFLICT_ALWAYS_DEFERRED_TO_HOUND_NOT_MAJORITY_VOTE",
        },
        "cases": {
            "duplicate_family": duplicate_family,
            "distinct_families": distinct_families,
            "high_confidence_single": high_confidence_single,
            "mixed_conflict": mixed_conflict,
        },
        "leaderboard_or_external_benchmark_claimed": False,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
