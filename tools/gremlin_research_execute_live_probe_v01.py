#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gremlin_mcp.research_executor import execute_research

DEFAULT_QUERY = (
    "audit evidence contradictions dependencies graph derive relation between "
    "Shannon entropy information geometry and quantum gravity"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="GREMLIN live executable research probe")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="artifacts/gremlin_research_execute_live.json")
    args = parser.parse_args()

    result = execute_research(
        args.query,
        providers=["crossref", "arxiv"],
        limit_per_provider=args.limit,
        max_species=4,
        max_sources=10,
    )
    stages = result.get("stage_executions", [])
    species_union: list[str] = []
    for stage in stages:
        for species in stage.get("route_mask", []):
            if species not in species_union:
                species_union.append(species)

    synthesis = result.get("synthesis") or {}
    candidate = synthesis.get("result") or {}
    required = {"OWL", "SPIDER", "MOLE", "HOUND"}
    verdict = "PASS" if (
        result.get("status") == "CANDIDATE_SYNTHESIS_READY"
        and synthesis.get("state") == "DONE"
        and synthesis.get("species") == "BELZEBUB"
        and required.issubset(set(species_union))
        and len(result.get("citations", [])) >= 3
        and result.get("worker_abi_exercised") is True
        and candidate.get("epistemic_status") == "CANDIDATE_SYNTHESIS"
        and candidate.get("authority", {}).get("canon_allowed") is False
    ) else "FAIL"

    receipt = {
        "schema": "GREMLIN_RESEARCH_EXECUTE_LIVE_PROBE_V0_1",
        "query": args.query,
        "verdict": verdict,
        "status": result.get("status"),
        "species_union": species_union,
        "stages": [
            {
                "stage_id": stage.get("stage_id"),
                "status": stage.get("status"),
                "route_mask": stage.get("route_mask"),
                "task_count": len(stage.get("task_ids", [])),
            }
            for stage in stages
        ],
        "source_count": len(result.get("citations", [])),
        "providers_completed": result.get("acquisition", {}).get("evidence", {}).get("providers_completed", []),
        "provider_errors": result.get("acquisition", {}).get("evidence", {}).get("provider_errors", []),
        "worker_abi_exercised": result.get("worker_abi_exercised"),
        "belzebub_state": synthesis.get("state"),
        "belzebub_candidate": candidate,
        "citations": result.get("citations", [])[:10],
        "execution_commitment": result.get("execution_commitment"),
        "research_commitment": result.get("acquisition", {}).get("research_commitment"),
        "authority": result.get("authority"),
    }

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
