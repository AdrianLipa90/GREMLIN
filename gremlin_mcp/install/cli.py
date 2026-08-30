from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .config import load_effective_config
from .doctor import run_doctor
from .paths import resolve_paths


DEFAULT_CONFIG_TEXT = """schema = \"GREMLIN_CONFIG_V0_1\"\n\n[runtime]\ntransport = \"stdio\"\nstate = \"auto\"\n\n[network]\ninternet = true\nlocal_http = false\n\n[research]\nmax_workers = 4\nmax_sources = 24\n\n[logging]\nlevel = \"info\"\n"""


def _emit(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
            else:
                print(f"{key}: {value}")
    else:
        print(payload)


def _paths(args: argparse.Namespace) -> int:
    payload = resolve_paths(platform=args.platform).as_dict()
    _emit(payload, as_json=args.json)
    return 0


def _config_show(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    payload = load_effective_config(
        user_config_path=paths.config_file,
        machine_policy_path=paths.machine_policy_file,
    )
    _emit(payload, as_json=args.json)
    return 0


def _doctor(args: argparse.Namespace) -> int:
    payload = run_doctor(platform=args.platform)
    _emit(payload, as_json=args.json)
    return 1 if payload["status"] == "FAIL" else 0


def _init(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    for directory in (paths.config_dir, paths.state_dir, paths.cache_dir, paths.data_dir, paths.logs_dir, paths.diagnostics_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    config_path = Path(paths.config_file)
    created = False
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
        created = True
    payload = {
        "schema": "GREMLIN_INSTALL_INIT_V0_1",
        "status": "READY",
        "config_created": created,
        "paths": paths.as_dict(),
    }
    _emit(payload, as_json=args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN installation and diagnostics control utility")
    sub = parser.add_subparsers(dest="command", required=True)

    paths = sub.add_parser("paths", help="show canonical GREMLIN installation/user-data paths")
    paths.add_argument("--platform", choices=("windows", "linux"))
    paths.add_argument("--json", action="store_true")
    paths.set_defaults(func=_paths)

    init = sub.add_parser("init", help="create GREMLIN user directories and a default config without overwriting")
    init.add_argument("--platform", choices=("windows", "linux"))
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=_init)

    config = sub.add_parser("config", help="inspect effective operational configuration")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    show = config_sub.add_parser("show", help="show effective config after env/policy precedence")
    show.add_argument("--platform", choices=("windows", "linux"))
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_config_show)

    doctor = sub.add_parser("doctor", help="run sanitized installation/product diagnostics")
    doctor.add_argument("--platform", choices=("windows", "linux"))
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
