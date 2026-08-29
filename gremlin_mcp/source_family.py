from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "GREMLIN_SOURCE_FAMILY_V0_1"
VERSION = "0.1.0"

_ARXIV_RE = re.compile(r"(?:^|/)(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _family_id(identity: Mapping[str, Any]) -> str:
    digest = hashlib.blake2b(b"GREMLIN-SOURCE-FAMILY/v0.1\0" + _canonical(identity), digest_size=16).hexdigest()
    return f"FAM-{digest}"


def normalize_title(value: Any) -> str:
    text = str(value or "").casefold()
    return " ".join(_NON_ALNUM.sub(" ", text).split())


def normalize_doi(value: Any) -> str | None:
    text = str(value or "").strip().casefold()
    if not text:
        return None
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text or None


def normalize_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parts = urlsplit(text)
    if not parts.scheme or not parts.netloc:
        return text.casefold()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, "", ""))


def arxiv_work_id(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = urlsplit(text).path if "://" in text else text
    match = _ARXIV_RE.search(path)
    if match:
        return match.group("id").casefold()
    plain = re.fullmatch(r"(?P<id>\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE)
    return plain.group("id").casefold() if plain else None


def source_identity(citation: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a conservative work identity for independence accounting.

    A sufficiently informative normalized title is preferred so duplicate/version records from
    different providers collapse. When title evidence is too weak, DOI, arXiv work id, then URL
    are used. This is a provenance-family heuristic, not proof of source independence.
    """
    title = normalize_title(citation.get("title"))
    if len(title) >= 20 and len(title.split()) >= 3:
        return {"kind": "NORMALIZED_TITLE", "value": title}
    doi = normalize_doi(citation.get("doi"))
    if doi:
        return {"kind": "DOI", "value": doi}
    arxiv = arxiv_work_id(citation.get("url"))
    if arxiv:
        return {"kind": "ARXIV_WORK", "value": arxiv}
    url = normalize_url(citation.get("url"))
    if url:
        return {"kind": "URL", "value": url}
    source_id = str(citation.get("source_id") or "").strip()
    if source_id:
        return {"kind": "SOURCE_ID_FALLBACK", "value": source_id}
    raise ValueError("citation must contain title, DOI, URL, or source_id")


def derive_source_families(citations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in citations]
    by_source: dict[str, dict[str, Any]] = {}
    duplicate_source_ids: list[str] = []
    for row in rows:
        source_id = str(row.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("citation source_id must be non-empty")
        if source_id in by_source:
            duplicate_source_ids.append(source_id)
            continue
        identity = source_identity(row)
        by_source[source_id] = {
            "source_id": source_id,
            "family_id": _family_id(identity),
            "identity": identity,
            "derivation": "DETERMINISTIC_PROVENANCE_HEURISTIC",
        }
    if duplicate_source_ids:
        raise ValueError(f"duplicate citation source_id values: {sorted(set(duplicate_source_ids))}")

    clusters: dict[str, list[str]] = {}
    for source_id, family in by_source.items():
        clusters.setdefault(family["family_id"], []).append(source_id)
    for members in clusters.values():
        members.sort()

    core = {
        "families_by_source_id": dict(sorted(by_source.items())),
        "clusters": dict(sorted(clusters.items())),
        "source_count": len(by_source),
        "family_count": len(clusters),
        "collapsed_duplicate_or_version_count": len(by_source) - len(clusters),
        "independence_status": "PROVENANCE_FAMILY_HEURISTIC_NOT_INDEPENDENCE_PROOF",
        "policy": "CONSERVATIVE_COLLAPSE_SHARED_WORK_IDENTITY",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "family_set_commitment": hashlib.blake2b(
            b"GREMLIN-SOURCE-FAMILY-SET/v0.1\0" + _canonical(core), digest_size=32
        ).hexdigest(),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def bind_guard_evidence_to_families(
    guard_evidence: Iterable[Mapping[str, Any]],
    *,
    citations: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    family_receipt = derive_source_families(citations)
    families = family_receipt["families_by_source_id"]
    bound: list[dict[str, Any]] = []
    overrides: list[dict[str, str]] = []
    for raw in guard_evidence:
        row = dict(raw)
        source_id = str(row.get("evidence_id") or "").strip()
        family = families.get(source_id)
        if family is None:
            raise ValueError(f"guard evidence source missing from citation family map: {source_id}")
        declared = str(row.get("source_family") or "").strip()
        derived = family["family_id"]
        row["source_family"] = derived
        row["source_family_origin"] = "DETERMINISTIC_EXECUTION_PROVENANCE_FAMILY"
        row["producer_declared_source_family"] = declared
        bound.append(row)
        if declared != derived:
            overrides.append({
                "source_id": source_id,
                "producer_declared_source_family": declared,
                "derived_source_family": derived,
            })
    return {
        "guard_evidence": bound,
        "family_receipt": family_receipt,
        "producer_family_overrides": overrides,
        "producer_family_authority": "NONE",
    }
