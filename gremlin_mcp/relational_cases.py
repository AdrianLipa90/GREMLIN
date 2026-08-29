from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

SCHEMA = "GREMLIN_RELATIONAL_CASES_V0_1"
VERSION = "0.1.0"

CASES: dict[str, dict[str, str]] = {
    "NOM": {"pl": "mianownik", "question": "kto? co?", "port_role": "source_or_subject"},
    "GEN": {"pl": "dopełniacz", "question": "kogo? czego?", "port_role": "origin_possession_partitive_or_governed_relation"},
    "DAT": {"pl": "celownik", "question": "komu? czemu?", "port_role": "recipient_target_or_orientation"},
    "ACC": {"pl": "biernik", "question": "kogo? co?", "port_role": "object_or_patient"},
    "INS": {"pl": "narzędnik", "question": "z kim? z czym? / kim? czym?", "port_role": "coupling_companion_predicative_or_instrumental_relation"},
    "LOC": {"pl": "miejscownik", "question": "o kim? o czym? / w kim? w czym?", "port_role": "topic_context_or_location"},
    "VOC": {"pl": "wołacz", "question": "o!", "port_role": "address_or_activation"},
}

# These are grammatical/relational port signatures, not claims that a case has
# exactly one semantic meaning. A binding carries both grammatical case and its
# operator-local role.
OPERATOR_SIGNATURES: dict[str, dict[str, Any]] = {
    "NAMES": {
        "required": ["NOM", "ACC", "INS"],
        "optional": [],
        "roles": {"NOM": "namer", "ACC": "entity_named", "INS": "assigned_name_or_designation"},
    },
    "DESCRIBES": {
        "required": ["NOM", "ACC"],
        "optional": ["INS", "LOC"],
        "roles": {"NOM": "describer", "ACC": "described_object", "INS": "coupled_model_or_predicative_medium", "LOC": "topic_or_context"},
    },
    "SPEAKS_ABOUT": {
        "required": ["NOM", "LOC"],
        "optional": ["INS"],
        "roles": {"NOM": "speaker", "LOC": "topic", "INS": "interlocutor"},
    },
    "CONNECTED_WITH": {
        "required": ["NOM", "INS"],
        "optional": [],
        "roles": {"NOM": "entity", "INS": "counterpart_in_relation"},
    },
    "BELONGS_TO": {
        "required": ["NOM", "GEN"],
        "optional": [],
        "roles": {"NOM": "entity", "GEN": "owner_domain_or_whole"},
    },
    "GIVES": {
        "required": ["NOM", "DAT", "ACC"],
        "optional": [],
        "roles": {"NOM": "giver", "DAT": "recipient", "ACC": "transferred_object"},
    },
    "ADDRESSES": {
        "required": ["NOM", "VOC"],
        "optional": [],
        "roles": {"NOM": "speaker", "VOC": "addressee"},
    },
}

_WORD = r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9_-]+"

_FIRST_PERSON = {
    "nazywam", "nazwałem", "nazwałam", "opisuję", "opisuje", "opisałem", "opisałam",
    "rozmawiam", "mówię", "mowie", "daję", "daje", "dałem", "dałam",
}

_OPERATOR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("NAMES", re.compile(r"\b(nazywam|nazywasz|nazywa|nazywamy|nazywacie|nazywają|nazywaja|nazwałem|nazwałam|nazwalem|nazwalam|nazwał|nazwała|nazwal|nazwala|nazwano)\b", re.IGNORECASE)),
    ("DESCRIBES", re.compile(r"\b(opisuję|opisuje|opisujesz|opisujemy|opisują|opisuja|opisałem|opisałam|opisalem|opisalam|opisał|opisała|opisal|opisala|opisano)\b", re.IGNORECASE)),
    ("SPEAKS_ABOUT", re.compile(r"\b(rozmawiam|rozmawiasz|rozmawia|rozmawiamy|rozmawiacie|rozmawiają|rozmawiaja|mówię|mowie|mówisz|mowisz|mówi|mowi)\b", re.IGNORECASE)),
    ("CONNECTED_WITH", re.compile(r"\b(jest\s+)?(związany|związana|związane|zwiazany|zwiazana|zwiazane|powiązany|powiązana|powiazany|powiazana|połączony|połączona|polaczony|polaczona)\b", re.IGNORECASE)),
    ("BELONGS_TO", re.compile(r"\b(należy|nalezy|należą|naleza|należał|nalezal|należała|nalezala)\b", re.IGNORECASE)),
    ("GIVES", re.compile(r"\b(daję|daje|dajesz|daje|dajemy|dają|daja|dałem|dałam|dalem|dalam|dał|dała|dal|dala)\b", re.IGNORECASE)),
)


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(value: Any) -> str:
    return hashlib.blake2b(
        b"GREMLIN-RELATIONAL-CASES/v0.1\0" + _canonical(value),
        digest_size=32,
    ).hexdigest()


