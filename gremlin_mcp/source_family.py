from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "GREMLIN_SOURCE_FAMILY_V0_1"
VERSION = "0.2.1"

_ARXIV_RE = re.compile(r"(?:^|/)(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_YEAR_RE = re.compile(r"^\s*(?P<year>\d{4})")
_STRONG_IDENTITY_KINDS = {"DOI", "ARXIV_WORK"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _family_id(identity: Mapping[str, Any]) -> str:
    digest = hashlib.blake2b(b"GREMLIN-SOURCE-FAMILY/v0.2\0" + _canonical(identity), digest_size=16).hexdigest()
    return f"FAM-{digest}"


def normalize_title(value: Any) -> str:
    text = str(value or "").casefold()
    return " ".join(_NON_ALNUM.sub(" ", text).split())


def normalize_doi(value: Any) -> str | None:
    text = str(value or "").strip().casefold()
    if not text:
        return None
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text or None


def doi_from_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parts = urlsplit(text)
    if parts.netloc.casefold() not in {"doi.org", "www.doi.org", "dx.doi.org"}:
        return None
    return normalize_doi(parts.path.lstrip("/"))


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


def _informative_title(value: Any) -> str | None:
    title = normalize_title(value)
    if len(title) >= 20 and len(title.split()) >= 3:
        return title
    return None


def _published_year(value: Any) -> int | None:
    match = _YEAR_RE.match(str(value or ""))
    return int(match.group("year")) if match else None


def source_identity(citation: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a conservative primary work identity for independence accounting.

    Stable work identifiers take precedence over titles. Exact informative titles remain a
    cross-provider bridge only when the title group is not ambiguous in strong identifiers.
    This is a provenance-family heuristic, not proof of source independence.
    """
    doi = normalize_doi(citation.get("doi")) or doi_from_url(citation.get("url"))
    if doi:
        return {"kind": "DOI", "value": doi}
    arxiv = arxiv_work_id(citation.get("url"))
    if arxiv:
        return {"kind": "ARXIV_WORK", "value": arxiv}
    url = normalize_url(citation.get("url"))
    if url:
        return {"kind": "URL", "value": url}
    title = _informative_title(citation.get("title"))
    if title:
        return {"kind": "NORMALIZED_TITLE", "value": title}
    source_id = str(citation.get("source_id") or "").strip()
    if source_id:
        return {"kind": "SOURCE_ID_FALLBACK", "value": source_id}
    raise ValueError("citation must contain DOI, arXiv URL, URL, informative title, or source_id")


def _title_bridge_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_title = _informative_title(left.get("title"))
    right_title = _informative_title(right.get("title"))
    if not left_title or left_title != right_title:
        return False
    left_year = _published_year(left.get("published"))
    right_year = _published_year(right.get("published"))
    if left_year is not None and right_year is not None and abs(left_year - right_year) > 3:
        return False
    return True


def _ambiguous_title_groups(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, set[str]]] = {}
    for record in records:
        title = _informative_title(record.get("title"))
        if not title:
            continue
        group = groups.setdefault(title, {"DOI": set(), "ARXIV_WORK": set()})
        identity = record["identity"]
        kind = str(identity.get("kind"))
        if kind in _STRONG_IDENTITY_KINDS:
            group[kind].add(str(identity.get("value")))

    ambiguous: dict[str, dict[str, Any]] = {}
    for title, identifiers in groups.items():
        doi_ids = sorted(identifiers["DOI"])
        arxiv_ids = sorted(identifiers["ARXIV_WORK"])
        if len(doi_ids) > 1 or len(arxiv_ids) > 1:
            ambiguous[title] = {
                "normalized_title": title,
                "doi_ids": doi_ids,
                "arxiv_work_ids": arxiv_ids,
                "policy": "TITLE_BRIDGE_DISABLED_DUE_TO_STRONG_IDENTITY_AMBIGUITY",
            }
    return ambiguous


def _canonical_family_identity(members: list[dict[str, Any]]) -> dict[str, Any]:
    identities = [row["identity"] for row in members]
    dois = sorted({str(identity["value"]) for identity in identities if identity["kind"] == "DOI"})
    if len(dois) == 1:
        return {"kind": "DOI", "value": dois[0]}
    arxiv_ids = sorted({str(identity["value"]) for identity in identities if identity["kind"] == "ARXIV_WORK"})
    if len(arxiv_ids) == 1:
        return {"kind": "ARXIV_WORK", "value": arxiv_ids[0]}
    titles = sorted({title for row in members if (title := _informative_title(row.get("title")))})
    if len(titles) == 1:
        return {"kind": "NORMALIZED_TITLE", "value": titles[0]}
    return min(identities, key=lambda row: (str(row.get("kind")), str(row.get("value"))))


def derive_source_families(citations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in citations]
    records: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    duplicate_source_ids: list[str] = []
    for row in rows:
        source_id = str(row.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("citation source_id must be non-empty")
        if source_id in seen_source_ids:
            duplicate_source_ids.append(source_id)
            continue
        seen_source_ids.add(source_id)
        records.append({**row, "source_id": source_id, "identity": source_identity(row)})
    if duplicate_source_ids:
        raise ValueError(f"duplicate citation source_id values: {sorted(set(duplicate_source_ids))}")

    ambiguous_titles = _ambiguous_title_groups(records)
    parent = list(range(len(records)))
    rank = [0] * len(records)
    merge_receipts: list[dict[str, Any]] = []

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left_index: int, right_index: int, reason: str) -> None:
        left_root = find(left_index)
        right_root = find(right_index)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1
        merge_receipts.append(
            {
                "left_source_id": records[left_index]["source_id"],
                "right_source_id": records[right_index]["source_id"],
                "reason": reason,
            }
        )

    for left_index, left in enumerate(records):
        for right_index in range(left_index + 1, len(records)):
            right = records[right_index]
            left_identity = left["identity"]
            right_identity = right["identity"]
            if left_identity == right_identity:
                union(left_index, right_index, "EXACT_PRIMARY_IDENTITY")
                continue
            title = _informative_title(left.get("title"))
            if title and title in ambiguous_titles:
                continue
            if _title_bridge_compatible(left, right):
                union(left_index, right_index, "EXACT_INFORMATIVE_TITLE_COMPATIBLE_YEAR_BRIDGE")

    grouped: dict[int, list[dict[str, Any]]] = {}
    for index, record in enumerate(records):
        grouped.setdefault(find(index), []).append(record)

    by_source: dict[str, dict[str, Any]] = {}
    clusters: dict[str, list[str]] = {}
    family_identities: dict[str, dict[str, Any]] = {}
    for members in grouped.values():
        canonical_identity = _canonical_family_identity(members)
        family_id = _family_id(canonical_identity)
        family_identities[family_id] = canonical_identity
        member_ids = sorted(row["source_id"] for row in members)
        clusters[family_id] = member_ids
        for row in members:
            by_source[row["source_id"]] = {
                "source_id": row["source_id"],
                "family_id": family_id,
                "identity": row["identity"],
                "family_identity": canonical_identity,
                "derivation": "STRONG_IDENTIFIER_FIRST_WITH_AMBIGUITY_GATED_TITLE_BRIDGE",
            }

    core = {
        "families_by_source_id": dict(sorted(by_source.items())),
        "clusters": dict(sorted(clusters.items())),
        "family_identities": dict(sorted(family_identities.items())),
        "merge_receipts": sorted(
            merge_receipts,
            key=lambda row: (row["left_source_id"], row["right_source_id"], row["reason"]),
        ),
        "ambiguous_title_bridges": [ambiguous_titles[key] for key in sorted(ambiguous_titles)],
        "source_count": len(by_source),
        "family_count": len(clusters),
        "collapsed_duplicate_or_version_count": len(by_source) - len(clusters),
        "independence_status": "PROVENANCE_FAMILY_HEURISTIC_NOT_INDEPENDENCE_PROOF",
        "policy": "STRONG_IDENTIFIERS_FIRST_AMBIGUITY_GATED_EXACT_TITLE_YEAR_CROSSWALK",
        "strong_identity_conflict_policy": "AMBIGUOUS_TITLE_GROUPS_WITH_MULTIPLE_DOI_OR_ARXIV_IDS_DISABLE_TITLE_BRIDGING",
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "family_set_commitment": hashlib.blake2b(
            b"GREMLIN-SOURCE-FAMILY-SET/v0.2\0" + _canonical(core), digest_size=32
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
            overrides.append(
                {
                    "source_id": source_id,
                    "producer_declared_source_family": declared,
                    "derived_source_family": derived,
                }
            )
    return {
        "guard_evidence": bound,
        "family_receipt": family_receipt,
        "producer_family_overrides": overrides,
        "producer_family_authority": "NONE",
    }
