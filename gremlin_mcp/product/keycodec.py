from __future__ import annotations

import base64
import binascii
from datetime import date
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .license import LicenseError, load_public_key, verify_license

LICENSE_KEY_PREFIX = "GRM1-"
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


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
        raise LicenseError("license key payload must be finite JSON") from exc


def _json_no_duplicates(text: str) -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise LicenseError(f"duplicate JSON key in license key: {key}")
            out[key] = value
        return out

    try:
        return json.loads(text, object_pairs_hook=hook)
    except LicenseError:
        raise
    except json.JSONDecodeError as exc:
        raise LicenseError("license key is malformed") from exc


def encode_license_key(envelope: Mapping[str, Any]) -> str:
    if not isinstance(envelope, Mapping):
        raise LicenseError("license key envelope must be an object")
    raw = base64.urlsafe_b64encode(_canonical(dict(envelope))).rstrip(b"=").decode("ascii")
    return LICENSE_KEY_PREFIX + raw


def decode_license_key(value: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise LicenseError("license key must be a string")
    if value != value.strip():
        raise LicenseError("license key must not contain surrounding whitespace")
    if not value.startswith(LICENSE_KEY_PREFIX):
        raise LicenseError(f"license key must start with {LICENSE_KEY_PREFIX}")
    encoded = value[len(LICENSE_KEY_PREFIX) :]
    if not encoded:
        raise LicenseError("license key payload is empty")
    if not _B64URL_RE.fullmatch(encoded):
        raise LicenseError("license key payload must be canonical unpadded base64url")
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    try:
        raw = base64.b64decode((encoded + padding).encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LicenseError("license key is malformed") from exc
    canonical_encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if canonical_encoded != encoded:
        raise LicenseError("license key payload must use canonical base64url encoding")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LicenseError("license key payload must be UTF-8 JSON") from exc
    decoded = _json_no_duplicates(text)
    if not isinstance(decoded, dict):
        raise LicenseError("license key envelope must be an object")
    return decoded


def verify_license_key(
    key: str,
    public_key_path: str | Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    return verify_license(decode_license_key(key), load_public_key(public_key_path), today=today)
