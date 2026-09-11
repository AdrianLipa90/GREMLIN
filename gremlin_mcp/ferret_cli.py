from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .ferret import (
    complete_human_handoff,
    detect_human_gate,
    prepare_action,
    prepare_human_handoff,
)
from .ferret_playwright import (
    FerretBrowserSessionError,
    collect_page_observation,
    open_headed_browser_for_handoff,
    persist_storage_state,
    wait_for_human_gate_clear,
)


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)


def handoff(args: argparse.Namespace) -> int:
    url = str(args.url).strip()
    state_path = Path(args.state_path).expanduser().resolve()
    preview = prepare_action(
        {
            "target_url": url,
            "intent": "Human verification handoff for a FERRET browser session",
            "steps": [
                {"action": "navigate", "url": url},
                {"action": "snapshot", "label": "post-human-gate"},
            ],
        }
    )

    session = open_headed_browser_for_handoff(url)
    pw = session["playwright"]
    browser = session["browser"]
    context = session["context"]
    page = session["page"]
    try:
        observation = collect_page_observation(page)
        gate = detect_human_gate(observation)
        if gate is None:
            state_receipt = persist_storage_state(context, state_path)
            print(
                _json(
                    {
                        "schema": "GREMLIN_FERRET_HANDOFF_CLI_V0_1",
                        "status": "NO_HUMAN_GATE_DETECTED",
                        "preview_commitment": preview["preview_commitment"],
                        "storage_state": state_receipt,
                        "automated_solution_attempted": False,
                    }
                )
            )
            return 0

        handoff_receipt = prepare_human_handoff(
            preview,
            gate,
            resolved_url=page.url,
        )
        print(_json(handoff_receipt), flush=True)
        print(
            "FERRET paused. Complete the site's verification manually in the visible browser window. "
            "FERRET will only observe whether the gate has cleared.",
            file=sys.stderr,
            flush=True,
        )

        clear_receipt = wait_for_human_gate_clear(
            page,
            observe=collect_page_observation,
            timeout_s=float(args.timeout),
            poll_ms=int(args.poll_ms),
        )
        state_receipt = persist_storage_state(context, state_path)
        resume_receipt = complete_human_handoff(
            handoff_receipt,
            actor=str(args.actor),
            completed=True,
            resolved_url=page.url,
            storage_state_sha256=state_receipt["sha256"],
        )
        print(
            _json(
                {
                    "schema": "GREMLIN_FERRET_HANDOFF_CLI_V0_1",
                    "status": "READY_TO_RESUME",
                    "gate_clear": clear_receipt,
                    "storage_state": state_receipt,
                    "resume": resume_receipt,
                    "next_step": "REOBSERVE_THEN_PREPARE_NEW_EXACT_ACTION_PREVIEW",
                }
            )
        )
        return 0
    finally:
        try:
            context.close()
        finally:
            try:
                browser.close()
            finally:
                pw.stop()


def observe(args: argparse.Namespace) -> int:
    session = open_headed_browser_for_handoff(
        str(args.url),
        storage_state=args.state_path,
    )
    pw = session["playwright"]
    browser = session["browser"]
    context = session["context"]
    page = session["page"]
    try:
        observation = collect_page_observation(page)
        gate = detect_human_gate(observation)
        print(
            _json(
                {
                    "schema": "GREMLIN_FERRET_OBSERVE_CLI_V0_1",
                    "resolved_url": page.url,
                    "gate": gate,
                    "cookies_returned": False,
                    "storage_state_returned": False,
                }
            )
        )
        return 0
    finally:
        try:
            context.close()
        finally:
            try:
                browser.close()
            finally:
                pw.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gremlin-ferret",
        description="FERRET local browser handoff utility",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_handoff = sub.add_parser(
        "handoff",
        help="open a visible browser, pause for human verification, and save exact session state",
    )
    p_handoff.add_argument("--url", required=True)
    p_handoff.add_argument("--actor", required=True)
    p_handoff.add_argument("--state-path", required=True)
    p_handoff.add_argument("--timeout", type=float, default=300.0)
    p_handoff.add_argument("--poll-ms", type=int, default=500)
    p_handoff.set_defaults(func=handoff)

    p_observe = sub.add_parser(
        "observe",
        help="open a visible browser using an optional saved state and report gate metadata",
    )
    p_observe.add_argument("--url", required=True)
    p_observe.add_argument("--state-path")
    p_observe.set_defaults(func=observe)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(int(args.func(args)))
    except FerretBrowserSessionError as exc:
        parser.exit(2, f"FERRET browser error: {exc}\n")


if __name__ == "__main__":
    main()
