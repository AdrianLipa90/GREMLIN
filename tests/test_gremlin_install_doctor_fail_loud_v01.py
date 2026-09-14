from __future__ import annotations

from pathlib import Path

import gremlin_mcp.install.doctor as doctor
from gremlin_mcp.install.paths import resolve_paths


def _env(tmp_path: Path) -> dict[str, str]:
    return {"HOME": str(tmp_path)}


def test_non_string_license_environment_value_is_reported_as_fail(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "secret_store_status", lambda _paths: {"available": False, "backend": "TEST"})
    payload = doctor.run_doctor(
        platform="linux",
        env={"HOME": str(tmp_path), "GREMLIN_LICENSE_PATH": 123},  # type: ignore[dict-item]
    )
    assert payload["status"] == "FAIL"
    check = next(row for row in payload["checks"] if row["check"] == "license")
    assert check["status"] == "FAIL"
    assert "environment value must be a string" in check["detail"]


def test_secret_store_truthy_string_does_not_become_pass(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "secret_store_status", lambda _paths: {"available": "false", "backend": "TEST"})
    payload = doctor.run_doctor(platform="linux", env=_env(tmp_path))
    check = next(row for row in payload["checks"] if row["check"] == "secret_store")
    assert check["status"] == "FAIL"
    assert payload["status"] == "FAIL"


def test_secret_store_exception_is_captured_as_fail_not_false_success(tmp_path, monkeypatch) -> None:
    def explode(_paths):
        raise RuntimeError("backend probe exploded")

    monkeypatch.setattr(doctor, "secret_store_status", explode)
    payload = doctor.run_doctor(platform="linux", env=_env(tmp_path))
    check = next(row for row in payload["checks"] if row["check"] == "secret_store")
    assert check["status"] == "FAIL"
    assert "status failed" in check["detail"]
    assert payload["secret_store"] is None


def test_product_runtime_nonobject_status_is_fail(tmp_path, monkeypatch) -> None:
    paths = resolve_paths(platform="linux", env=_env(tmp_path))
    Path(paths.config_dir).mkdir(parents=True, exist_ok=True)
    license_file = Path(paths.license_file)
    license_file.write_text("fixture", encoding="utf-8")

    monkeypatch.setattr(doctor, "secret_store_status", lambda _paths: {"available": False, "backend": "TEST"})
    monkeypatch.setattr(doctor, "_license_configuration", lambda _paths, _env: ("license", None, "pub", None))

    class Runtime:
        def status(self):
            return "LICENSED"

    monkeypatch.setattr(doctor.ProductRuntime, "from_configuration", lambda **kwargs: Runtime())
    payload = doctor.run_doctor(platform="linux", env=_env(tmp_path))
    check = next(row for row in payload["checks"] if row["check"] == "license")
    assert check["status"] == "FAIL"
    assert "non-object status" in check["detail"]


def test_product_runtime_status_exception_is_fail(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "secret_store_status", lambda _paths: {"available": False, "backend": "TEST"})
    monkeypatch.setattr(doctor, "_license_configuration", lambda _paths, _env: ("license", None, "pub", None))

    class Runtime:
        def status(self):
            raise RuntimeError("bad entitlement state")

    monkeypatch.setattr(doctor.ProductRuntime, "from_configuration", lambda **kwargs: Runtime())
    payload = doctor.run_doctor(platform="linux", env=_env(tmp_path))
    check = next(row for row in payload["checks"] if row["check"] == "license")
    assert check["status"] == "FAIL"
    assert "status failed" in check["detail"]


def test_product_runtime_initialization_exception_is_fail(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "secret_store_status", lambda _paths: {"available": False, "backend": "TEST"})
    monkeypatch.setattr(doctor, "_license_configuration", lambda _paths, _env: ("license", None, "pub", None))

    def explode(**kwargs):
        raise RuntimeError("bad key")

    monkeypatch.setattr(doctor.ProductRuntime, "from_configuration", explode)
    payload = doctor.run_doctor(platform="linux", env=_env(tmp_path))
    check = next(row for row in payload["checks"] if row["check"] == "license")
    assert check["status"] == "FAIL"
    assert "initialization failed" in check["detail"]
