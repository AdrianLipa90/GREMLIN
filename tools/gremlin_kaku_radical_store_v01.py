from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from tools.gremlin_kaku_radical_writer_v01 import (
    BUNDLE_RECEIPT_SCHEMA,
    GremlinKakuRadicalWriterError,
    read_bundle_jsonl,
    render_bundle_jsonl,
    validate_persistence_bundle,
)

STORE_RECEIPT_SCHEMA = "GREMLIN_KAKU_RADICAL_IMMUTABLE_STORE_RECEIPT_V0_1"


def write_immutable_bundle_jsonl(
    path: str | os.PathLike[str],
    bundle: Mapping[str, Any],
    *,
    create_parents: bool = False,
) -> dict[str, Any]:
    """Write one content-addressed KAKU/Radical bundle with collision-safe semantics."""
    validate_persistence_bundle(bundle)
    data = render_bundle_jsonl(bundle)
    target = Path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.exists():
        raise GremlinKakuRadicalWriterError("target parent directory does not exist")

    sha = hashlib.sha256(data).hexdigest()
    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise GremlinKakuRadicalWriterError("immutable persistence path collision")
        restored = read_bundle_jsonl(target)
        if restored["bundle_commitment"] != bundle["bundle_commitment"]:
            raise GremlinKakuRadicalWriterError("idempotent persistence commitment mismatch")
        return {
            "schema": STORE_RECEIPT_SCHEMA,
            "path": str(target),
            "bundle_commitment": bundle["bundle_commitment"],
            "sha256": sha,
            "size_bytes": len(data),
            "record_count": len(bundle["records"]),
            "write_mode": "IDEMPOTENT_EXISTING_BYTES",
            "execution_admitted": False,
            "canon_allowed": False,
            "status": "IMMUTABLE_STORE_CONFIRMED",
        }

    temp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    if temp.exists():
        raise GremlinKakuRadicalWriterError("temporary persistence path already exists")
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            raise GremlinKakuRadicalWriterError("immutable persistence path appeared during write")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()

    return {
        "schema": STORE_RECEIPT_SCHEMA,
        "path": str(target),
        "bundle_commitment": bundle["bundle_commitment"],
        "sha256": sha,
        "size_bytes": len(data),
        "record_count": len(bundle["records"]),
        "write_mode": "NEW_IMMUTABLE_OBJECT",
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "IMMUTABLE_STORE_CONFIRMED",
    }
