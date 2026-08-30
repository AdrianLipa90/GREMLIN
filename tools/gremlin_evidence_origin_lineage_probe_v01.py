from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.evidence_kind import EMPIRICAL, PRIMARY_EXPERIMENT
from gremlin_mcp.evidence_origin import (
    DATASET,
    EXPERIMENT,
    ORIGIN_POLICY_INSUFFICIENT,
    ORIGIN_POLICY_SUFFICIENT,
    ORIGIN_UNKNOWN_FAIL_CLOSED,
    PRIMARY_GENERATION,
    REANALYSIS,
    assess_evidence_origin_lineage,
)
from gremlin_mcp.evidence_robustness import SUPPORT


def _guard(source_id: str, family: str) -> dict:
    return {
        "evidence_id": source_id,
        "source_family": family,
        "stance": SUPPORT,
        "payload_commitment": f"probe:{source_id}",
    }


def _kind(source_id: str) -> dict:
    return {"source_id": source_id, "evidence_kind": PRIMARY_EXPERIMENT}


def _origin(source_id: str, origin_id: str | None, *, kind=EXPERIMENT, usage=PRIMARY_GENERATION) -> dict:
    refs = (
        [{"origin_id": origin_id, "origin_kind": kind, "usage": usage}]
        if origin_id is not None
        else [{"origin_id": "UNKNOWN", "origin_kind": "UNKNOWN", "usage": "UNKNOWN"}]
    )
    return {"source_id": source_id, "origin_refs": refs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    guards = [_guard("a", "fam-a"), _guard("b", "fam-b")]
    kinds = [_kind("a"), _kind("b")]

    shared_dataset = assess_evidence_origin_lineage(
        guards,
        evidence_kind_assignments=kinds,
        origin_assignments=[
            _origin("a", "dataset:shared", kind=DATASET, usage=REANALYSIS),
            _origin("b", "dataset:shared", kind=DATASET, usage=REANALYSIS),
        ],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    distinct_origins = assess_evidence_origin_lineage(
        guards,
        evidence_kind_assignments=kinds,
        origin_assignments=[_origin("a", "experiment:A"), _origin("b", "experiment:B")],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    unknown_origin = assess_evidence_origin_lineage(
        guards,
        evidence_kind_assignments=kinds,
        origin_assignments=[_origin("a", "experiment:A"), _origin("b", None)],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )
    bridge_case = assess_evidence_origin_lineage(
        [_guard("a", "fam-a"), _guard("b", "fam-b"), _guard("c", "fam-c")],
        evidence_kind_assignments=[_kind("a"), _kind("b"), _kind("c")],
        origin_assignments=[
            _origin("a", "experiment:X"),
            _origin("b", "experiment:Y"),
            {
                "source_id": "c",
                "origin_refs": [
                    {"origin_id": "experiment:X", "origin_kind": EXPERIMENT, "usage": REANALYSIS},
                    {"origin_id": "experiment:Y", "origin_kind": EXPERIMENT, "usage": REANALYSIS},
                ],
            },
        ],
        claim_mode=EMPIRICAL,
        min_origin_groups=2,
    )

    expected_authority = {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    results = {
        "shared_dataset": shared_dataset,
        "distinct_origins": distinct_origins,
        "unknown_origin": unknown_origin,
        "multi_origin_bridge": bridge_case,
    }
    checks = {
        "shared_dataset_collapses_to_one_lineage": (
            shared_dataset["state"] == ORIGIN_POLICY_INSUFFICIENT
            and shared_dataset["origin_lineage_group_count"] == 1
        ),
        "distinct_origins_satisfy_two_group_gate": (
            distinct_origins["state"] == ORIGIN_POLICY_SUFFICIENT
            and distinct_origins["origin_lineage_group_count"] == 2
        ),
        "unknown_origin_fails_closed": unknown_origin["state"] == ORIGIN_UNKNOWN_FAIL_CLOSED,
        "multi_origin_bridge_collapses_components": (
            bridge_case["state"] == ORIGIN_POLICY_INSUFFICIENT
            and bridge_case["origin_lineage_group_count"] == 1
        ),
        "authority_fail_closed": all(row["authority"] == expected_authority for row in results.values()),
    }

    receipt = {
        "schema": "GREMLIN_EVIDENCE_ORIGIN_LINEAGE_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "cases": results,
        "scope": "DETERMINISTIC_LINEAGE_CONTRACT_VALIDATION_ONLY",
        "external_benchmark_claimed": False,
        "automatic_origin_inference_executed": False,
        "independence_proof_claimed": False,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
