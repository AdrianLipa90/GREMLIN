from __future__ import annotations

from gremlin_mcp.relational_memory_encoder import (
    bees_coherence_finding,
    elephant_memory_orbit,
    encode_memory_text,
    memory_similarity,
    retrieve_memory,
)


MEMORIES = {
    "stella": "stella octangula: two shared poles and six lateral vertices",
    "projections": "six projections share the poles and expose six lateral channels each",
    "36d": "36 = 6 projections x 6 relational channels",
    "moire": "six projections may have distinct frequencies and slight relative rotations",
    "elephant": "ELEPHANT consolidates relational memory, replay and retention",
    "bees": "BEES checks overlap coherence, anti-entropy delta and reconciliation proposals",
}

PARAPHRASES = {
    "stella": "compound tetrahedral geometry with a common antipodal pole pair and six side points",
    "projections": "six views use the same two poles, each carrying six side channels",
    "36d": "thirty six dimensions factor into six views with six relation channels per view",
    "moire": "slightly twisted layers oscillating at different rates create the interference pattern",
    "elephant": "long-term memory is strengthened through consolidation, replay and retention planning",
    "bees": "distributed fragments are compared for overlap consistency and proposed anti-entropy reconciliation",
}


def test_relational_encoder_is_exact_6_by_6_and_hash_is_not_semantic_geometry() -> None:
    packet = encode_memory_text(MEMORIES["elephant"])
    assert packet["dimension"] == 36
    assert packet["factorization"] == [6, 6]
    assert len(packet["phase36"]) == 36
    assert len(packet["matrix6x6"]) == 6
    assert all(len(row) == 6 for row in packet["matrix6x6"])
    assert packet["claims"]["hash_is_integrity_not_semantic_distance"] is True
    assert packet["authority"]["canon_allowed"] is False


def test_semantic_normalization_is_stable_across_punctuation() -> None:
    a = encode_memory_text("BEES: anti-entropy reconciliation.")
    b = encode_memory_text("BEES anti entropy reconciliation")
    assert a["semantic_commitment"] == b["semantic_commitment"]
    assert a["raw_text_commitment"] != b["raw_text_commitment"]


def test_six_current_memory_paraphrases_recall_six_of_six() -> None:
    for expected, cue in PARAPHRASES.items():
        result = retrieve_memory(cue, MEMORIES)
        assert result["status"] == "MATCH"
        assert result["picked"] == expected


def test_unrelated_cue_fails_closed_instead_of_forcing_a_match() -> None:
    result = retrieve_memory(
        "weather forecast restaurant booking mortgage payment",
        MEMORIES,
    )
    assert result["status"] == "NO_CONFIDENT_MATCH"
    assert result["picked"] is None


def test_related_memory_has_higher_score_than_unrelated_memory() -> None:
    related = memory_similarity(PARAPHRASES["elephant"], MEMORIES["elephant"])
    unrelated = memory_similarity(PARAPHRASES["elephant"], MEMORIES["bees"])
    assert related["score"] > unrelated["score"]
    assert related["weighted_atom_jaccard"] > unrelated["weighted_atom_jaccard"]


def test_elephant_and_bees_emit_candidate_only_non_authoritative_artifacts() -> None:
    orbit = elephant_memory_orbit("self:elephant", MEMORIES["elephant"])
    finding = bees_coherence_finding(
        "self:bees-a",
        MEMORIES["bees"],
        "self:bees-b",
        PARAPHRASES["bees"],
    )
    assert orbit["artifact_type"] == "MEMORY_ORBIT"
    assert orbit["status"] == "CANDIDATE_ONLY"
    assert orbit["authority"]["execution_admitted"] is False
    assert finding["artifact_type"] == "COHERENCE_FINDING"
    assert finding["reconcile_proposal_only"] is True
    assert finding["authority"]["production_runtime_write"] is False
