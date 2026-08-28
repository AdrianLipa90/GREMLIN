from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from tools.gremlin_scalar_source_firewall_v03 import validate_frozen_scalar_source_registry_v03

SCHEMA = "GREMLIN_SCALAR_SOURCE_DELTA_V0_5"
DOMAIN = b"GREMLIN-SCALAR-SOURCE-DELTA/v0.5\x00"


class ScalarSourceDeltaError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise ScalarSourceDeltaError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ScalarSourceDeltaError(f"{name} must be hexadecimal") from exc
    return text


def build_scalar_source_delta_v05(base_registry: Mapping[str, Any]) -> dict[str, Any]:
    validate_frozen_scalar_source_registry_v03(base_registry)
    core = {
        "schema": SCHEMA,
        "base_registry_commitment": _hash64(base_registry.get("registry_commitment"), "base_registry_commitment"),
        "updates": {
            "affect": {
                "readiness": "DETERMINISTIC_INPUT_CONDITIONED_PRODUCER_CANDIDATE",
                "semantic_authority": "THE_CONSCIOUSNESS_DICTIONARY_CLX2-AFFECT-002",
                "formalism": "F-AFFECT-FIELD",
                "producer": {
                    "repository": "AdrianLipa90/The-Consciousness-Dictionary",
                    "commit": "b988113faf0cfd0c534dab4bb4a7b5cca41e40b9",
                    "path": "src/consciousness_dictionary/affect_detection.py",
                    "blob_sha": "6771c2316c1b6b3157ae76c36f2d3000b916baaf",
                    "method": "transparent_lexical_surface_v1",
                    "validation_path": "provenance/AFFECT_DETECTION_V0_1_VALIDATION.json",
                    "validation_blob_sha": "cda747d3374d0ea96710af0c452a8781503c3a98",
                },
                "field": [
                    "valence",
                    "arousal",
                    "urgency",
                    "threat_relevance",
                    "attachment_relevance",
                    "reward_relevance",
                ],
                "confidence_separate": True,
                "raw_text_persistence": "HASH_ONLY",
            },
            "valuation": {
                "readiness": "SCHEMA_PRESENT_EVALUATOR_UNSPECIFIED",
                "semantic_term_id": "CLX2-AFFECT-001",
                "current_typed_scaffold": "RIFCCoordinates.valuation",
                "producer_status": "UNRESOLVED",
            },
            "epistemic_support": {
                "readiness": "ANTECEDENTS_PRESENT_SCALARIZATION_UNRESOLVED",
                "semantic_antecedents": ["CLX2-SEM-019", "CLX2-SEM-020", "CLX2-SEM-021", "CLX2-SEM-023"],
                "software_gate": "promotion_requires_evidence",
                "producer_status": "UNRESOLVED",
            },
            "contradiction_load": {
                "readiness": "SEMANTIC_TERM_PRESENT_EVALUATOR_UNRESOLVED",
                "semantic_term_id": "CLX2-DYN-009",
                "producer_status": "UNRESOLVED",
            },
            "recursive_integrity": {
                "readiness": "SEMANTIC_TERM_PRESENT_EVALUATOR_UNRESOLVED",
                "semantic_term_id": "CLX2-DYN-010",
                "producer_status": "UNRESOLVED",
            },
        },
        "readiness": {
            "affect_source_closed_for_candidate_inference": True,
            "kaku_pre_vector_complete": False,
            "radical_pre_vector_complete": False,
            "vector_synthesis_globally_ready": False,
        },
        "rules": {
            "affect_confidence_is_epistemic_support": False,
            "affect_phase36_required_pre_vector": False,
            "phase_similarity_promotes_epistemic_status": False,
            "unresolved_evaluator_receives_default_zero": False,
        },
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "SOURCE_FRONTIER_UPDATED",
    }
    return {**core, "source_delta_commitment": hashlib.blake2b(DOMAIN + _canonical(core), digest_size=32).hexdigest()}


def validate_scalar_source_delta_v05(delta: Mapping[str, Any], base_registry: Mapping[str, Any]) -> bool:
    validate_frozen_scalar_source_registry_v03(base_registry)
    expected = build_scalar_source_delta_v05(base_registry)
    if _canonical(delta) != _canonical(expected):
        raise ScalarSourceDeltaError("scalar source delta differs from frozen v0.5 frontier")
    if delta.get("production_runtime_write") is not False:
        raise ScalarSourceDeltaError("source delta cannot grant runtime write")
    if delta.get("execution_admitted") is not False or delta.get("canon_allowed") is not False:
        raise ScalarSourceDeltaError("source delta authority boundary violated")
    return True
