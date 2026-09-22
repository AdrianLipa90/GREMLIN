from __future__ import annotations

import pytest

from gremlin_mcp.core import bestiary_manifest, species_profile
from gremlin_mcp.memory_capabilities import evaluate_access, issue_capability_token
from gremlin_mcp.phasenav_runtime import status as phasenav_status


def _allow(*, beast: str, operation: str, artifact_type: str) -> dict:
    token = issue_capability_token(
        beast=beast,
        layer="RELATIONAL",
        operation=operation,
        artifact_type=artifact_type,
        subject_scope="memory:alpha",
        generation_scope="gen:1",
        task_scope="task:1",
    )
    return evaluate_access(
        beast=beast,
        layer="RELATIONAL",
        operation=operation,
        artifact_type=artifact_type,
        subject_id="memory:alpha",
        generation_id="gen:1",
        task_id="task:1",
        token=token,
    )


def test_relational_memory_roles_are_manifested_without_phase_carrier_promotion() -> None:
    names = {row["name"] for row in bestiary_manifest()["species"]}
    assert {"ELEPHANT", "BEES"} <= names
    assert len(names) == 20
    assert species_profile("ELEPHANT")["stage"] == "memory"
    assert species_profile("BEES")["stage"] == "coherence"
    assert species_profile("ELEPHANT")["scheduler_profile"] is None
    assert species_profile("BEES")["scheduler_profile"] is None

    # Historical/current validated PhaseNav carrier surface remains 18 until
    # separate carrier validation explicitly promotes the two memory roles.
    phase = phasenav_status()
    assert phase["species_count"] == 18
    assert "ELEPHANT" not in phase["species"]
    assert "BEES" not in phase["species"]


def test_elephant_can_consolidate_memory_orbits_but_cannot_overwrite() -> None:
    receipt = _allow(
        beast="ELEPHANT",
        operation="CONSOLIDATE",
        artifact_type="MEMORY_ORBIT",
    )
    assert receipt["decision"] == "ALLOW"
    assert receipt["reason_code"] == "POLICY_AND_SCOPE_MATCH"

    with pytest.raises(PermissionError):
        issue_capability_token(
            beast="ELEPHANT",
            layer="RELATIONAL",
            operation="OVERWRITE",
            artifact_type="MEMORY_ORBIT",
            subject_scope="memory:alpha",
            generation_scope="gen:1",
            task_scope="task:1",
        )


def test_bees_can_emit_anti_entropy_delta_but_cannot_consolidate_memory() -> None:
    receipt = _allow(
        beast="BEES",
        operation="DERIVE",
        artifact_type="ANTI_ENTROPY_DELTA",
    )
    assert receipt["decision"] == "ALLOW"
    assert receipt["reason_code"] == "POLICY_AND_SCOPE_MATCH"

    with pytest.raises(PermissionError):
        issue_capability_token(
            beast="BEES",
            layer="RELATIONAL",
            operation="CONSOLIDATE",
            artifact_type="MEMORY_ORBIT",
            subject_scope="memory:alpha",
            generation_scope="gen:1",
            task_scope="task:1",
        )


def test_bees_reconciliation_is_proposal_only() -> None:
    receipt = _allow(
        beast="BEES",
        operation="DERIVE",
        artifact_type="RECONCILE_PROPOSAL",
    )
    assert receipt["decision"] == "ALLOW"

    with pytest.raises(PermissionError):
        issue_capability_token(
            beast="BEES",
            layer="RELATIONAL",
            operation="IN_PLACE_EDIT",
            artifact_type="RECONCILE_PROPOSAL",
            subject_scope="memory:alpha",
            generation_scope="gen:1",
            task_scope="task:1",
        )
