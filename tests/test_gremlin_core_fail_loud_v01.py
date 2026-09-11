from __future__ import annotations

import pytest

from gremlin_mcp.core import plan_bestiary, species_profile


def test_species_profile_rejects_non_string_instead_of_stringifying() -> None:
    with pytest.raises(ValueError, match="species must be a string"):
        species_profile(7)  # type: ignore[arg-type]


def test_plan_rejects_non_string_species_key() -> None:
    with pytest.raises(ValueError, match="route_counts species must be a string"):
        plan_bestiary({7: 1})  # type: ignore[dict-item]


def test_plan_rejects_boolean_and_string_counts_instead_of_coercing() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        plan_bestiary({"SPIDER": True})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="must be an integer"):
        plan_bestiary({"SPIDER": "8"})  # type: ignore[dict-item]


def test_vector_width_requires_literal_positive_integer() -> None:
    with pytest.raises(ValueError, match="vector_width must be an integer"):
        plan_bestiary({"SPIDER": 1}, vector_width="8")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="vector_width must be an integer"):
        plan_bestiary({"SPIDER": 1}, vector_width=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="vector_width must be >= 1"):
        plan_bestiary({"SPIDER": 1}, vector_width=0)
