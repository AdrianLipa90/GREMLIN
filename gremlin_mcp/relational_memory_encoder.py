from __future__ import annotations

import cmath
import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_RELATIONAL_MEMORY_ENCODER_V0_1"
VERSION = "0.1.0"
DIM = 36
PROJECTIONS = 6
CHANNELS = 6
CLAIM_SCOPE = "REFERENCE_SEMANTIC_GEOMETRY_CANDIDATE"
AUTHORITY = {
    "production_runtime_write": False,
    "execution_admitted": False,
    "canon_allowed": False,
}

# Deliberately bounded, versioned ontology.  It is an explicit semantic bridge,
# not an opaque model and not a claim that hashing creates semantic distance.
CONCEPT_ALIASES: dict[str, tuple[str, ...]] = {
    "geometry.stella": (
        "stella octangula", "stella", "tetrahedral compound",
        "compound tetrahedral", "tetrahedral geometry",
    ),
    "geometry.poles": (
        "poles", "pole pair", "antipodal pole", "antipodal poles",
        "two poles", "bieguny", "biegun",
    ),
    "geometry.lateral": (
        "lateral vertices", "side vertices", "side points", "lateral points",
        "boczne wierzcholki", "boczne punkty",
    ),
    "projection.six": (
        "six projections", "six views", "6 projections", "6 views",
        "szesc rzutow", "6 rzutow",
    ),
    "projection.shared": (
        "share the poles", "same two poles", "common poles", "shared poles",
        "wspolne bieguny",
    ),
    "channel.six": (
        "six lateral channels", "six side channels", "six relational channels",
        "6 relational channels", "6 channels", "szesc bocznych kanalow",
        "szesc kanalow relacji",
    ),
    "factor.36": (
        "36", "thirty six", "thirty-six", "36d", "36 dimensions",
        "thirty six dimensions", "trzydziesci szesc",
        "trzydziesci szesc wymiarow",
    ),
    "factor.6x6": (
        "6 x 6", "6x6", "six by six", "six views with six",
        "six projections x six", "6 by 6", "six relation coordinates",
        "szesc rzutow po szesc",
    ),
    "relation.channel": (
        "relational channels", "relation channels", "relational channel",
        "relation channel", "kanalow relacji", "kanaly relacji",
    ),
    "dynamics.frequency": (
        "frequency", "frequencies", "different rates", "oscillating",
        "oscillate", "czestotliwosci", "carrier rates",
        "unequal carrier rates", "roznymi czestotliwosciami", "czestotliwosciami",
    ),
    "dynamics.rotation": (
        "rotation", "rotations", "twisted", "twist",
        "slight relative rotations", "obroty", "angular offsets",
        "small angular offsets", "obrocone", "lekko obrocone",
    ),
    "dynamics.interference": (
        "interference", "moire", "beat", "beating", "beat pattern",
        "interferencja", "interferencje",
    ),
    "memory.core": (
        "memory", "relational memory", "memory trace", "pamiec", "wspomnienie",
    ),
    "memory.consolidation": (
        "consolidation", "consolidates", "consolidate", "strengthened",
        "utrwalenie", "konsolidacja",
    ),
    "memory.replay": (
        "replay", "rehearsal", "replaying", "powtorzenie",
    ),
    "memory.retention": (
        "retention", "long-term", "long term", "retention planning", "retencja",
    ),
    "coherence.overlap": (
        "overlap", "overlaps", "overlap coherence", "intersection", "styk",
    ),
    "coherence.consistency": (
        "coherence", "consistency", "consistent", "spojnosc", "zgodnosc",
    ),
    "coherence.anti_entropy": (
        "anti-entropy", "anti entropy", "antientropy",
    ),
    "coherence.reconcile": (
        "reconciliation", "reconcile", "reconciliation proposals",
        "reconcile proposals",
    ),
    "distributed.fragments": (
        "distributed fragments", "distributed memory", "fragments", "replicas",
    ),
    "role.elephant": ("elephant", "slon"),
    "role.bees": ("bees", "bee", "pszczoly"),
    "role.raven": ("raven", "kruk"),
    "role.spider": ("spider", "pajak"),
    "role.hound": ("hound",),
    "role.owl": ("owl", "sowa"),
}

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "with", "in", "on", "each",
    "may", "have", "are", "is", "into", "per", "for", "at", "by", "same",
    "common", "slight", "relative", "create", "checks", "proposed", "through",
    "use", "uses", "their", "this", "that", "from", "as", "be", "been",
    "i", "we", "you", "it", "sie", "i", "z", "na", "do", "w", "ze", "jest",
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


