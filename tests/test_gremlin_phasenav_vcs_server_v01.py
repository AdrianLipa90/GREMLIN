from __future__ import annotations

from gremlin_mcp.phasenav_vcs_server import (
    gremlin_vcs_preflight,
    gremlin_vcs_status,
)


def _attestation() -> dict:
    generation = "server-test-gen-001"
    return {
        "schema": "GREMLIN_TRIPLE_PULSE_ATTESTATION_V0_1",
        "generation": generation,
        "identity_receipt": {"generation": generation, "status": "VERIFIED"},
        "domain_receipt": {"generation": generation, "status": "VERIFIED"},
        "authority_receipt": {"generation": generation, "status": "VERIFIED"},
    }


def test_dedicated_server_reports_bounded_vcs_capability() -> None:
    status = gremlin_vcs_status()
    assert status["schema"] == "GREMLIN_PHASENAV_MCP_VCS_CAPABILITY_V0_1"
    assert status["status"] == "CANDIDATE_AVAILABLE"
    assert status["copy_only"] is True
    assert status["shell_used"] is False
    assert status["git_cli_allowed"] is False
    assert status["subprocess_allowed"] is False
    assert status["direct_main_mutation"] is False
    assert status["native_adapter_execution_required"] is True
    assert status["canon_allowed"] is False


def test_dedicated_server_preflight_binds_triple_pulse_and_action_packet() -> None:
    result = gremlin_vcs_preflight(
        action_packet={
            "schema": "PHASENAV_ACTION_PACKET_V1",
            "action_id": "server-test-action-001",
        },
        gate_receipt="server-test-gate-001",
        tether_status="ACTIVE",
        gremlin_attestation=_attestation(),
        shell_used=False,
        copy_only=True,
    )
    assert result["status"] == "PREFLIGHT_PASS"
    assert result["tether_status"] == "ACTIVE"
    assert result["shell_used"] is False
    assert result["copy_only"] is True
    assert len(result["preflight_commitment"]) == 64
