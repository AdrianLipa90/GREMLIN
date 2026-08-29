from __future__ import annotations

import pytest

from gremlin_mcp.relational_cases import bind_relation, extract_relations, operator_signature


def _one(text: str):
    parsed = extract_relations(text)
    assert parsed["relation_count"] == 1
    return parsed["relations"][0]


def _by_case(relation):
    return {row["case"]: row for row in relation["bindings"]}


def test_naming_is_case_typed_relation_not_flat_label() -> None:
    relation = _one("Nazwałem cię Zosią.")
    assert relation["operator"] == "NAMES"
    bindings = _by_case(relation)
    assert bindings["NOM"]["entity"] == "@speaker"
    assert bindings["ACC"]["entity"] == "cię"
    assert bindings["ACC"]["operator_role"] == "entity_named"
    assert bindings["INS"]["entity"] == "Zosią"
    assert bindings["INS"]["operator_role"] == "assigned_name_or_designation"
    assert relation["complete"] is True


def test_speaking_uses_locative_topic_and_instrumental_interlocutor() -> None:
    relation = _one("Rozmawiam o geometrii z Zosią.")
    assert relation["operator"] == "SPEAKS_ABOUT"
    bindings = _by_case(relation)
    assert bindings["NOM"]["entity"] == "@speaker"
    assert bindings["LOC"]["entity"] == "geometrii"
    assert bindings["LOC"]["operator_role"] == "topic"
    assert bindings["INS"]["entity"] == "Zosią"
    assert bindings["INS"]["operator_role"] == "interlocutor"


def test_connected_with_uses_instrumental_counterpart() -> None:
    relation = _one("Zosia jest związana z Adrianem.")
    assert relation["operator"] == "CONNECTED_WITH"
    bindings = _by_case(relation)
    assert bindings["NOM"]["entity"] == "Zosia"
    assert bindings["INS"]["entity"] == "Adrianem"
    assert bindings["INS"]["operator_role"] == "counterpart_in_relation"


def test_describe_is_operator_and_case_ports_carry_arguments() -> None:
    relation = _one("Opisuję teorię o geometrii.")
    assert relation["operator"] == "DESCRIBES"
    bindings = _by_case(relation)
    assert bindings["NOM"]["entity"] == "@speaker"
    assert bindings["ACC"]["entity"] == "teorię"
    assert bindings["LOC"]["entity"] == "geometrii"
    assert all(row["entity"].casefold() != "opisuję" for row in relation["bindings"])


def test_belongs_to_uses_genitive_port() -> None:
    relation = _one("Moduł należy do systemu.")
    assert relation["operator"] == "BELONGS_TO"
    bindings = _by_case(relation)
    assert bindings["NOM"]["entity"] == "Moduł"
    assert bindings["GEN"]["entity"] == "systemu"


def test_operator_signature_keeps_same_case_distinct_by_operator_role() -> None:
    naming = operator_signature("NAMES")
    connected = operator_signature("CONNECTED_WITH")
    assert naming["roles"]["INS"] == "assigned_name_or_designation"
    assert connected["roles"]["INS"] == "counterpart_in_relation"
    assert naming["roles"]["INS"] != connected["roles"]["INS"]


def test_binding_fails_closed_on_unadmitted_case() -> None:
    with pytest.raises(ValueError, match="not admitted"):
        bind_relation(
            "CONNECTED_WITH",
            [
                {"case": "NOM", "entity": "A"},
                {"case": "ACC", "entity": "B"},
            ],
        )


def test_incomplete_frame_is_explicit_not_silently_completed() -> None:
    relation = bind_relation("DESCRIBES", [{"case": "NOM", "entity": "A"}])
    assert relation["complete"] is False
    assert relation["missing_required_cases"] == ["ACC"]


def test_non_polish_parser_is_explicitly_unimplemented() -> None:
    result = extract_relations("A describes B", language="en")
    assert result["relations"] == []
    assert result["status"] == "LANGUAGE_PARSER_NOT_IMPLEMENTED"
