from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import re
from typing import Any

SCHEMA = "GREMLIN_FULL_TEXT_CLAIM_AUDIT_V0_1"
VERSION = "0.1.0"

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}")
_NEGATION_RE = re.compile(r"\b(?:not|no|never|cannot|can't|doesn't|does not|isn't|is not|are not|without)\b", re.I)
_OPEN_RE = re.compile(
    r"\b(?:open question|remains open|unresolved|not resolved|not addressed|unknown|uncertain|cannot be resolved)\b",
    re.I,
)
_UNIQUENESS_RE = re.compile(r"\b(?:unique|uniquely|only solution|only possible|one and only)\b", re.I)
_EXACTNESS_RE = re.compile(r"\b(?:exact|exactly|identity|identical)\b", re.I)
_PROOF_RE = re.compile(r"\b(?:prove|proves|proved|proof|demonstrates conclusively|establishes)\b", re.I)
_NUMERIC_ASSIGNMENT_RE = re.compile(
    r"(?m)^\s*(?P<lhs>[A-Za-z][A-Za-z0-9_]{0,63})\s*=\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"(?:\s*(?P<unit>[A-Za-zμµΩ°/%][A-Za-z0-9μµΩ°/%^*·⋅−+\-]*))?\s*[.;,]?\s*$"
)

_STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "before", "being", "between",
    "both", "but", "can", "could", "does", "every", "for", "from", "has", "have", "into", "its", "more",
    "most", "not", "only", "our", "same", "than", "that", "the", "their", "there", "these", "this", "through",
    "under", "was", "were", "which", "with", "within", "would",
}


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("full text audit data must be finite JSON") from exc


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _sentences(text: str) -> list[str]:
    compact = " ".join(text.replace("\x00", " ").split())
    if not compact:
        return []
    return [row.strip() for row in _SENTENCE_SPLIT_RE.split(compact) if row.strip()]


def _tokens(sentence: str) -> set[str]:
    return {
        token.casefold()
        for token in _WORD_RE.findall(sentence)
        if token.casefold() not in _STOPWORDS and len(token) >= 3
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _contradiction_candidates(sentences: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prepared = [(sentence, _tokens(sentence), bool(_NEGATION_RE.search(sentence))) for sentence in sentences]
    for index, (left, left_tokens, left_negated) in enumerate(prepared):
        if len(left_tokens) < 3:
            continue
        for right, right_tokens, right_negated in prepared[index + 1 :]:
            if left_negated == right_negated or len(right_tokens) < 3:
                continue
            similarity = _jaccard(left_tokens, right_tokens)
            if similarity < 0.72:
                continue
            rows.append(
                {
                    "classification": "DIRECT_NEGATION_CANDIDATE",
                    "left": left,
                    "right": right,
                    "lexical_similarity": similarity,
                    "requires_domain_review": True,
                    "epistemic_status": "CANDIDATE_NOT_ESTABLISHED_CONTRADICTION",
                }
            )
    return rows


def _numeric_assignments(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in _NUMERIC_ASSIGNMENT_RE.finditer(text):
        value = float(match.group("value"))
        if not math.isfinite(value):
            continue
        rows.append(
            {
                "lhs": match.group("lhs"),
                "value": value,
                "literal": match.group("value"),
                "unit": match.group("unit") or None,
            }
        )
    return rows


def _numeric_conflicts(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for row in assignments:
        grouped[(row["lhs"], row["unit"])].append(row)

    conflicts: list[dict[str, Any]] = []
    for (lhs, unit), rows in grouped.items():
        if len(rows) < 2:
            continue
        values = [row["value"] for row in rows]
        abs_nonzero = [abs(value) for value in values if value != 0.0]
        if not abs_nonzero:
            continue
        hi = max(abs_nonzero)
        lo = min(abs_nonzero)
        ratio = hi / lo if lo else math.inf
        distinct = len({row["literal"] for row in rows}) > 1
        if not distinct or ratio < 1.000001:
            continue
        conflicts.append(
            {
                "lhs": lhs,
                "unit": unit,
                "values": values,
                "ratio": ratio,
                "classification": "INTERNAL_NUMERIC_CONFLICT_CANDIDATE",
                "requires_equation_context": True,
                "epistemic_status": "CANDIDATE_NOT_ESTABLISHED_ERROR",
            }
        )
    conflicts.sort(key=lambda row: (-row["ratio"], row["lhs"]))
    return conflicts


def _strong_claims(sentences: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sentence in sentences:
        if _UNIQUENESS_RE.search(sentence):
            rows.append(
                {
                    "claim": sentence,
                    "claim_strength": "UNIQUENESS",
                    "gate": "REQUIRES_UNIQUENESS_WITNESS",
                    "epistemic_status": "ASSERTED_REQUIRES_DERIVATION_AUDIT",
                }
            )
        elif _PROOF_RE.search(sentence):
            rows.append(
                {
                    "claim": sentence,
                    "claim_strength": "PROOF_OR_ESTABLISHMENT",
                    "gate": "REQUIRES_PROOF_CHAIN_WITNESS",
                    "epistemic_status": "ASSERTED_REQUIRES_DERIVATION_AUDIT",
                }
            )
        elif _EXACTNESS_RE.search(sentence):
            rows.append(
                {
                    "claim": sentence,
                    "claim_strength": "EXACTNESS",
                    "gate": "REQUIRES_EXACT_IDENTITY_WITNESS",
                    "epistemic_status": "ASSERTED_REQUIRES_DERIVATION_AUDIT",
                }
            )
    return rows


def _open_claims(sentences: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "claim": sentence,
            "epistemic_status": "OPEN_OR_EXPLICITLY_LIMITED",
        }
        for sentence in sentences
        if _OPEN_RE.search(sentence)
    ]


def audit_full_text(text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_id, str):
        raise ValueError("source_id must be a string")
    source = source_id.strip()
    if not source:
        raise ValueError("source_id must be non-empty")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    body = text
    if not body.strip():
        core = {
            "schema": SCHEMA,
            "version": VERSION,
            "source_id": source,
            "status": "NO_TEXT_FAIL_CLOSED",
            "contradiction_candidates": [],
            "numeric_assignments": [],
            "numeric_conflicts": [],
            "strong_claims": [],
            "open_or_limited_claims": [],
            "authority": _authority(),
        }
        core["audit_commitment"] = _commit(b"GREMLIN-FULL-TEXT-AUDIT/v0.1", core)
        return core

    sentences = _sentences(body)
    assignments = _numeric_assignments(body)
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "source_id": source,
        "status": "CANDIDATE_AUDIT_COMPLETE",
        "text_length_chars": len(body),
        "sentence_count": len(sentences),
        "contradiction_candidates": _contradiction_candidates(sentences),
        "numeric_assignments": assignments,
        "numeric_conflicts": _numeric_conflicts(assignments),
        "strong_claims": _strong_claims(sentences),
        "open_or_limited_claims": _open_claims(sentences),
        "scope_boundary": [
            "INTERNAL_FULL_TEXT_STRUCTURE_ONLY",
            "NO_EXTERNAL_PHYSICS_VALIDATION",
            "NO_AUTOMATIC_CANON_PROMOTION",
            "CANDIDATES_REQUIRE_EQUATION_OR_DOMAIN_REVIEW",
        ],
        "authority": _authority(),
    }
    core["audit_commitment"] = _commit(b"GREMLIN-FULL-TEXT-AUDIT/v0.1", core)
    return core