def operator_signature(operator: str) -> dict[str, Any]:
    name = str(operator).strip().upper()
    if name not in OPERATOR_SIGNATURES:
        raise ValueError(f"unknown relational operator: {operator!r}")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "operator": name,
        **OPERATOR_SIGNATURES[name],
        "cases": {case: CASES[case] for case in OPERATOR_SIGNATURES[name]["required"] + OPERATOR_SIGNATURES[name]["optional"]},
        "authority": _authority(),
    }


def bind_relation(
    operator: str,
    bindings: Iterable[Mapping[str, Any]],
    *,
    evidence: str = "CALLER_SUPPLIED",
) -> dict[str, Any]:
    name = str(operator).strip().upper()
    signature = operator_signature(name)
    normalized: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    for raw in bindings:
        case = str(raw.get("case") or "").strip().upper()
        if case not in CASES:
            raise ValueError(f"unknown grammatical case: {case!r}")
        entity = str(raw.get("entity") or "").strip()
        if not entity:
            raise ValueError("relation binding requires non-empty entity")
        if case in seen_cases:
            raise ValueError(f"duplicate case binding for {case}")
        seen_cases.add(case)
        allowed = set(signature["required"]) | set(signature["optional"])
        if case not in allowed:
            raise ValueError(f"case {case} is not admitted by {name}")
        normalized.append(
            {
                "case": case,
                "case_name": CASES[case]["pl"],
                "question": CASES[case]["question"],
                "entity": entity,
                "operator_role": signature["roles"].get(case),
                "evidence": str(raw.get("evidence") or evidence),
                "confidence": float(raw.get("confidence", 1.0)),
            }
        )
    missing = [case for case in signature["required"] if case not in seen_cases]
    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "operator": name,
        "signature": {"required": signature["required"], "optional": signature["optional"]},
        "bindings": normalized,
        "missing_required_cases": missing,
        "complete": not missing,
        "epistemic_status": "CASE_TYPED_RELATION_CANDIDATE",
        "authority": _authority(),
    }
    core["relation_commitment"] = _commit(core)
    return core


def _clean_entity(value: str) -> str:
    return str(value).strip().strip(".,;:!?()[]{}\"'")


def _subject_before(text: str, start: int, verb: str) -> tuple[str, str, float]:
    if verb.casefold() in _FIRST_PERSON:
        return "@speaker", "FIRST_PERSON_VERB_MORPHOLOGY", 0.98
    prefix = text[:start].strip()
    words = re.findall(_WORD, prefix)
    if words:
        return words[-1], "EXPLICIT_PREVERBAL_TOKEN", 0.82
    return "@implicit_subject", "IMPLICIT_SUBJECT_UNRESOLVED", 0.45


def _after(text: str, end: int) -> str:
    return text[end:].strip().strip(".,;:!?")


def _phrase_after_preposition(tail: str, prep: str) -> str | None:
    # Bounded reference parser: stop at punctuation or another high-signal relation preposition.
    pattern = re.compile(
        rf"(?:^|\s){re.escape(prep)}\s+(?P<phrase>{_WORD}(?:\s+{_WORD}){{0,3}}?)(?=\s+(?:z|ze|o|do|dla|od|bez|ku|przy|w|na|po|nad|pod|przed|za)\s|[.,;:!?]|$)",
        re.IGNORECASE,
    )
    match = pattern.search(tail)
    return _clean_entity(match.group("phrase")) if match else None


