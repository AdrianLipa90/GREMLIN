from __future__ import annotations

from gremlin_mcp.source_family import (
    arxiv_work_id,
    bind_guard_evidence_to_families,
    derive_source_families,
    normalize_doi,
)


def _citation(source_id, *, title, url, doi=None):
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": title,
        "url": url,
        "doi": doi,
        "published": "2026-08-30",
    }


def _guard(source_id, declared_family):
    return {
        "evidence_id": source_id,
        "source_family": declared_family,
        "stance": "SUPPORT",
        "payload_commitment": f"payload:{source_id}",
    }


def test_arxiv_version_suffix_is_removed_from_work_identity():
    assert arxiv_work_id("https://arxiv.org/abs/2608.12345v1") == "2608.12345"
    assert arxiv_work_id("https://arxiv.org/pdf/2608.12345v7.pdf") == "2608.12345"
    assert arxiv_work_id("2608.12345v3") == "2608.12345"


def test_doi_normalization_removes_common_prefixes():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("doi:10.1000/ABC") == "10.1000/abc"


def test_same_work_title_across_providers_collapses_to_one_family():
    title = "A Modular Information Dynamical Bridge Between Quantum Systems and Geometry"
    citations = [
        _citation("crossref", title=title, url="https://doi.org/10.1000/example", doi="10.1000/example"),
        _citation("arxiv-v1", title=title, url="https://arxiv.org/abs/2608.12345v1"),
        _citation("arxiv-v2", title=title, url="https://arxiv.org/abs/2608.12345v2"),
    ]
    receipt = derive_source_families(citations)
    assert receipt["source_count"] == 3
    assert receipt["family_count"] == 1
    assert receipt["collapsed_duplicate_or_version_count"] == 2
    families = {row["family_id"] for row in receipt["families_by_source_id"].values()}
    assert len(families) == 1


def test_distinct_informative_titles_remain_distinct_families():
    citations = [
        _citation("a", title="Entropy constraints in emergent gravitational geometry", url="https://example.org/a"),
        _citation("b", title="Quantum control topology for open dynamical systems", url="https://example.org/b"),
    ]
    receipt = derive_source_families(citations)
    assert receipt["family_count"] == 2
    assert receipt["collapsed_duplicate_or_version_count"] == 0


def test_producer_declared_families_cannot_fake_independence_for_same_work():
    title = "Information Geometry and Entropy Relations in Quantum Gravity"
    citations = [
        _citation("v1", title=title, url="https://arxiv.org/abs/2608.54321v1"),
        _citation("v2", title=title, url="https://arxiv.org/abs/2608.54321v2"),
    ]
    bound = bind_guard_evidence_to_families(
        [_guard("v1", "producer-family-one"), _guard("v2", "producer-family-two")],
        citations=citations,
    )
    derived = {row["source_family"] for row in bound["guard_evidence"]}
    assert len(derived) == 1
    assert all(family.startswith("FAM-") for family in derived)
    assert bound["family_receipt"]["family_count"] == 1
    assert len(bound["producer_family_overrides"]) == 2
    assert bound["producer_family_authority"] == "NONE"


def test_short_weak_title_falls_back_to_arxiv_work_id_and_still_collapses_versions():
    citations = [
        _citation("v1", title="Short title", url="https://arxiv.org/abs/2608.99999v1"),
        _citation("v2", title="Short title", url="https://arxiv.org/abs/2608.99999v2"),
    ]
    receipt = derive_source_families(citations)
    assert receipt["family_count"] == 1
    identities = {row["identity"]["kind"] for row in receipt["families_by_source_id"].values()}
    assert identities == {"ARXIV_WORK"}
