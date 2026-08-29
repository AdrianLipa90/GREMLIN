from __future__ import annotations

from email.message import Message
import urllib.error

import pytest

import gremlin_mcp.web as web


def test_validate_url_rejects_non_https() -> None:
    with pytest.raises(web.WebAccessError, match="HTTPS"):
        web.validate_url("http://example.com/")


def test_validate_url_rejects_loopback() -> None:
    with pytest.raises(web.WebAccessError, match="non-public"):
        web.validate_url("https://127.0.0.1/")


def test_request_bytes_retries_429(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status = 200

        def __init__(self) -> None:
            self.headers = Message()
            self.headers["Content-Type"] = "application/json; charset=utf-8"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, limit: int) -> bytes:
            return b'{"ok":true}'

        def geturl(self) -> str:
            return "https://example.org/data"

    class FakeOpener:
        def __init__(self) -> None:
            self.calls = 0

        def open(self, request, timeout: float):
            self.calls += 1
            if self.calls == 1:
                headers = Message()
                headers["Retry-After"] = "0"
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "Too Many Requests",
                    headers,
                    None,
                )
            return FakeResponse()

    opener = FakeOpener()
    monkeypatch.setattr(web, "validate_url", lambda url: str(url))
    monkeypatch.setattr(web, "_opener", lambda: opener)
    monkeypatch.setattr(web.time, "sleep", lambda seconds: None)

    body, meta = web._request_bytes("https://example.org/data", retries=2)
    assert body == b'{"ok":true}'
    assert opener.calls == 2
    assert meta["network_attempts"] == 2


def test_fetch_url_extracts_html_and_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    body = b"<html><body><h1>Evidence</h1><script>ignore()</script><p>alpha beta</p></body></html>"

    def fake_request(url: str, **kwargs):
        return body, {
            "url": "https://example.org/evidence",
            "status": 200,
            "content_type": "text/html",
            "charset": "utf-8",
            "content_length": len(body),
            "etag": None,
            "last_modified": None,
            "network_attempts": 1,
        }

    monkeypatch.setattr(web, "_request_bytes", fake_request)
    result = web.fetch_url("https://example.org/evidence")
    assert result["http_status"] == 200
    assert result["network_attempts"] == 1
    assert "Evidence" in result["text"]
    assert "alpha beta" in result["text"]
    assert "ignore" not in result["text"]
    assert len(result["sha256"]) == 64
    assert len(result["receipt_commitment"]) == 64
    assert result["authority"]["canon_allowed"] is False


def test_search_web_deduplicates_across_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_crossref(query: str, *, limit: int = 6):
        return {
            "provider": "crossref",
            "results": [
                {"provider": "crossref", "title": "Same Paper", "url": "https://doi.org/10.1/x", "doi": "10.1/x"},
                {"provider": "crossref", "title": "Other", "url": "https://example.org/other"},
            ],
        }

    def fake_arxiv(query: str, *, limit: int = 6):
        return {
            "provider": "arxiv",
            "results": [
                {"provider": "arxiv", "title": "Same Paper", "url": "https://doi.org/10.1/x", "doi": "10.1/x"},
            ],
        }

    monkeypatch.setattr(web, "search_crossref", fake_crossref)
    monkeypatch.setattr(web, "search_arxiv", fake_arxiv)
    result = web.search_web("phase geometry", providers=["crossref", "arxiv"], limit_per_provider=4)
    assert result["raw_result_count"] == 3
    assert result["deduped_result_count"] == 2
    assert result["providers_completed"] == ["crossref", "arxiv"]
    assert len(result["evidence_commitment"]) == 64


def test_search_web_records_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(query: str, *, limit: int = 6):
        raise web.WebAccessError("blocked")

    monkeypatch.setattr(web, "search_crossref", fail)
    result = web.search_web("test", providers=["crossref"], limit_per_provider=2)
    assert result["results"] == []
    assert result["providers_completed"] == []
    assert result["provider_errors"][0]["provider"] == "crossref"
    assert "WebAccessError" in result["provider_errors"][0]["error"]


def test_research_plan_decomposes_complex_query() -> None:
    query = (
        "audit evidence contradictions dependencies graph derive relation between "
        "Shannon entropy information geometry and quantum gravity"
    )
    plan = web.build_research_plan(query)
    stages = {stage["stage_id"]: stage for stage in plan["stages"]}

    assert set(stages) == {
        "ACQUIRE_EVIDENCE",
        "MAP_RELATIONS",
        "DERIVE_CANDIDATE",
        "ADVERSARIAL_CHECK",
    }
    assert "OWL" in stages["ACQUIRE_EVIDENCE"]["route_mask"]
    assert "SPIDER" in stages["MAP_RELATIONS"]["route_mask"]
    assert "MOLE" in stages["DERIVE_CANDIDATE"]["route_mask"]
    assert "HOUND" in stages["ADVERSARIAL_CHECK"]["route_mask"]
    assert {"OWL", "SPIDER", "MOLE", "HOUND"}.issubset(set(plan["species_union"]))
    assert len(plan["plan_commitment"]) == 64


def test_research_routes_and_keeps_candidate_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        web,
        "search_web",
        lambda query, **kwargs: {
            "schema": web.WEB_SCHEMA,
            "results": [{"provider": "arxiv", "title": "Candidate", "url": "https://arxiv.org/abs/1"}],
            "deduped_result_count": 1,
        },
    )
    result = web.research("derive information geometry evidence", providers=["arxiv"])
    assert result["status"] == "EVIDENCE_READY"
    assert "OWL" in result["octopus"]["route_mask"]
    assert "research_plan" in result
    assert "MOLE" in result["research_plan"]["species_union"]
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    assert len(result["research_commitment"]) == 64
