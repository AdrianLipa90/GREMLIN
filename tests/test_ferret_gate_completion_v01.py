from __future__ import annotations

from gremlin_mcp.ferret import detect_human_gate


def test_solved_hcaptcha_response_does_not_keep_gate_active() -> None:
    observation = {
        "resolved_url": "https://example.com/complaints",
        "title": "Complaint form",
        "body_text": "Tell us what went wrong",
        "frames": [
            {
                "name": "hcaptcha",
                "url": "https://newassets.hcaptcha.com/captcha/v1/abc/static/hcaptcha.html",
                "text": "I am human",
            }
        ],
        "fields": [
            {
                "tag": "textarea",
                "name": "h-captcha-response",
                "value_present": True,
            }
        ],
    }
    assert detect_human_gate(observation) is None


def test_solved_response_does_not_override_live_security_interstitial() -> None:
    observation = {
        "resolved_url": "https://example.com/complaints",
        "title": "Additional security check",
        "body_text": "Additional security check is required",
        "frames": [],
        "fields": [
            {
                "tag": "textarea",
                "name": "h-captcha-response",
                "value_present": True,
            }
        ],
    }
    gate = detect_human_gate(observation)
    assert gate is not None
    assert gate["gate_kind"] in {"CAPTCHA", "BOT_CHALLENGE"}
