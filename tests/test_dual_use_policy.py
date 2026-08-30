from gremlin_mcp.dual_use_policy import (
    Action,
    RiskClass,
    allowed_actions_for,
    attach_policy,
    capability_firewall,
    inherit_risk,
    make_policy_envelope,
    policy_api,
)


def test_risk_inheritance_is_monotonic():
    assert inherit_risk("BENIGN", ["DUAL_USE_HIGH", "DUAL_USE_LOW"]) is RiskClass.DUAL_USE_HIGH


def test_unknown_risk_fails_closed_to_high():
    assert inherit_risk(None, []) is RiskClass.DUAL_USE_HIGH


def test_incomplete_context_raises_low_to_high():
    assert inherit_risk("DUAL_USE_LOW", [], context_complete=False) is RiskClass.DUAL_USE_HIGH


def test_high_risk_cannot_request_execution():
    decision = capability_firewall(
        risk="DUAL_USE_HIGH",
        requested_action="REQUEST_EXECUTION",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    assert decision["admitted"] is False
    assert decision["reason"] == "HIGH_OR_RESTRICTED_RISK_CANNOT_REQUEST_EXECUTION"


def test_restricted_action_set_is_defensive_only():
    assert allowed_actions_for("RESTRICTED") == ["ANALYZE", "DETECT", "MITIGATE", "MONITOR", "PATCH"]


def test_execution_requires_human_gate():
    decision = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=False,
        tool_gate=True,
        sandboxed=True,
    )
    assert decision["admitted"] is False


def test_execution_requires_tool_gate():
    decision = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=False,
        sandboxed=True,
    )
    assert decision["admitted"] is False


def test_execution_requires_sandbox():
    decision = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=True,
        sandboxed=False,
    )
    assert decision["admitted"] is False


def test_low_risk_fully_gated_execution_can_be_admitted_only_by_firewall():
    decision = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    assert decision["admitted"] is True
    assert decision["production_runtime_write"] is False
    assert decision["canon_allowed"] is False


def test_high_risk_execution_stays_blocked_even_with_all_gates():
    decision = capability_firewall(
        risk="DUAL_USE_HIGH",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    assert decision["admitted"] is False


def test_policy_commitment_is_deterministic_and_parent_commitments_are_preserved():
    first = make_policy_envelope(
        object_kind="RADICAL",
        object_commitment="abc",
        declared_risk="DUAL_USE_LOW",
        parent_risks=["BENIGN", "DUAL_USE_HIGH"],
        parent_commitments=["p2", "p1"],
        source_refs=["source-b", "source-a"],
        transformations=["extract", "compose"],
        evidence_refs=["ev2", "ev1"],
        confidence=0.9,
    )
    second = make_policy_envelope(
        object_kind="RADICAL",
        object_commitment="abc",
        declared_risk="DUAL_USE_LOW",
        parent_risks=["DUAL_USE_HIGH", "BENIGN"],
        parent_commitments=["p1", "p2"],
        source_refs=["source-a", "source-b"],
        transformations=["extract", "compose"],
        evidence_refs=["ev1", "ev2"],
        confidence=0.9,
    )
    assert first["risk_class"] == "DUAL_USE_HIGH"
    assert first["parent_commitments"] == ["p1", "p2"]
    assert first["policy_commitment"] == second["policy_commitment"]
    assert first["execution_admitted"] is False


def test_attach_policy_never_promotes_authority():
    candidate = {"commitment": "candidate-1", "payload": {"x": 1}}
    wrapped = attach_policy(
        candidate,
        object_kind="KAKU",
        declared_risk="BENIGN",
        confidence=1.0,
    )
    assert wrapped["dual_use_policy"]["execution_admitted"] is False
    assert wrapped["dual_use_policy"]["canon_allowed"] is False


def test_policy_api_inherit_and_firewall_are_fail_closed():
    inherited = policy_api(
        "inherit",
        {
            "declared_risk": "BENIGN",
            "parent_risks": ["DUAL_USE_HIGH"],
        },
    )
    assert inherited["risk_class"] == "DUAL_USE_HIGH"

    decision = policy_api(
        "firewall",
        {
            "risk": "RESTRICTED",
            "requested_action": Action.EXECUTE.value,
            "human_gate": True,
            "tool_gate": True,
            "sandboxed": True,
        },
    )
    assert decision["admitted"] is False
