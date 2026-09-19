from __future__ import annotations

import hashlib
import json
from pathlib import Path

import gremlin_mcp.install.support_report as support
from gremlin_mcp.install.paths import resolve_paths


def _paths(tmp_path: Path):
    home = tmp_path / "alice"
    home.mkdir()
    return resolve_paths(
        platform="linux",
        env={
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".data"),
        },
    )


def test_support_report_redacts_paths_and_excludes_provider_command_details(tmp_path, monkeypatch) -> None:
    paths = _paths(tmp_path)
    home = str(tmp_path / "alice")
    env = {"HOME": home}

    monkeypatch.setattr(
        support,
        "run_doctor",
        lambda **_kwargs: {
            "schema": "GREMLIN_DOCTOR_V0_1",
            "status": "WARN",
            "counts": {"PASS": 2, "WARN": 1, "FAIL": 0},
            "checks": [
                {"check": "paths", "status": "PASS", "detail": f"resolved under {home}/.config/gremlin"},
                {"check": "license", "status": "WARN", "detail": "no product license configured"},
            ],
            "product": {"status": "BLOCKED", "reason": "LICENSE_REQUIRED", "license_id": "secret-license-id"},
            "secret_store": {"backend": "TEST", "available": True, "private_material": "never-share"},
        },
    )
    monkeypatch.setattr(
        support,
        "evaluate_readiness",
        lambda _paths: {
            "status": "ACTION_REQUIRED",
            "runtime": {"available": True, "command": "/usr/bin/gremlin-product-mcp", "transport": "stdio"},
            "providers": {"detected": 1, "connected": 0, "connected_ids": [], "unverified": 1, "unverified_ids": ["codex"]},
            "profile": {"configured": False, "path": f"{home}/.config/gremlin/client-profile.json"},
            "actions": ["Activate your GREMLIN license"],
        },
    )
    monkeypatch.setattr(
        support,
        "list_providers",
        lambda _paths, env=None: {
            "providers": [{
                "provider_id": "codex",
                "display_name": "OpenAI Codex",
                "detected": True,
                "connected": False,
                "connection_status": "REGISTERED_UNVERIFIED",
                "integration_mode": "NATIVE_CLI",
                "executable": f"{home}/bin/codex",
                "config_path": f"{home}/.codex/config.toml",
                "detail": "token=do-not-share",
            }],
        },
    )

    report = support.build_support_report(paths, env=env)
    serialized = json.dumps(report, sort_keys=True)

    assert report["schema"] == "GREMLIN_SUPPORT_REPORT_V0_1"
    assert report["privacy"] == {
        "license_key_included": False,
        "absolute_paths_included": False,
        "provider_command_output_included": False,
        "config_contents_included": False,
    }
    assert report["providers"][0] == {
        "provider_id": "codex",
        "display_name": "OpenAI Codex",
        "detected": True,
        "connected": False,
        "connection_status": "REGISTERED_UNVERIFIED",
        "integration_mode": "NATIVE_CLI",
    }
    assert home not in serialized
    assert "secret-license-id" not in serialized
    assert "never-share" not in serialized
    assert "do-not-share" not in serialized
    assert "<path>" in serialized
    assert len(report["report_commitment"]) == 64


def _sealed_fixture(**extra):
    core = {
        "schema": "GREMLIN_SUPPORT_REPORT_V0_1",
        "status": "fixture",
        **extra,
    }
    commitment = hashlib.blake2b(
        support.DOMAIN + support._canonical(core),
        digest_size=32,
    ).hexdigest()
    return {**core, "report_commitment": commitment}


def test_support_report_write_uses_canonical_diagnostics_directory(tmp_path) -> None:
    paths = _paths(tmp_path)
    report = _sealed_fixture()
    target = support.write_support_report(paths, report)
    assert target.parent == Path(paths.diagnostics_dir)
    assert target.is_file()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == report


def test_support_report_write_rejects_tampered_payload(tmp_path) -> None:
    paths = _paths(tmp_path)
    report = _sealed_fixture()
    report["status"] = "tampered"
    try:
        support.write_support_report(paths, report)
    except ValueError as exc:
        assert "commitment mismatch" in str(exc)
    else:
        raise AssertionError("tampered support report was persisted")
