from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .config import load_effective_config
from .device import build_activation_request, device_identity_status, ensure_device_identity
from .doctor import run_doctor
from .integrations import gremlin_stdio_entry, inspect_json_mcp, install_json_mcp, remove_json_mcp
from .license_activation import activate_license_key, import_license_file, installed_license_status
from .paths import resolve_paths
from .provider_integrations import connect_provider, disconnect_provider, list_providers, test_provider
from .readiness import evaluate_readiness
from .secrets import resolve_secret_store, secret_store_status


DEFAULT_CONFIG_TEXT = """schema = \"GREMLIN_CONFIG_V0_1\"\n\n[runtime]\ntransport = \"stdio\"\nstate = \"auto\"\n\n[network]\ninternet = true\nlocal_http = false\n\n[research]\nmax_workers = 4\nmax_sources = 24\n\n[logging]\nlevel = \"info\"\n"""
PROVIDER_IDS = (
    "codex", "opencode", "claude-code", "claude-desktop",
    "gemini", "cursor", "vscode", "windsurf",
)


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
    _emit(resolve_paths(platform=args.platform).as_dict(), as_json=args.json)
    return 0


def _config_show(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    payload = load_effective_config(user_config_path=paths.config_file, machine_policy_path=paths.machine_policy_file)
    _emit(payload, as_json=args.json)
    return 0


def _doctor(args: argparse.Namespace) -> int:
    payload = run_doctor(platform=args.platform)
    _emit(payload, as_json=args.json)
    return 1 if payload["status"] == "FAIL" else 0


def _ready(args: argparse.Namespace) -> int:
    payload = evaluate_readiness(resolve_paths(platform=args.platform))
    _emit(payload, as_json=args.json)
    return 0 if payload["status"] == "READY" else 1


def _init(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    for directory in (paths.config_dir, paths.state_dir, paths.cache_dir, paths.data_dir, paths.logs_dir, paths.diagnostics_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    config_path = Path(paths.config_file)
    created = False
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
        created = True
    _emit({"schema": "GREMLIN_INSTALL_INIT_V0_1", "status": "READY", "config_created": created, "paths": paths.as_dict()}, as_json=args.json)
    return 0


def _license_status(args: argparse.Namespace) -> int:
    payload = installed_license_status(resolve_paths(platform=args.platform))
    _emit(payload, as_json=args.json)
    return 0 if payload.get("status") == "ACTIVE" else 1


def _license_activate(args: argparse.Namespace) -> int:
    if bool(args.stdin) == bool(args.key_file):
        raise SystemExit("choose exactly one of --stdin or --key-file")
    key = sys.stdin.read().strip() if args.stdin else Path(args.key_file).read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("license key is empty")
    result = activate_license_key(key, resolve_paths(platform=args.platform))
    _emit(result.as_dict(), as_json=args.json)
    return 0


def _license_import(args: argparse.Namespace) -> int:
    result = import_license_file(args.file, resolve_paths(platform=args.platform))
    _emit(result.as_dict(), as_json=args.json)
    return 0


def _device_status(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    store_state = secret_store_status(paths)
    if not bool(store_state.get("available")):
        payload = {"schema": "GREMLIN_DEVICE_STATUS_V0_1", "status": "SECRET_STORE_UNAVAILABLE", "secret_store": store_state, "identity": None}
    else:
        store = resolve_secret_store(paths)
        payload = {"schema": "GREMLIN_DEVICE_STATUS_V0_1", "status": "READY", "secret_store": store_state, "identity": device_identity_status(store)}
    _emit(payload, as_json=args.json)
    return 0


def _device_init(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    _emit(ensure_device_identity(resolve_secret_store(paths)), as_json=args.json)
    return 0


def _device_activation_request(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    payload = build_activation_request(license_id=args.license_id, store=resolve_secret_store(paths))
    _emit(payload, as_json=args.json)
    return 0


def _integration_inspect(args: argparse.Namespace) -> int:
    _emit(inspect_json_mcp(args.config, server_name=args.server_name), as_json=args.json)
    return 0


def _integration_install(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    receipt = install_json_mcp(client_id=args.client_id, config_path=args.config, entry=gremlin_stdio_entry(paths), backup_root=Path(paths.data_dir) / "integration-backups", server_name=args.server_name)
    _emit(receipt.as_dict(), as_json=args.json)
    return 0


def _integration_remove(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    receipt = remove_json_mcp(client_id=args.client_id, config_path=args.config, backup_root=Path(paths.data_dir) / "integration-backups", server_name=args.server_name)
    _emit(receipt.as_dict(), as_json=args.json)
    return 0


def _providers_list(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    _emit(list_providers(paths), as_json=args.json)
    return 0


def _provider_action(args: argparse.Namespace) -> int:
    paths = resolve_paths(platform=args.platform)
    if args.provider_action == "connect":
        result = connect_provider(args.provider, paths)
    elif args.provider_action == "disconnect":
        result = disconnect_provider(args.provider, paths)
    else:
        result = test_provider(args.provider, paths)
    _emit(result.as_dict(), as_json=args.json)
    return 0 if result.status not in {"NOT_CONNECTED"} else 1


def _integration_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client-id", default="generic-json-mcp")
    parser.add_argument("--config", required=True, help="path to a JSON MCP client configuration")
    parser.add_argument("--server-name", default="gremlin")
    parser.add_argument("--platform", choices=("windows", "linux"))
    parser.add_argument("--json", action="store_true")


def _provider_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("provider", choices=PROVIDER_IDS)
    parser.add_argument("--platform", choices=("windows", "linux"))
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(func=_provider_action)


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

    license_cmd = sub.add_parser("license", help="activate or inspect the installed GREMLIN entitlement")
    license_sub = license_cmd.add_subparsers(dest="license_command", required=True)
    license_status = license_sub.add_parser("status", help="verify the installed signed license")
    license_status.add_argument("--platform", choices=("windows", "linux"))
    license_status.add_argument("--json", action="store_true")
    license_status.set_defaults(func=_license_status)
    license_activate = license_sub.add_parser("activate", help="verify and install a GRM1 customer license key")
    license_activate.add_argument("--stdin", action="store_true", help="read the GRM1 key from stdin so it is not exposed in the process list")
    license_activate.add_argument("--key-file", help="read a GRM1 key from a local text file")
    license_activate.add_argument("--platform", choices=("windows", "linux"))
    license_activate.add_argument("--json", action="store_true")
    license_activate.set_defaults(func=_license_activate)
    license_import = license_sub.add_parser("import", help="verify and install a signed license.json file")
    license_import.add_argument("file")
    license_import.add_argument("--platform", choices=("windows", "linux"))
    license_import.add_argument("--json", action="store_true")
    license_import.set_defaults(func=_license_import)

    config = sub.add_parser("config", help="inspect effective operational configuration")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    show = config_sub.add_parser("show", help="show effective config after env/policy precedence")
    show.add_argument("--platform", choices=("windows", "linux"))
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_config_show)

    device = sub.add_parser("device", help="manage the installation Ed25519 identity")
    device_sub = device.add_subparsers(dest="device_command", required=True)
    device_status = device_sub.add_parser("status", help="show secret-store and device identity status")
    device_status.add_argument("--platform", choices=("windows", "linux"))
    device_status.add_argument("--json", action="store_true")
    device_status.set_defaults(func=_device_status)
    device_init = device_sub.add_parser("init", help="create or recover the installation identity in OS secret storage")
    device_init.add_argument("--platform", choices=("windows", "linux"))
    device_init.add_argument("--json", action="store_true")
    device_init.set_defaults(func=_device_init)
    activation_request = device_sub.add_parser("activation-request", help="create a signed device activation proof")
    activation_request.add_argument("--license-id", required=True)
    activation_request.add_argument("--platform", choices=("windows", "linux"))
    activation_request.add_argument("--json", action="store_true")
    activation_request.set_defaults(func=_device_activation_request)

    integrations = sub.add_parser("integrations", help="connect GREMLIN to supported AI clients or custom MCP configs")
    integrations_sub = integrations.add_subparsers(dest="integration_command", required=True)

    providers = integrations_sub.add_parser("providers", help="discover supported AI clients and show MCP connection status")
    providers.add_argument("--platform", choices=("windows", "linux"))
    providers.add_argument("--json", action="store_true")
    providers.set_defaults(func=_providers_list)

    for action in ("connect", "disconnect", "test"):
        provider = integrations_sub.add_parser(action, help=f"{action} a supported AI client")
        _provider_common(provider)
        provider.set_defaults(provider_action=action)

    inspect = integrations_sub.add_parser("inspect", help="inspect a generic JSON MCP configuration")
    inspect.add_argument("--config", required=True)
    inspect.add_argument("--server-name", default="gremlin")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=_integration_inspect)
    install = integrations_sub.add_parser("install", help="advanced: backup, merge and verify a generic JSON MCP config")
    _integration_common(install)
    install.set_defaults(func=_integration_install)
    remove = integrations_sub.add_parser("remove", help="advanced: remove GREMLIN from a generic JSON MCP config")
    _integration_common(remove)
    remove.set_defaults(func=_integration_remove)

    ready = sub.add_parser("ready", help="return one customer-facing READY / ACTION_REQUIRED verdict")
    ready.add_argument("--platform", choices=("windows", "linux"))
    ready.add_argument("--json", action="store_true")
    ready.set_defaults(func=_ready)

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
