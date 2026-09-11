from __future__ import annotations

import socket

import pytest

import gremlin_mcp.ferret as ferret


def _minimal_request(**overrides):
    request = {
        "target_url": "https://example.com/form",
        "intent": "Test exact FERRET preview",
        "steps": [{"action": "navigate", "url": "https://example.com/form"}],
    }
    request.update(overrides)
    return request


def test_preview_rejects_non_string_boundary_values() -> None:
    with pytest.raises(ValueError, match="target_url must be a string"):
        ferret.prepare_action(_minimal_request(target_url=123))
    with pytest.raises(ValueError, match="intent must be a string"):
        ferret.prepare_action(_minimal_request(intent=123))
    with pytest.raises(ValueError, match="action must be a string"):
        ferret.prepare_action(
            _minimal_request(steps=[{"action": 123, "url": "https://example.com/form"}])
        )
    with pytest.raises(ValueError, match="selector must be a string"):
        ferret.prepare_action(
            _minimal_request(steps=[{"action": "click", "selector": 123}])
        )


def test_preview_rejects_truthy_non_boolean_controls() -> None:
    with pytest.raises(ValueError, match="secret must be boolean"):
        ferret.prepare_action(
            _minimal_request(
                steps=[{"action": "fill", "selector": "#x", "value": "v", "secret": 1}]
            )
        )
    with pytest.raises(ValueError, match="checked must be boolean"):
        ferret.prepare_action(
            _minimal_request(steps=[{"action": "check", "selector": "#x", "checked": 1}])
        )

    preview = ferret.prepare_action(_minimal_request())
    with pytest.raises(ValueError, match="approved must be boolean"):
        ferret.authorize_action(preview, actor="USER007", approved=1)  # type: ignore[arg-type]


def test_secret_fill_requires_reference_and_never_embeds_plaintext() -> None:
    with pytest.raises(ValueError, match="must not be embedded"):
        ferret.prepare_action(
            _minimal_request(
                steps=[
                    {
                        "action": "fill",
                        "selector": "#password",
                        "secret": True,
                        "value": "plaintext-secret",
                        "secret_ref": "account-password",
                    }
                ]
            )
        )
    with pytest.raises(ValueError, match="secret_ref"):
        ferret.prepare_action(
            _minimal_request(
                steps=[{"action": "fill", "selector": "#password", "secret": True}]
            )
        )

    preview = ferret.prepare_action(
        _minimal_request(
            steps=[
                {
                    "action": "fill",
                    "selector": "#password",
                    "secret": True,
                    "secret_ref": "account-password",
                }
            ]
        )
    )
    assert preview["steps"][0]["value"] == "<REDACTED>"
    assert preview["steps"][0]["secret_ref"] == "account-password"


def test_private_and_loopback_literal_targets_fail_closed() -> None:
    for url in (
        "https://127.0.0.1/",
        "https://10.0.0.1/",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::1]/",
        "https://[fc00::1]/",
    ):
        with pytest.raises(ValueError, match="non-public"):
            ferret.prepare_action(_minimal_request(target_url=url, steps=[{"action": "navigate", "url": url}]))


def test_transport_edge_rejects_dns_rebinding_to_private_address(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.10.10.10", 443))
        ],
    )
    with pytest.raises(ValueError, match="non-public"):
        ferret.validate_public_network_url("https://public-looking.example/path")


def test_transport_edge_accepts_only_all_public_dns_answers(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    assert ferret.validate_public_network_url("https://example.com/path") == "https://example.com/path"


def test_incomplete_or_malformed_gate_observation_does_not_mean_clear() -> None:
    with pytest.raises(ferret.FerretHandoffError, match="incomplete"):
        ferret.detect_human_gate(
            {
                "observation_complete": False,
                "body_text": "",
                "frames": [],
                "fields": [],
            }
        )
    with pytest.raises(ValueError, match="frames must be a list"):
        ferret.detect_human_gate({"frames": "not-a-list"})
    with pytest.raises(ValueError, match=r"frames\[0\]"):
        ferret.detect_human_gate({"frames": ["not-a-mapping"]})


def test_handoff_completion_rejects_truthy_non_boolean() -> None:
    preview = ferret.prepare_action(_minimal_request())
    gate = ferret.detect_human_gate(
        {
            "resolved_url": "https://example.com/form",
            "body_text": "verify you are human captcha",
            "frames": [],
            "fields": [],
        }
    )
    assert gate is not None
    handoff = ferret.prepare_human_handoff(
        preview, gate, resolved_url="https://example.com/form"
    )
    with pytest.raises(ValueError, match="completed must be boolean"):
        ferret.complete_human_handoff(
            handoff,
            actor="USER007",
            completed=1,  # type: ignore[arg-type]
            resolved_url="https://example.com/form",
            storage_state_sha256="a" * 64,
        )
