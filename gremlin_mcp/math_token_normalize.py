from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

SCHEMA = "GREMLIN_MATH_TOKEN_NORMALIZE_V0_1"
VERSION = "0.1.0"
_INTEGER_RE = re.compile(r"^[0-9]+$")


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + b"\0" + _canonical(value), digest_size=32).hexdigest()


def _basic(token: str) -> tuple[str, list[str]]:
    text = str(token).strip()
    transforms: list[str] = []
    replacements = (
        ("×", "*", "UNICODE_MULTIPLICATION_NORMALIZED"),
        ("·", "*", "UNICODE_MULTIPLICATION_NORMALIZED"),
        ("⋅", "*", "UNICODE_MULTIPLICATION_NORMALIZED"),
        ("−", "-", "UNICODE_MINUS_NORMALIZED"),
        ("–", "-", "UNICODE_MINUS_NORMALIZED"),
    )
    for old, new, flag in replacements:
        if old in text:
            text = text.replace(old, new)
            transforms.append(flag)
    if text == "π":
        text = "pi"
        transforms.append("UNICODE_PI_NORMALIZED")
    return text, transforms


def normalize_math_tokens(tokens: Iterable[str]) -> dict[str, Any]:
    raw = [str(value).strip() for value in tokens if str(value).strip()]
    basic: list[str] = []
    transforms: list[str] = []
    for token in raw:
        normalized, flags = _basic(token)
        basic.append(normalized)
        transforms.extend(flags)

    stitched: list[str] = []
    index = 0
    while index < len(basic):
        # integer '.' integer -> one decimal token. This is deliberately adjacency-sensitive;
        # an explicit operator between fragments prevents stitching.
        if (
            index + 2 < len(basic)
            and _INTEGER_RE.fullmatch(basic[index])
            and basic[index + 1] == "."
            and _INTEGER_RE.fullmatch(basic[index + 2])
        ):
            stitched.append(f"{basic[index]}.{basic[index + 2]}")
            transforms.append("DECIMAL_FRAGMENT_STITCHED")
            index += 3
            continue
        # leading decimal '.125' when the dot and digits are adjacent tokens.
        if index + 1 < len(basic) and basic[index] == "." and _INTEGER_RE.fullmatch(basic[index + 1]):
            stitched.append(f"0.{basic[index + 1]}")
            transforms.append("DECIMAL_FRAGMENT_STITCHED")
            index += 2
            continue
        stitched.append(basic[index])
        index += 1

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "input_tokens": raw,
        "tokens": stitched,
        "transforms": sorted(set(transforms)),
        "scope_boundary": [
            "ONLY_EXPLICIT_UNICODE_OPERATOR_NORMALIZATION",
            "PI_GLYPH_NORMALIZED_ONLY_WHEN_STANDALONE_TOKEN",
            "DECIMAL_STITCH_REQUIRES_ADJACENT_DIGIT_DOT_DIGIT_TOKENS",
            "NO_COMPACT_SYMBOL_STRING_SPLITTING",
            "UNITS_ARE_PRESERVED",
            "NO_SEMANTIC_GUESSING",
            "NO_AUTOMATIC_CANON_PROMOTION",
        ],
        "authority": _authority(),
    }
    core["normalization_commitment"] = _commit(b"GREMLIN-MATH-TOKEN-NORMALIZE/v0.1", core)
    return core
