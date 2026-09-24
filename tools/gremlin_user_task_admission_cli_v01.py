from __future__ import annotations

import argparse
import json
import sys

from gremlin_mcp.user_task_admission import build_user_turn_admission


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one read-only GREMLIN + PhaseNav user-turn admission preflight."
    )
    parser.add_argument("--surface-root", default="/dev/shm/ciel_noema")
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise SystemExit("stdin must contain one JSON object")
    result = build_user_turn_admission(
        str(payload.get("prompt") or ""),
        current_task=payload.get("current_task"),
        active_path=payload.get("active_path"),
        recent_summary=payload.get("recent_summary"),
        request_id=payload.get("request_id"),
        surface_root=args.surface_root,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
