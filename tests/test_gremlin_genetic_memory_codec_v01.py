from __future__ import annotations

import copy

import pytest

from gremlin_mcp.genetic_memory_codec import (
    CODONS,
    CODON_CODEBOOK,
    CODON_SYMBOLS,
    build_hypercrystal_expression,
    decode_bytes,
    decode_memory_record,
    encode_bytes,
    encode_memory_record,
    validate_genome_packet,
)


def test_codon_codebook_is_exact_64_way_bijection() -> None:
    assert len(CODONS) == 64
    assert len(set(CODONS)) == 64
    assert len(CODON_SYMBOLS) == 64
    assert len(set(CODON_SYMBOLS)) == 64
    assert set(CODON_CODEBOOK) == set(CODONS)
    assert all(len(codon) == 3 and set(codon) <= set("ACGT") for codon in CODONS)
    assert [CODON_CODEBOOK[codon]["value"] for codon in CODONS] == list(range(64))


@pytest.mark.parametrize("size", [0, 1, 2, 3, 4, 5, 31, 256, 1024])
def test_exact_bytes_round_trip(size: int) -> None:
    raw = bytes((index * 37 + 11) % 256 for index in range(size))
    packet = encode_bytes(raw, source_id="fixture")
    assert decode_bytes(packet) == raw
    assert validate_genome_packet(packet)["genome_id"] == packet["genome_id"]


def test_hive_record_round_trip_is_byte_identical_canonical_json() -> None:
    record = {
        "record_id": "hive:fixture",
        "subject_id": "subject-1",
        "version": 3,
        "payload": {"z": [1, 2, 3], "a": "ąść", "nested": {"flag": False}},
        "parent_record_id": "hive:parent",
        "priority": 0.82,
    }
    packet = encode_memory_record(record)
    restored = decode_memory_record(packet)
    assert restored == record
    assert encode_memory_record(restored) == packet


def test_genome_tamper_fails_closed() -> None:
    packet = encode_bytes(b"memory")
    tampered = copy.deepcopy(packet)
    first = tampered["sequence"][:3]
    replacement = "AAA" if first != "AAA" else "AAC"
    tampered["sequence"] = replacement + tampered["sequence"][3:]
    with pytest.raises(ValueError, match="genome commitment mismatch"):
        decode_bytes(tampered)


def test_nonzero_terminal_padding_fails_closed_even_with_rebound_commitment() -> None:
    packet = encode_bytes(b"x")
    tampered = dict(packet)
    tampered["bit_padding"] = 1
    with pytest.raises(ValueError):
        validate_genome_packet(tampered)


def test_hypercrystal_expression_is_deterministic_read_only_and_bound_to_36d() -> None:
    packet = encode_memory_record({
        "record_id": "hive:fixture",
        "parent_record_id": None,
        "payload": {"kind": "MEMORY_INDEX", "value": 7},
    })
    phase = [index / 17.0 for index in range(36)]
    one = build_hypercrystal_expression(packet, phase, top_k=8, phase_source="TEST_36D")
    two = build_hypercrystal_expression(packet, phase, top_k=8, phase_source="TEST_36D")
    assert one == two
    assert one["genome_id"] == packet["genome_id"]
    assert one["memory_mutation_allowed"] is False
    assert one["semantic_truth_claim"] is False
    assert one["physical_mechanism_claim"] is False
    assert len(one["active_codons"]) <= 8
    assert all(0.0 <= row["coherence"] <= 1.0 + 1e-15 for row in one["active_codons"])
    with pytest.raises(ValueError, match="exactly 36"):
        build_hypercrystal_expression(packet, phase[:-1])
