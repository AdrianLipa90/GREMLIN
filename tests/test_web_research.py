from __future__ import annotations

import pytest

import gremlin_mcp.web as web


def test_validate_url_rejects_non_https() -> None:
    with pytest.raises(web.WebAccessError, match="HTTPS"):
        web.validate_url("http://example.com/")


def test_validate_url_rejects_loopback() -> None:
    with pytest.raises(web.WebAccessError, match="non-public"):
        web.validate_url("https://127.0.0.1/")


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
        }

    monkeypatch.setattr(web, "_request_bytes", fake_request)
    result = web.fetch_url("https://example.org/evidence")
    assert result["http_status"] == 200
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
    assert result["authority"] == {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }
    assert len(result["research_commitment"]) == 64