def _parse_names(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    verb = match.group(1)
    subject, subject_evidence, subject_conf = _subject_before(text, match.start(), verb)
    tail = _after(text, match.end())
    words = re.findall(_WORD, tail)
    if len(words) < 2:
        return None
    # The governing verb "nazwać/nazywać" admits an ACC entity and an INS
    # predicative designation. The deterministic reference parser only binds
    # the compact two-slot form; longer clauses remain unresolved.
    acc = _clean_entity(words[0])
    ins = _clean_entity(words[1])
    return bind_relation(
        "NAMES",
        [
            {"case": "NOM", "entity": subject, "evidence": subject_evidence, "confidence": subject_conf},
            {"case": "ACC", "entity": acc, "evidence": "NAMES_GOVERNED_OBJECT", "confidence": 0.88},
            {"case": "INS", "entity": ins, "evidence": "NAMES_PREDICATIVE_DESIGNATION", "confidence": 0.88},
        ],
        evidence="POLISH_REFERENCE_RULE",
    )


def _parse_speaks_about(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    verb = match.group(1)
    subject, subject_evidence, subject_conf = _subject_before(text, match.start(), verb)
    tail = _after(text, match.end())
    topic = _phrase_after_preposition(tail, "o")
    companion = _phrase_after_preposition(tail, "z") or _phrase_after_preposition(tail, "ze")
    if not topic:
        return None
    bindings: list[dict[str, Any]] = [
        {"case": "NOM", "entity": subject, "evidence": subject_evidence, "confidence": subject_conf},
        {"case": "LOC", "entity": topic, "evidence": "SPEAK_ABOUT_O_PLUS_LOC", "confidence": 0.96},
    ]
    if companion:
        bindings.append({"case": "INS", "entity": companion, "evidence": "INTERLOCUTOR_Z_PLUS_INS", "confidence": 0.94})
    return bind_relation("SPEAKS_ABOUT", bindings, evidence="POLISH_REFERENCE_RULE")


def _parse_connected(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    prefix = text[:match.start()].strip()
    words = re.findall(_WORD, prefix)
    if not words:
        return None
    subject = _clean_entity(words[-1])
    tail = _after(text, match.end())
    companion = _phrase_after_preposition(tail, "z") or _phrase_after_preposition(tail, "ze")
    if not companion:
        return None
    return bind_relation(
        "CONNECTED_WITH",
        [
            {"case": "NOM", "entity": subject, "evidence": "EXPLICIT_PREVERBAL_SUBJECT", "confidence": 0.92},
            {"case": "INS", "entity": companion, "evidence": "CONNECTED_Z_PLUS_INS", "confidence": 0.95},
        ],
        evidence="POLISH_REFERENCE_RULE",
    )


def _parse_describes(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    verb = match.group(1)
    subject, subject_evidence, subject_conf = _subject_before(text, match.start(), verb)
    tail = _after(text, match.end())
    words = re.findall(_WORD, tail)
    if not words:
        return None
    obj = _clean_entity(words[0])
    bindings: list[dict[str, Any]] = [
        {"case": "NOM", "entity": subject, "evidence": subject_evidence, "confidence": subject_conf},
        {"case": "ACC", "entity": obj, "evidence": "DESCRIBES_GOVERNED_OBJECT", "confidence": 0.86},
    ]
    topic = _phrase_after_preposition(tail, "o")
    if topic:
        bindings.append({"case": "LOC", "entity": topic, "evidence": "O_PLUS_LOC_CONTEXT", "confidence": 0.82})
    return bind_relation("DESCRIBES", bindings, evidence="POLISH_REFERENCE_RULE")


def _parse_belongs(text: str, match: re.Match[str]) -> dict[str, Any] | None:
    prefix = text[:match.start()].strip()
    words = re.findall(_WORD, prefix)
    if not words:
        return None
    subject = _clean_entity(words[-1])
    tail = _after(text, match.end())
    owner = _phrase_after_preposition(tail, "do")
    if not owner:
        return None
    return bind_relation(
        "BELONGS_TO",
        [
            {"case": "NOM", "entity": subject, "evidence": "EXPLICIT_PREVERBAL_SUBJECT", "confidence": 0.9},
            {"case": "GEN", "entity": owner, "evidence": "BELONGS_DO_PLUS_GEN", "confidence": 0.97},
        ],
        evidence="POLISH_REFERENCE_RULE",
    )


def extract_relations(text: str, *, language: str = "pl") -> dict[str, Any]:
    raw = str(text).strip()
    if not raw:
        raise ValueError("text must be non-empty")
    lang = str(language).strip().lower()
    if lang not in {"pl", "polish"}:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "language": lang,
            "text": raw,
            "relations": [],
            "status": "LANGUAGE_PARSER_NOT_IMPLEMENTED",
            "operator_signatures": sorted(OPERATOR_SIGNATURES),
            "authority": _authority(),
        }

    relations: list[dict[str, Any]] = []
    for operator, pattern in _OPERATOR_PATTERNS:
        for match in pattern.finditer(raw):
            relation = None
            if operator == "NAMES":
                relation = _parse_names(raw, match)
            elif operator == "DESCRIBES":
                relation = _parse_describes(raw, match)
            elif operator == "SPEAKS_ABOUT":
                relation = _parse_speaks_about(raw, match)
            elif operator == "CONNECTED_WITH":
                relation = _parse_connected(raw, match)
            elif operator == "BELONGS_TO":
                relation = _parse_belongs(raw, match)
            if relation is not None:
                relation["surface_operator"] = match.group(0)
                relations.append(relation)

    core = {
        "schema": SCHEMA,
        "version": VERSION,
        "language": "pl",
        "text": raw,
        "relations": relations,
        "relation_count": len(relations),
        "status": "CASE_RELATIONS_EXTRACTED" if relations else "NO_REFERENCE_RULE_MATCH",
        "parser_scope": "DETERMINISTIC_POLISH_REFERENCE_RULES_V0_1",
        "operator_signatures": sorted(OPERATOR_SIGNATURES),
        "authority": _authority(),
    }
    core["parse_commitment"] = _commit(core)
    return core
