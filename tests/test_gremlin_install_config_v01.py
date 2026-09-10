from __future__ import annotations

import os

import pytest

from gremlin_mcp.install.config import load_effective_config, validate_runtime_config


def test_config_precedence_user_then_env_then_cli(tmp_path) -> None:
    user = tmp_path / "config.toml"
    user.write_text(
        """schema = \"GREMLIN_CONFIG_V0_1\"\n[research]\nmax_workers = 8\nmax_sources = 40\n[logging]\nlevel = \"warning\"\n""",
        encoding="utf-8",
    )
    config = load_effective_config(
        user_config_path=user,
        env={"GREMLIN_MAX_WORKERS": "6", "GREMLIN_LOG_LEVEL": "error"},
        cli_overrides={"research": {"max_workers": 5}},
    )
    assert config["research"]["max_workers"] == 5
    assert config["research"]["max_sources"] == 40
    assert config["logging"]["level"] == "error"


def test_machine_policy_can_only_reduce_selected_capabilities(tmp_path) -> None:
    user = tmp_path / "config.toml"
    user.write_text(
        """schema = \"GREMLIN_CONFIG_V0_1\"\n[network]\ninternet = true\nlocal_http = true\n[research]\nmax_workers = 32\nmax_sources = 200\n""",
        encoding="utf-8",
    )
    policy = tmp_path / "policy.toml"
    policy.write_text(
        """[network]\ninternet = false\nlocal_http = false\n[research]\nmax_workers = 4\nmax_sources = 24\n[runtime]\nforce_transport = \"stdio\"\n""",
        encoding="utf-8",
    )
    config = load_effective_config(
        user_config_path=user,
        machine_policy_path=policy,
        env={"GREMLIN_MAX_WORKERS": "64", "GREMLIN_LOCAL_HTTP": "true"},
    )
    assert config["network"]["internet"] is False
    assert config["network"]["local_http"] is False
    assert config["research"]["max_workers"] == 4
    assert config["research"]["max_sources"] == 24
    assert config["runtime"]["transport"] == "stdio"


def test_string_false_in_user_config_is_rejected_instead_of_becoming_truthy(tmp_path) -> None:
    user = tmp_path / "config.toml"
    user.write_text(
        """schema = \"GREMLIN_CONFIG_V0_1\"\n[network]\ninternet = \"false\"\n""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="network.internet must be boolean"):
        load_effective_config(user_config_path=user, env={})


def test_string_false_in_machine_policy_is_rejected_instead_of_failing_open(tmp_path) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("""[network]\ninternet = \"false\"\n""", encoding="utf-8")
    with pytest.raises(ValueError, match="machine policy.network.internet must be boolean"):
        load_effective_config(machine_policy_path=policy, env={})


def test_fractional_worker_limit_is_rejected_instead_of_truncated() -> None:
    malformed = {
        "schema": "GREMLIN_CONFIG_V0_1",
        "runtime": {"transport": "stdio", "state": "auto"},
        "network": {"internet": True, "local_http": False},
        "research": {"max_workers": 4.9, "max_sources": 24},
        "logging": {"level": "info"},
    }
    with pytest.raises(ValueError, match="research.max_workers must be an integer"):
        validate_runtime_config(malformed)


def test_unknown_config_key_is_rejected_instead_of_silently_ignored(tmp_path) -> None:
    user = tmp_path / "config.toml"
    user.write_text(
        """schema = \"GREMLIN_CONFIG_V0_1\"\n[research]\nmax_worker = 1\n""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported keys"):
        load_effective_config(user_config_path=user, env={})


def test_unknown_machine_policy_key_is_rejected_instead_of_silently_ignored(tmp_path) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("""[network]\ninternett = false\n""", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported keys"):
        load_effective_config(machine_policy_path=policy, env={})


def test_non_string_environment_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="environment value must be a string"):
        load_effective_config(env={"GREMLIN_INTERNET": False})  # type: ignore[dict-item]


def test_decimal_environment_limits_reject_signs_and_fractional_values() -> None:
    with pytest.raises(ValueError, match="positive decimal integer"):
        load_effective_config(env={"GREMLIN_MAX_WORKERS": "4.0"})
    with pytest.raises(ValueError, match="positive decimal integer"):
        load_effective_config(env={"GREMLIN_MAX_WORKERS": "+4"})


def test_existing_config_directory_is_not_silently_treated_as_missing(tmp_path) -> None:
    user = tmp_path / "config.toml"
    user.mkdir()
    with pytest.raises(ValueError, match="must be a regular file"):
        load_effective_config(user_config_path=user, env={})


def test_existing_policy_directory_is_not_silently_treated_as_missing(tmp_path) -> None:
    policy = tmp_path / "policy.toml"
    policy.mkdir()
    with pytest.raises(ValueError, match="must be a regular file"):
        load_effective_config(machine_policy_path=policy, env={})


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows CI")
def test_broken_config_symlink_is_not_silently_treated_as_missing(tmp_path) -> None:
    target = tmp_path / "missing.toml"
    link = tmp_path / "config.toml"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="broken symlink"):
        load_effective_config(user_config_path=link, env={})
