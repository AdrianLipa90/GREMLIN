#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.web import fetch_url, research

DEFAULT_QUERY = "information geometry quantum gravity Shannon entropy"
FETCH_PROBE_URL = "https://api.crossref.org/works?rows=1"


def main() -> int:
    parser = argparse.ArgumentParser(description="GREMLIN live internet research probe")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="artifacts/gremlin_web_live_receipt.json")
    args = parser.parse_args()

    result = research(
        args.query,
        providers=["crossref", "arxiv"],
        limit_per_provider=args.limit,
        max_species=4,
    )
    fetch = fetch_url(FETCH_PROBE_URL, max_bytes=250_000, max_chars=2_000)

    evidence = result["evidence"]
    top = [
        {
            "provider": row.get("provider"),
            "title": row.get("title"),
            "url": row.get("url"),
            "published": row.get("published"),
        }
        for row in evidence.get("results", [])[:8]
    ]
    provider_count = len(evidence.get("providers_completed", []))
    result_count = int(evidence.get("deduped_result_count", 0))
    verdict = "PASS" if provider_count >= 1 and result_count >= 3 and fetch.get("http_status") == 200 else "FAIL"

    receipt = {
        "schema": "GREMLIN_WEB_LIVE_PROBE_V0_1",
        "query": args.query,
        "verdict": verdict,
        "octopus_route_mask": result["octopus"]["route_mask"],
        "octopus_route_commitment": result["octopus"]["route_commitment"],
        "providers_requested": evidence.get("providers_requested", []),
        "providers_completed": evidence.get("providers_completed", []),
        "provider_errors": evidence.get("provider_errors", []),
        "raw_result_count": evidence.get("raw_result_count", 0),
        "deduped_result_count": result_count,
        "top_results": top,
        "evidence_commitment": evidence.get("evidence_commitment"),
        "research_commitment": result.get("research_commitment"),
        "fetch_probe": {
            "url": FETCH_PROBE_URL,
            "http_status": fetch.get("http_status"),
            "content_type": fetch.get("content_type"),
            "bytes": fetch.get("bytes"),
            "sha256": fetch.get("sha256"),
            "receipt_commitment": fetch.get("receipt_commitment"),
        },
        "authority": result["authority"],
    }

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
