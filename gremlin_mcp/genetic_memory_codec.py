from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from hashlib import blake2b, sha256
import json
import math
import struct
from typing import Any, Mapping, Sequence

GENETIC_MEMORY_SCHEMA = "GREMLIN_GENETIC_MEMORY_CODEC_V0_1"
GENETIC_MEMORY_VERSION = "0.1.0"
EXPRESSION_SCHEMA = "GREMLIN_HYPERCRYSTAL_MEMORY_EXPRESSION_V0_1"
AUTHORITY = "SHARED_COGNITION_ONLY"
EPISTEMIC = "CHYBA"
CODEC = "EXACT_6BIT_CODON_TRANSPORT"
PHASE_DIM = 36
BASES = "ACGT"
CODONS = tuple(a + b + c for a in BASES for b in BASES for c in BASES)
CODON_SYMBOLS = (
    "START", "STOP", "HEADER", "VERSION", "SCHEMA", "SUBJECT", "RECORD", "PARENT",
    "GENERATION", "PAYLOAD", "PAYLOAD_HASH", "RELATION", "PHASE", "GEOMETRY", "EVIDENCE", "PROVENANCE",
    "DEPENDENCY", "CONTEXT", "ACTIVATION", "REFERENCE", "CHECKSUM", "LENGTH", "AUTHORITY", "EPISTEMIC",
    "CANON_FALSE", "WORKING", "EPISODIC", "SEMANTIC", "RELATIONAL", "ARCHIVAL", "OPEN", "ALIGNING",
    "DISPUTED", "QUARANTINED", "LOCKED", "PRIORITY", "ORBIT", "ANGLE", "RADIUS", "TICK",
    "TYPE", "KEY", "VALUE", "LIST", "MAP", "INTEGER", "FLOAT", "STRING",
    "BOOLEAN", "NULL", "BYTES", "UTF8", "JSON", "BLAKE2B", "SHA256", "EXPRESSION",
    "COHERENCE", "RECALL", "CANDIDATE", "DERIVE", "SELECT", "RECOMBINE", "RESERVED_0", "RESERVED_1",
)
CODON_TO_VALUE = {codon: index for index, codon in enumerate(CODONS)}
CODON_CODEBOOK = {
    codon: {"value": index, "symbol": CODON_SYMBOLS[index]}
    for index, codon in enumerate(CODONS)
}


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("genetic-memory values must be finite canonical JSON data") from exc


def _packet_digest(value: Mapping[str, Any], *, person: bytes) -> str:
    return blake2b(_canonical_bytes(value), digest_size=32, person=person[:16]).hexdigest()


def bytes_to_codons(payload: bytes | bytearray | memoryview) -> tuple[str, int]:
    """Encode bytes exactly as 6-bit codons; returns (DNA sequence, zero-bit padding)."""
    data = bytes(payload)
    bit_length = len(data) * 8
    padding = (-bit_length) % 6
    if not data:
        return "", 0
    value = int.from_bytes(data, "big") << padding
    codon_count = (bit_length + padding) // 6
    out = []
    for index in range(codon_count):
        shift = 6 * (codon_count - index - 1)
        out.append(CODONS[(value >> shift) & 0x3F])
    return "".join(out), padding


