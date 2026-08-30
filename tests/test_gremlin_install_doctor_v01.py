from __future__ import annotations

from pathlib import Path

from gremlin_mcp.install.doctor import run_doctor
from gremlin_mcp.install.paths import resolve_paths


def test_doctor_is_sanitized_and_warns_before_activation(tmp_path) -> None:
    env = {"HOME": str(tmp_path)}
    payload = run_doctor(platform="linux", env=env)
    assert payload["schema"] == "GREMLIN_DOCTOR_V0_1"
    assert payload["status"] == "WARN"
    assert payload["counts"]["FAIL"] == 0
    license_checks = [row for row in payload["checks"] if row["check"] == "license"]
    assert license_checks[0]["status"] == "WARN"
    serialized = str(payload)
    assert "PRIVATE KEY" not in serialized.upper()
    assert "GREMLIN_LICENSE_KEY" not in serialized


def test_doctor_fails_on_invalid_user_config(tmp_path) -> None:
    env = {"HOME": str(tmp_path)}
    paths = resolve_paths(platform="linux", env=env)
    Path(paths.config_dir).mkdir(parents=True)
    Path(paths.config_file).write_text(
        """schema = \"GREMLIN_CONFIG_V0_1\"\n[runtime]\ntransport = \"public-internet\"\n""",
        encoding="utf-8",
    )
    payload = run_doctor(platform="linux", env=env)
    assert payload["status"] == "FAIL"
    config_checks = [row for row in payload["checks"] if row["check"] == "config"]
    assert config_checks[0]["status"] == "FAIL"
