from __future__ import annotations

from gremlin_mcp.hound_provenance import hound_provenance_audit
from gremlin_mcp.source_family import derive_source_families


def _citation(source_id, *, title, url, doi=None, published="2026-08-30"):
    return {
        "source_id": source_id,
        "provider": "fixture",
        "title": title,
        "url": url,
        "doi": doi,
        "published": published,
    }


def test_hound_reuses_exact_family_set_commitment_and_clusters():
    title = "Information Geometry and Entropy Relations in Quantum Gravity"
    citations = [
        _citation("v1", title=title, url="https://arxiv.org/abs/2608.54321v1"),
        _citation("v2", title=title, url="https://arxiv.org/abs/2608.54321v2"),
        _citation("other", title="Different Independent Work On Quantum Geometry", url="https://example.org/other"),
    ]
    family = derive_source_families(citations)
    audit = hound_provenance_audit(citations)
    assert audit["family_set_commitment"] == family["family_set_commitment"]
    assert audit["source_count"] == 3
    assert audit["family_count"] == 2
    assert audit["collapsed_duplicate_or_version_count"] == 1
    assert len(audit["duplicate_or_version_clusters"]) == 1
    assert audit["duplicate_or_version_clusters"][0]["source_ids"] == ["v1", "v2"]
    assert audit["contradiction_inference_from_family_topology"] is False
    assert audit["authority"]["canon_allowed"] is False


def test_hound_preserves_ambiguous_title_veto_instead_of_transitive_collapse():
    title = "One Shared Title That Must Not Create A Transitive Identity Collision"
    citations = [
        _citation("doi-a", title=title, url="https://doi.org/10.1000/a", doi="10.1000/a"),
        _citation("arxiv", title=title, url="https://arxiv.org/abs/2608.44444v1"),
        _citation("doi-b", title=title, url="https://doi.org/10.1000/b", doi="10.1000/b"),
    ]
    audit = hound_provenance_audit(citations)
    assert audit["family_count"] == 3
    assert audit["duplicate_or_version_clusters"] == []
    assert len(audit["ambiguous_title_bridges"]) == 1
    assert audit["ambiguous_title_bridges"][0]["policy"] == "TITLE_BRIDGE_DISABLED_DUE_TO_STRONG_IDENTITY_AMBIGUITY"


def test_same_title_cross_provider_single_doi_and_arxiv_can_be_one_provenance_family():
    title = "A Modular Information Dynamical Bridge Between Quantum Systems and Geometry"
    citations = [
        _citation("journal", title=title, url="https://doi.org/10.1000/example", doi="10.1000/example"),
        _citation("preprint", title=title, url="https://arxiv.org/abs/2608.12345v2"),
    ]
    audit = hound_provenance_audit(citations)
    assert audit["family_count"] == 1
    assert audit["collapsed_duplicate_or_version_count"] == 1
    cluster = audit["duplicate_or_version_clusters"][0]
    assert cluster["source_ids"] == ["journal", "preprint"]
    assert cluster["classification"].endswith("NOT_ASSUMED_CONTRADICTION")