def codons_to_bytes(sequence: str, *, bit_padding: int) -> bytes:
    """Decode an exact 6-bit codon stream back to its original bytes."""
    if not isinstance(sequence, str):
        raise ValueError("sequence must be a string")
    if isinstance(bit_padding, bool) or not isinstance(bit_padding, int) or not 0 <= bit_padding <= 5:
        raise ValueError("bit_padding must be an integer in [0,5]")
    if len(sequence) % 3:
        raise ValueError("genetic sequence length must be divisible by 3")
    codon_count = len(sequence) // 3
    if codon_count == 0:
        if bit_padding != 0:
            raise ValueError("empty genetic sequence cannot carry padding")
        return b""

    value = 0
    for offset in range(0, len(sequence), 3):
        codon = sequence[offset:offset + 3]
        try:
            token = CODON_TO_VALUE[codon]
        except KeyError as exc:
            raise ValueError(f"invalid codon at offset {offset}: {codon!r}") from exc
        value = (value << 6) | token

    payload_bits = codon_count * 6 - bit_padding
    if payload_bits < 0 or payload_bits % 8:
        raise ValueError("codon stream/padding does not resolve to whole bytes")
    if bit_padding:
        if value & ((1 << bit_padding) - 1):
            raise ValueError("non-zero terminal padding bits")
        value >>= bit_padding
    return value.to_bytes(payload_bits // 8, "big")


def encode_bytes(
    payload: bytes | bytearray | memoryview,
    *,
    media_type: str = "application/octet-stream",
    source_id: str | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    data = bytes(payload)
    sequence, padding = bytes_to_codons(data)
    source = None if source_id is None else str(source_id).strip() or None
    parent = None if parent_id is None else str(parent_id).strip() or None
    core = {
        "schema": GENETIC_MEMORY_SCHEMA,
        "version": GENETIC_MEMORY_VERSION,
        "codec": CODEC,
        "media_type": str(media_type),
        "source_id": source,
        "parent_id": parent,
        "payload_size": len(data),
        "payload_sha256": sha256(data).hexdigest(),
        "bit_padding": padding,
        "sequence": sequence,
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
    }
    return {
        **core,
        "genome_id": "gmem:" + _packet_digest(core, person=b"GRMLN-GENOME-V1"),
    }


def validate_genome_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, Mapping):
        raise ValueError("genome packet must be a mapping")
    row = dict(packet)
    if row.get("schema") != GENETIC_MEMORY_SCHEMA or row.get("version") != GENETIC_MEMORY_VERSION:
        raise ValueError("unsupported genetic-memory schema/version")
    if row.get("codec") != CODEC:
        raise ValueError("unsupported genetic-memory codec")
    if row.get("authority") != AUTHORITY or row.get("epistemic") != EPISTEMIC:
        raise ValueError("genetic-memory authority/epistemic boundary mismatch")
    if row.get("canon_allowed") is not False:
        raise ValueError("genetic-memory packets must remain canon_allowed=false")
    if isinstance(row.get("payload_size"), bool) or not isinstance(row.get("payload_size"), int) or row["payload_size"] < 0:
        raise ValueError("payload_size must be a non-negative integer")
    if not isinstance(row.get("payload_sha256"), str) or len(row["payload_sha256"]) != 64:
        raise ValueError("payload_sha256 must be a 64-character hex digest")
    if not isinstance(row.get("sequence"), str):
        raise ValueError("sequence must be a string")

    core = {key: row.get(key) for key in (
        "schema", "version", "codec", "media_type", "source_id", "parent_id",
        "payload_size", "payload_sha256", "bit_padding", "sequence",
        "authority", "epistemic", "canon_allowed",
    )}
    expected_id = "gmem:" + _packet_digest(core, person=b"GRMLN-GENOME-V1")
    if row.get("genome_id") != expected_id:
        raise ValueError("genome commitment mismatch")

    data = codons_to_bytes(row["sequence"], bit_padding=row.get("bit_padding"))
    if len(data) != row["payload_size"]:
        raise ValueError("decoded payload size mismatch")
    if sha256(data).hexdigest() != row["payload_sha256"]:
        raise ValueError("decoded payload digest mismatch")
    return {**core, "genome_id": expected_id}


def decode_bytes(packet: Mapping[str, Any]) -> bytes:
    normalized = validate_genome_packet(packet)
    return codons_to_bytes(normalized["sequence"], bit_padding=normalized["bit_padding"])


def _memory_mapping(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        raw = asdict(record)
    elif isinstance(record, Mapping):
        raw = dict(record)
    else:
        raise ValueError("memory record must be a dataclass or mapping")
    _canonical_bytes(raw)
    return raw


def encode_memory_record(record: Any) -> dict[str, Any]:
    raw = _memory_mapping(record)
    payload = _canonical_bytes(raw)
    record_id = raw.get("record_id")
    parent_id = raw.get("parent_record_id")
    return encode_bytes(
        payload,
        media_type="application/vnd.gremlin.hive-record+json",
        source_id=None if record_id is None else str(record_id),
        parent_id=None if parent_id is None else str(parent_id),
    )


def decode_memory_record(packet: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_genome_packet(packet)
    if normalized["media_type"] != "application/vnd.gremlin.hive-record+json":
        raise ValueError("genome packet is not a Hive memory-record representation")
    data = decode_bytes(normalized)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("genome payload is not canonical UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("decoded Hive memory record must be a JSON object")
    if _canonical_bytes(value) != data:
        raise ValueError("decoded Hive memory record is not canonical JSON")
    if normalized["source_id"] is not None and str(value.get("record_id")) != normalized["source_id"]:
        raise ValueError("decoded record_id does not match genetic source_id")
    expected_parent = value.get("parent_record_id")
    expected_parent = None if expected_parent is None else str(expected_parent)
    if expected_parent != normalized["parent_id"]:
        raise ValueError("decoded parent lineage does not match genetic parent_id")
    return value


def _phase36(values: Sequence[float]) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray)) or len(values) != PHASE_DIM:
        raise ValueError("phase vector must contain exactly 36 coordinates")
    out = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in out):
        raise ValueError("phase vector must contain only finite values")
    return out


def _codon_anchor(codon: str) -> tuple[float, ...]:
    anchors = []
    for dim in range(PHASE_DIM):
        raw = blake2b(
            f"{codon}:{dim}".encode("ascii"),
            digest_size=8,
            person=b"GRMLN-HX-ANCH",
        ).digest()
        fraction = int.from_bytes(raw, "big") / float(1 << 64)
        anchors.append(math.tau * fraction)
    return tuple(anchors)


def build_hypercrystal_expression(
    packet: Mapping[str, Any],
    phase36: Sequence[float],
    *,
    top_k: int = 16,
    phase_source: str = "UNSPECIFIED_36D_REFERENCE",
) -> dict[str, Any]:
    """Build a deterministic read-only recall index from a genome and 36D phase.

    The phase/codon anchors are reference addressing only; they do not assert
    semantic truth or a physical mechanism. The result cannot mutate Hive memory.
    """
    genome = validate_genome_packet(packet)
    phases = _phase36(phase36)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 64:
        raise ValueError("top_k must be an integer in [1,64]")

    codon_list = [genome["sequence"][i:i + 3] for i in range(0, len(genome["sequence"]), 3)]
    counts = Counter(codon_list)
    total = len(codon_list)
    rows: list[dict[str, Any]] = []
    for codon, count in counts.items():
        anchor = _codon_anchor(codon)
        c = math.fsum(math.cos(phi - alpha) for phi, alpha in zip(phases, anchor)) / PHASE_DIM
        s = math.fsum(math.sin(phi - alpha) for phi, alpha in zip(phases, anchor)) / PHASE_DIM
        coherence = c * c + s * s
        frequency = count / total if total else 0.0
        rows.append({
            "codon": codon,
            "value": CODON_TO_VALUE[codon],
            "symbol": CODON_SYMBOLS[CODON_TO_VALUE[codon]],
            "count": count,
            "frequency": frequency,
            "coherence": coherence,
            "score": frequency * coherence,
        })
    rows.sort(key=lambda row: (-row["score"], -row["count"], row["codon"]))
    active = rows[:top_k]

    phase_bytes = struct.pack("<36d", *phases)
    core = {
        "schema": EXPRESSION_SCHEMA,
        "version": GENETIC_MEMORY_VERSION,
        "genome_id": genome["genome_id"],
        "phase_dim": PHASE_DIM,
        "phase_sha256": sha256(phase_bytes).hexdigest(),
        "phase_source": str(phase_source),
        "top_k": top_k,
        "active_codons": active,
        "authority": AUTHORITY,
        "epistemic": EPISTEMIC,
        "canon_allowed": False,
        "memory_mutation_allowed": False,
        "semantic_truth_claim": False,
        "physical_mechanism_claim": False,
    }
    return {
        **core,
        "expression_id": "gexpr:" + _packet_digest(core, person=b"GRMLN-GEXPR-V1"),
    }


__all__ = [
    "AUTHORITY",
    "BASES",
    "CODEC",
    "CODONS",
    "CODON_CODEBOOK",
    "CODON_SYMBOLS",
    "EPISTEMIC",
    "EXPRESSION_SCHEMA",
    "GENETIC_MEMORY_SCHEMA",
    "GENETIC_MEMORY_VERSION",
    "PHASE_DIM",
    "build_hypercrystal_expression",
    "bytes_to_codons",
    "codons_to_bytes",
    "decode_bytes",
    "decode_memory_record",
    "encode_bytes",
    "encode_memory_record",
    "validate_genome_packet",
]
