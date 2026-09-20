from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "gremlin_mcp" / "core.py"
CONTRACT = ROOT / "spec" / "GREMLIN_ROLE_CAPABILITY_CONTRACT_V1.json"
HIVE_SPEC = ROOT / "spec" / "GREMLIN_ORBITAL_HIVE_MEMORY_V0_1.md"


def _core_roles() -> dict[str, dict[str, str]]:
    tree = ast.parse(CORE.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "BESTIARY_ROLES"
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    raise AssertionError("BESTIARY_ROLES assignment not found")


def test_role_capability_contract_matches_runtime_core_exactly() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema"] == "GREMLIN_ROLE_CAPABILITY_CONTRACT_V1"
    assert contract["roles"] == _core_roles()
    assert contract["canon_allowed"] is False


def test_hive_documentation_does_not_swap_hound_and_raven() -> None:
    text = HIVE_SPEC.read_text(encoding="utf-8")
    assert "+--> RAVEN memory/similarity" in text
    assert "+--> HOUND contradiction/anomaly/test targets" in text
    assert "+--> OWL evidence/provenance audit" in text
    assert "HOUND evidence/provenance" not in text
    assert "RAVEN contradiction checks" not in text
