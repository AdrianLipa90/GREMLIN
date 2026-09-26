from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

ASTRO_SCHEMA = "GREMLIN_FERRET_ASTRO_SOURCE_V0_1"
HANDOFF_SCHEMA = "GREMLIN_FERRET_BESTIARY_HANDOFF_V0_1"
VERSION = "0.2.0"
LIBRARY_PROXY_SCHEMA = "GREMLIN_FERRET_ASTRO_LIBRARY_PROXY_V0_1"
NOEMA_ZIP_SELECTOR_RE = re.compile(r"^noema://zip/sha256/(?P<archive>[0-9a-f]{64})/entry/(?P<entry>[0-9a-f]{64})$")

OFFICIAL_ASTRO_HOSTS = frozenset({
    "irsa.ipac.caltech.edu",
    "lambda.gsfc.nasa.gov",
    "skyview.gsfc.nasa.gov",
})

ALLOWED_KINDS = frozenset({
    "CMB_COMPONENT",
    "CMB_FREQUENCY",
    "FOREGROUND_CONTROL",
    "XRAY_CONTROL",
    "POWER_SPECTRUM",
})


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out:
        raise ValueError(f"{field} must be non-empty")
    return out


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def _official_https(url: str) -> tuple[str, str]:
    parsed = urlsplit(_text(url, "source_url"))
    if parsed.scheme.lower() != "https":
        raise ValueError("FERRET astro sources must use HTTPS")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("FERRET astro source URL authority is invalid")
    host = (parsed.hostname or "").lower()
    if host not in OFFICIAL_ASTRO_HOSTS:
        raise ValueError(f"FERRET astro source host is not allowlisted: {host}")
    return url, host


