from __future__ import annotations

import pytest

from gremlin_mcp.source_family import (
    arxiv_work_id,
    bind_guard_evidence_to_families,
    derive_source_families,
    doi_from_url,
    normalize_doi,
    normalize_title,
    normalize_url,
    source_identity,
)


def _citation(source_id: object, *, title: object = "A sufficiently informative source title", url: object = "https://example.org/work", doi: object = None, published: object = "2026-08-30") -> dict[str, object]:
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": title,
        "url": url,
        "doi": doi,
        "published": published,
    }


def _guard(source_id: object, source_family: object = "producer-family") -> dict[str, object]:
    return {
        "evidence_id": source_id,
        "source_family": source_family,
        "stance": "SUPPORT",
        "payload_commitment": "payload",
    }


def test_normalizers_reject_non_string_metadata_instead_of_stringifying() -> None:
    with pytest.raises(ValueError, match="title must be a string or None"):
        normalize_title(123)
    with pytest.raises(ValueError, match="doi must be a string or None"):
        normalize_doi(123)
    with pytest.raises(ValueError, match="url must be a string or None"):
        doi_from_url(False)
    with pytest.raises(ValueError, match="url must be a string or None"):
        normalize_url(["https://example.org"])
    with pytest.raises(ValueError, match="arxiv value must be a string or None"):
        arxiv_work_id({"id": "2608.12345"})


def test_source_identity_rejects_non_mapping_and_non_string_fallback_id() -> None:
    with pytest.raises(ValueError, match="citation must be an object"):
        source_identity("bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="citation source_id must be a string"):
        source_identity({"source_id": 123, "title": None, "url": None, "doi": None})


def test_derive_source_families_rejects_bad_container_and_rows() -> None:
    with pytest.raises(ValueError, match="citations must be an iterable of objects"):
        derive_source_families("not-a-list")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="citations must contain only objects"):
        derive_source_families([_citation("a"), "bad-row"])  # type: ignore[list-item]


def test_derive_source_families_rejects_non_string_source_id() -> None:
    with pytest.raises(ValueError, match="citation source_id must be a string"):
        derive_source_families([_citation(123)])


def test_title_bridge_rejects_non_string_publication_metadata() -> None:
    title = "Exact informative shared title used for strict bridge validation"
    citations = [
        _citation("a", title=title, url="https://example.org/a", published=2026),
        _citation("b", title=title, url="https://example.org/b", published="2026-08-30"),
    ]
    with pytest.raises(ValueError, match="published must be a string or None"):
        derive_source_families(citations)


def test_bind_guard_rejects_non_string_declared_family() -> None:
    citations = [_citation("a", url="https://example.org/a")]
    with pytest.raises(ValueError, match="guard evidence source_family must be a string"):
        bind_guard_evidence_to_families([_guard("a", 42)], citations=citations)


def test_bind_guard_rejects_non_string_and_duplicate_evidence_ids() -> None:
    citations = [_citation("a", url="https://example.org/a")]
    with pytest.raises(ValueError, match="guard evidence evidence_id must be a string"):
        bind_guard_evidence_to_families([_guard(123)], citations=citations)

    with pytest.raises(ValueError, match="duplicate guard evidence evidence_id"):
        bind_guard_evidence_to_families(
            [_guard("a", "family-one"), _guard("a", "family-two")],
            citations=citations,
        )
