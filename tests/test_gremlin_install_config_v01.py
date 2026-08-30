from __future__ import annotations

from gremlin_mcp.install.config import load_effective_config


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