def _normalize_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    raw = unicodedata.normalize("NFKD", text.lower())
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.replace("moiré", "moire")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


_NORMALIZED_ALIASES = {
    concept: tuple(_normalize_text(alias) for alias in aliases)
    for concept, aliases in CONCEPT_ALIASES.items()
}


def _stem_token(token: str) -> str:
    out = token
    for suffix in ("ingly", "ation", "ations", "tion", "ions", "ing", "ed", "es", "s"):
        if len(out) > len(suffix) + 3 and out.endswith(suffix):
            out = out[:-len(suffix)]
            break
    return out


def _phrase_present(normalized: str, phrase: str) -> bool:
    return re.search(rf"(?:^| ){re.escape(phrase)}(?: |$)", normalized) is not None


def semantic_atoms(text: str) -> dict[str, Any]:
    normalized = _normalize_text(text)
    concepts: set[str] = set()
    for concept, aliases in _NORMALIZED_ALIASES.items():
        if any(_phrase_present(normalized, alias) for alias in aliases):
            concepts.add(concept)

    lexical: set[str] = set()
    numeric: set[str] = set()
    for token in normalized.split():
        if token.isdigit():
            numeric.add(f"num:{token}")
            continue
        if len(token) < 3 or token in _STOPWORDS:
            continue
        lexical.add("lex:" + _stem_token(token))

    return {
        "normalized_text": normalized,
        "concept_atoms": sorted(concepts),
        "numeric_atoms": sorted(numeric),
        "lexical_atoms": sorted(lexical),
    }


def _atom_weight(atom: str) -> float:
    if atom.startswith("lex:"):
        return 0.5
    if atom.startswith("num:"):
        return 2.0
    return 3.0


def _atom_phase(atom: str, coordinate: int) -> float:
    if coordinate < 0 or coordinate >= DIM:
        raise ValueError("coordinate out of range")
    digest = hashlib.sha256(
        f"{SCHEMA}|{VERSION}|{atom}|{coordinate}".encode("utf-8")
    ).digest()
    unit = int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)
    return (2.0 * math.pi * unit) - math.pi


def _all_atoms(packet: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            set(packet.get("concept_atoms", ()))
            | set(packet.get("numeric_atoms", ()))
            | set(packet.get("lexical_atoms", ()))
        )
    )


def encode_memory_text(text: str) -> dict[str, Any]:
    atoms = semantic_atoms(text)
    all_atoms = _all_atoms(atoms)
    if not all_atoms:
        raise ValueError("semantic encoder produced no atoms")

    phase36: list[float] = []
    amplitude36: list[float] = []
    total_weight = sum(_atom_weight(atom) for atom in all_atoms)
    for coordinate in range(DIM):
        z = 0j
        for atom in all_atoms:
            z += _atom_weight(atom) * cmath.exp(1j * _atom_phase(atom, coordinate))
        phase36.append(float(cmath.phase(z)) if abs(z) > 1e-15 else 0.0)
        amplitude36.append(float(abs(z) / total_weight))

    semantic_core = {
        "concept_atoms": atoms["concept_atoms"],
        "numeric_atoms": atoms["numeric_atoms"],
        "lexical_atoms": atoms["lexical_atoms"],
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ENCODED_CANDIDATE",
        "claim_scope": CLAIM_SCOPE,
        "dimension": DIM,
        "factorization": [PROJECTIONS, CHANNELS],
        "space": "T^36",
        "normalized_text": atoms["normalized_text"],
        **semantic_core,
        "phase36": phase36,
        "amplitude36": amplitude36,
        "matrix6x6": [
            phase36[row * CHANNELS:(row + 1) * CHANNELS]
            for row in range(PROJECTIONS)
        ],
        "amplitude_matrix6x6": [
            amplitude36[row * CHANNELS:(row + 1) * CHANNELS]
            for row in range(PROJECTIONS)
        ],
        "semantic_commitment": _sha256(semantic_core),
        "raw_text_commitment": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "ontology_commitment": _sha256(CONCEPT_ALIASES),
        "authority": dict(AUTHORITY),
        "claims": {
            "hash_is_integrity_not_semantic_distance": True,
            "semantic_geometry_is_candidate": True,
            "biological_substrate_required": False,
            "phase_coherence_establishes_truth": False,
        },
    }


def _ensure_encoded(value: str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, str):
        return encode_memory_text(value)
    if not isinstance(value, Mapping) or value.get("schema") != SCHEMA:
        raise ValueError("value must be text or a relational-memory encoder packet")
    phase = value.get("phase36")
    if not isinstance(phase, Sequence) or len(phase) != DIM:
        raise ValueError("encoded packet requires exact 36D phase")
    return dict(value)


