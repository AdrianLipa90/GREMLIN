from __future__ import annotations

import base64
from datetime import date
import json
from pathlib import Path
from typing import Any, Mapping

from .license import LicenseError, load_public_key, verify_license

LICENSE_KEY_PREFIX = "GRM1-"


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


def encode_license_key(envelope: Mapping[str, Any]) -> str:
    raw = base64.urlsafe_b64encode(_canonical(dict(envelope))).rstrip(b"=").decode("ascii")
    return LICENSE_KEY_PREFIX + raw


def decode_license_key(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text.startswith(LICENSE_KEY_PREFIX):
        raise LicenseError(f"license key must start with {LICENSE_KEY_PREFIX}")
    encoded = text[len(LICENSE_KEY_PREFIX) :]
    if not encoded:
        raise LicenseError("license key payload is empty")
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise LicenseError("license key is malformed") from exc
    if not isinstance(value, dict):
        raise LicenseError("license key envelope must be an object")
    return value


def verify_license_key(
    key: str,
    public_key_path: str | Path,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    return verify_license(decode_license_key(key), load_public_key(public_key_path), today=today)
