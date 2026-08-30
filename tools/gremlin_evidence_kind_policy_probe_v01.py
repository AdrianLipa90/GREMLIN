from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.evidence_kind import (
    CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
    EMPIRICAL,
    ENGINEERING,
    ENGINEERING_TEST,
    KIND_POLICY_INSUFFICIENT,
    KIND_POLICY_SUFFICIENT,
    PRIMARY_EXPERIMENT,
    REVIEW_META,
    SIMULATION,
    THEORETICAL,
    THEORY_DERIVATION,
    assess_evidence_kind_policy,
)
from gremlin_mcp.evidence_robustness import SUPPORT


def _guard(source_id: str, family: str) -> dict:
    return {
        "evidence_id": source_id,
        "source_family": family,
        "stance": SUPPORT,
        "payload_commitment": f"probe:{source_id}",
    }


def _assignment(source_id: str, kind: str) -> dict:
    return {
        "source_id": source_id,
        "content_commitment": f"content:{source_id}",
        "evidence_kind": kind,
        "producer_id": "probe-kind-producer",
        "producer_version": "0.1.0",
        "model_id": None,
        "mode": "PROBE_EXPLICIT_ASSIGNMENT",
        "rationale_code": "PROBE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    guards = [_guard("a", "fam-a"), _guard("b", "fam-b")]

    empirical_review_only = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", REVIEW_META), _assignment("b", REVIEW_META)],
        claim_mode=EMPIRICAL,
    )
    empirical_direct = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", PRIMARY_EXPERIMENT), _assignment("b", REVIEW_META)],
        claim_mode=EMPIRICAL,
    )
    theoretical_sim_only = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", SIMULATION), _assignment("b", REVIEW_META)],
        claim_mode=THEORETICAL,
    )
    theoretical_direct = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", THEORY_DERIVATION), _assignment("b", REVIEW_META)],
        claim_mode=THEORETICAL,
    )
    engineering_sim_only = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", SIMULATION), _assignment("b", REVIEW_META)],
        claim_mode=ENGINEERING,
    )
    engineering_direct = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", ENGINEERING_TEST), _assignment("b", REVIEW_META)],
        claim_mode=ENGINEERING,
    )
    unknown_mode = assess_evidence_kind_policy(
        guards,
        assignments=[_assignment("a", PRIMARY_EXPERIMENT), _assignment("b", REVIEW_META)],
        claim_mode=None,
    )

    expected_authority = {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    results = {
        "empirical_review_only": empirical_review_only,
        "empirical_direct": empirical_direct,
        "theoretical_sim_only": theoretical_sim_only,
        "theoretical_direct": theoretical_direct,
        "engineering_sim_only": engineering_sim_only,
        "engineering_direct": engineering_direct,
        "unknown_mode": unknown_mode,
    }
    checks = {
        "review_only_not_empirical_direct": empirical_review_only["state"] == KIND_POLICY_INSUFFICIENT,
        "primary_experiment_satisfies_empirical_direct_gate": empirical_direct["state"] == KIND_POLICY_SUFFICIENT,
        "simulation_not_theory_derivation": theoretical_sim_only["state"] == KIND_POLICY_INSUFFICIENT,
        "theory_derivation_satisfies_theoretical_gate": theoretical_direct["state"] == KIND_POLICY_SUFFICIENT,
        "simulation_not_engineering_test": engineering_sim_only["state"] == KIND_POLICY_INSUFFICIENT,
        "engineering_test_satisfies_engineering_gate": engineering_direct["state"] == KIND_POLICY_SUFFICIENT,
        "unknown_claim_mode_fails_closed": unknown_mode["state"] == CLAIM_MODE_UNKNOWN_FAIL_CLOSED,
        "authority_fail_closed": all(row["authority"] == expected_authority for row in results.values()),
    }

    receipt = {
        "schema": "GREMLIN_EVIDENCE_KIND_POLICY_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "cases": results,
        "scope": "DETERMINISTIC_CONTRACT_VALIDATION_ONLY",
        "external_benchmark_claimed": False,
        "automatic_kind_inference_executed": False,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