def memory_similarity(
    left: str | Mapping[str, Any],
    right: str | Mapping[str, Any],
) -> dict[str, Any]:
    a = _ensure_encoded(left)
    b = _ensure_encoded(right)
    aa = set(_all_atoms(a))
    bb = set(_all_atoms(b))
    union = aa | bb
    intersection = aa & bb
    union_weight = sum(_atom_weight(atom) for atom in union)
    overlap_weight = sum(_atom_weight(atom) for atom in intersection)
    weighted_jaccard = overlap_weight / union_weight if union_weight else 0.0

    pa = [float(x) for x in a["phase36"]]
    pb = [float(x) for x in b["phase36"]]
    phase_coherence = abs(
        sum(cmath.exp(1j * (x - y)) for x, y in zip(pa, pb)) / DIM
    )
    score = (0.75 * weighted_jaccard) + (0.25 * phase_coherence)
    return {
        "schema": "GREMLIN_RELATIONAL_MEMORY_SIMILARITY_V0_1",
        "score": float(score),
        "weighted_atom_jaccard": float(weighted_jaccard),
        "phase_coherence36": float(phase_coherence),
        "shared_atoms": sorted(intersection),
        "authority": dict(AUTHORITY),
    }


def retrieve_memory(
    cue: str | Mapping[str, Any],
    candidates: Mapping[str, str | Mapping[str, Any]],
    *,
    min_score: float = 0.22,
    min_margin: float = 0.08,
) -> dict[str, Any]:
    if not isinstance(candidates, Mapping) or not candidates:
        raise ValueError("candidates must be a non-empty mapping")
    cue_packet = _ensure_encoded(cue)
    rows = []
    for candidate_id, candidate in candidates.items():
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate ids must be non-empty strings")
        similarity = memory_similarity(cue_packet, candidate)
        rows.append({"candidate_id": candidate_id, **similarity})
    rows.sort(key=lambda row: (-float(row["score"]), row["candidate_id"]))
    best = rows[0]
    second_score = float(rows[1]["score"]) if len(rows) > 1 else 0.0
    margin = float(best["score"]) - second_score
    if float(best["score"]) < float(min_score):
        status = "NO_CONFIDENT_MATCH"
        picked = None
    elif margin < float(min_margin):
        status = "AMBIGUOUS"
        picked = None
    else:
        status = "MATCH"
        picked = best["candidate_id"]
    return {
        "schema": "GREMLIN_RELATIONAL_MEMORY_RETRIEVAL_V0_1",
        "status": status,
        "picked": picked,
        "best_score": float(best["score"]),
        "margin": margin,
        "min_score": float(min_score),
        "min_margin": float(min_margin),
        "ranked": rows,
        "cue_semantic_commitment": cue_packet["semantic_commitment"],
        "authority": dict(AUTHORITY),
    }


def elephant_memory_orbit(trace_id: str, text: str) -> dict[str, Any]:
    if not isinstance(trace_id, str) or not trace_id.strip():
        raise ValueError("trace_id must be non-empty")
    encoded = encode_memory_text(text)
    core = {
        "trace_id": trace_id.strip(),
        "semantic_commitment": encoded["semantic_commitment"],
        "phase36": encoded["phase36"],
        "amplitude36": encoded["amplitude36"],
    }
    return {
        "schema": "GREMLIN_ELEPHANT_MEMORY_ORBIT_V0_1",
        "artifact_type": "MEMORY_ORBIT",
        "status": "CANDIDATE_ONLY",
        **core,
        "orbit_commitment": _sha256(core),
        "authority": dict(AUTHORITY),
    }


def bees_coherence_finding(
    left_id: str,
    left: str | Mapping[str, Any],
    right_id: str,
    right: str | Mapping[str, Any],
) -> dict[str, Any]:
    if not all(isinstance(x, str) and x.strip() for x in (left_id, right_id)):
        raise ValueError("memory ids must be non-empty strings")
    similarity = memory_similarity(left, right)
    core = {
        "left_id": left_id.strip(),
        "right_id": right_id.strip(),
        "score": similarity["score"],
        "weighted_atom_jaccard": similarity["weighted_atom_jaccard"],
        "phase_coherence36": similarity["phase_coherence36"],
        "shared_atoms": similarity["shared_atoms"],
    }
    return {
        "schema": "GREMLIN_BEES_COHERENCE_FINDING_V0_1",
        "artifact_type": "COHERENCE_FINDING",
        "status": "CANDIDATE_ONLY",
        **core,
        "finding_commitment": _sha256(core),
        "reconcile_proposal_only": True,
        "authority": dict(AUTHORITY),
    }
