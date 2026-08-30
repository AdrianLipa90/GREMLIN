from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.evidence_robustness import CONTRADICT, SUPPORT, score_paired_probe


def _evidence(evidence_id: str, source_family: str, stance: str, credibility: float) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "source_family": source_family,
        "stance": stance,
        "payload_commitment": f"synthetic:{evidence_id}",
        "credibility": credibility,
    }


def _case(index: int) -> dict[str, object]:
    prefix = f"case-{index}"
    clean = [
        _evidence(f"{prefix}-support-a", f"{prefix}-family-a", SUPPORT, 0.71 + index * 0.01),
        _evidence(f"{prefix}-support-b", f"{prefix}-family-b", SUPPORT, 0.75 + index * 0.01),
    ]
    noisy = clean + [
        _evidence(f"{prefix}-noise", f"{prefix}-authority-lookalike", CONTRADICT, 0.99),
    ]
    return {
        "claim_id": prefix,
        "clean_evidence": clean,
        "noisy_evidence": noisy,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/gremlin_paired_evidence_probe_v01.json")
    args = parser.parse_args()

    receipt = score_paired_probe([_case(index) for index in range(1, 7)])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "metrics": receipt["metrics"], "gates": receipt["gates"]}, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