def prepare_astro_source(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    source_url, host = _official_https(_text(request.get("source_url"), "source_url"))
    kind = _text(request.get("kind"), "kind").upper()
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unsupported astro source kind: {kind}")
    ra_deg = _finite(request.get("ra_deg"), "ra_deg")
    dec_deg = _finite(request.get("dec_deg"), "dec_deg")
    if not 0.0 <= ra_deg < 360.0:
        raise ValueError("ra_deg must be in [0, 360)")
    if not -90.0 <= dec_deg <= 90.0:
        raise ValueError("dec_deg must be in [-90, 90]")

    core = {
        "schema": ASTRO_SCHEMA,
        "version": VERSION,
        "status": "PREPARED_READ_ONLY",
        "source_url": source_url,
        "source_host": host,
        "product": _text(request.get("product"), "product"),
        "kind": kind,
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "query": dict(request.get("query") or {}),
        "expected_file_name": request.get("expected_file_name"),
        "authority": "READ_ONLY_SOURCE_ACQUISITION",
        "external_mutation_allowed": False,
        "canon_allowed": False,
        "fail_closed": True,
    }
    return {**core, "source_commitment": _sha256(core)}


def prepare_library_proxy_source(request: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare an immutable NOEMA Library ZIP member as a FERRET FITS source."""
    if not isinstance(request, Mapping):
        raise ValueError("request must be a mapping")
    selector_uri = _text(request.get("selector_uri"), "selector_uri")
    match = NOEMA_ZIP_SELECTOR_RE.fullmatch(selector_uri)
    if not match:
        raise ValueError("selector_uri must be a canonical noema://zip/sha256/.../entry/... URI")
    archive_sha256 = _text(request.get("archive_sha256"), "archive_sha256").lower()
    entry_sha256 = _text(request.get("entry_sha256"), "entry_sha256").lower()
    if archive_sha256 != match.group("archive"):
        raise ValueError("archive_sha256 does not match selector URI")
    if len(entry_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in entry_sha256):
        raise ValueError("entry_sha256 must be lowercase hexadecimal SHA-256")
    byte_count = request.get("byte_count")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count <= 0:
        raise ValueError("byte_count must be a positive integer")
    kind = _text(request.get("kind"), "kind").upper()
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unsupported astro source kind: {kind}")
    ra_deg = _finite(request.get("ra_deg"), "ra_deg")
    dec_deg = _finite(request.get("dec_deg"), "dec_deg")
    if not 0.0 <= ra_deg < 360.0:
        raise ValueError("ra_deg must be in [0, 360)")
    if not -90.0 <= dec_deg <= 90.0:
        raise ValueError("dec_deg must be in [-90, 90]")
    core = {
        "schema": LIBRARY_PROXY_SCHEMA,
        "version": VERSION,
        "status": "PREPARED_LIBRARY_PROXY",
        "selector_uri": selector_uri,
        "archive_sha256": archive_sha256,
        "entry_selector_sha256": match.group("entry"),
        "entry_sha256": entry_sha256,
        "byte_count": byte_count,
        "file_name": _text(request.get("file_name"), "file_name"),
        "product": _text(request.get("product"), "product"),
        "kind": kind,
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "source_transport": "NOEMA_LIBRARY_ZIP_MEMBER",
        "authority": "READ_ONLY_RECOVERY",
        "external_mutation_allowed": False,
        "live_observation_claim": False,
        "canon_allowed": False,
        "fail_closed": True,
    }
    return {**core, "source_commitment": _sha256(core)}


def build_fits_provenance_receipt(
    source: Mapping[str, Any],
    *,
    file_name: str,
    sha256: str | None = None,
    byte_count: int | None = None,
    header: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    accepted = {
        (ASTRO_SCHEMA, "PREPARED_READ_ONLY"),
        (LIBRARY_PROXY_SCHEMA, "PREPARED_LIBRARY_PROXY"),
    }
    if (source.get("schema"), source.get("status")) not in accepted:
        raise ValueError("source must be a prepared FERRET astro source or immutable Library proxy")
    core = {
        "schema": "GREMLIN_FERRET_FITS_PROVENANCE_V0_1",
        "version": VERSION,
        "status": "OBSERVED" if sha256 else "SOURCE_DECLARED",
        "source_commitment": source.get("source_commitment"),
        "source_url": source.get("source_url") or source.get("selector_uri"),
        "source_host": source.get("source_host") or source.get("source_transport"),
        "product": source.get("product"),
        "kind": source.get("kind"),
        "target": {"ra_deg": source.get("ra_deg"), "dec_deg": source.get("dec_deg")},
        "file_name": _text(file_name, "file_name"),
        "sha256": sha256 or source.get("entry_sha256"),
        "byte_count": byte_count or source.get("byte_count"),
        "header": dict(header or {}),
        "authority": "PROVENANCE_ONLY",
        "canon_allowed": False,
    }
    return {**core, "receipt_sha256": _sha256(core)}


def build_bestiary_handoff(
    receipts: Sequence[Mapping[str, Any]],
    *,
    task_id: str,
) -> dict[str, Any]:
    if not receipts:
        raise ValueError("at least one source receipt is required")
    normalized = []
    for receipt in receipts:
        if receipt.get("schema") != "GREMLIN_FERRET_FITS_PROVENANCE_V0_1":
            raise ValueError("handoff accepts FITS provenance receipts only")
        normalized.append({
            "receipt_sha256": receipt.get("receipt_sha256"),
            "kind": receipt.get("kind"),
            "product": receipt.get("product"),
            "file_name": receipt.get("file_name"),
            "source_url": receipt.get("source_url"),
        })
    core = {
        "schema": HANDOFF_SCHEMA,
        "version": VERSION,
        "status": "READY_FOR_BESTIARY",
        "task_id": _text(task_id, "task_id"),
        "source_receipts": normalized,
        "handoff_order": [
            "HUMMINGBIRD",
            "BAT",
            "HOUND",
            "OWL",
            "SPIDER",
            "BELZEBUB",
            "GREMLIN",
        ],
        "analysis_contract": {
            "BAT": ["phase_pattern", "harmonic_comparison", "cross_map_phase_consistency"],
            "HOUND": ["anomaly", "mismatch", "false_positive_controls"],
            "OWL": ["provenance", "epistemic_status", "source_classification"],
            "SPIDER": ["cross_source_relations", "dependency_graph", "foreground_links"],
            "BELZEBUB": ["adversarial_synthesis", "overclaim_rejection"],
            "GREMLIN": ["aggregate_candidate", "phase36d_context"],
        },
        "routing_authority": "OCTOPUS_OR_EXPLICIT_HOST_ONLY",
        "ferret_worker_fanout": False,
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
    return {**core, "handoff_sha256": _sha256(core)}
