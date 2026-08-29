from __future__ import annotations

import argparse
import json
from pathlib import Path

from gremlin_mcp.dual_use_policy import capability_firewall, inherit_risk, make_policy_envelope


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    inherited = inherit_risk("BENIGN", ["DUAL_USE_HIGH", "DUAL_USE_LOW"])
    unknown = inherit_risk(None, [])
    high_request = capability_firewall(
        risk="DUAL_USE_HIGH",
        requested_action="REQUEST_EXECUTION",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    high_execute = capability_firewall(
        risk="DUAL_USE_HIGH",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    low_execute_no_human = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=False,
        tool_gate=True,
        sandboxed=True,
    )
    low_execute_gated = capability_firewall(
        risk="DUAL_USE_LOW",
        requested_action="EXECUTE",
        human_gate=True,
        tool_gate=True,
        sandboxed=True,
    )
    envelope = make_policy_envelope(
        object_kind="OPERATOR",
        object_commitment="probe-operator",
        declared_risk="DUAL_USE_LOW",
        parent_risks=["DUAL_USE_HIGH"],
        parent_commitments=["parent-a", "parent-b"],
        source_refs=["probe-source"],
        transformations=["discover", "validate"],
        evidence_refs=["probe-evidence"],
        confidence=0.9,
    )

    checks = {
        "risk_inheritance_monotonic": inherited.name == "DUAL_USE_HIGH",
        "unknown_fails_closed": unknown.name == "DUAL_USE_HIGH",
        "high_request_execution_blocked": high_request["admitted"] is False,
        "high_execute_blocked": high_execute["admitted"] is False,
        "low_execute_without_human_blocked": low_execute_no_human["admitted"] is False,
        "low_execute_requires_all_gates": low_execute_gated["admitted"] is True,
        "envelope_inherits_high": envelope["risk_class"] == "DUAL_USE_HIGH",
        "envelope_never_pre_admits_execution": envelope["execution_admitted"] is False,
        "canon_remains_blocked": envelope["canon_allowed"] is False,
    }

    receipt = {
        "schema": "GREMLIN_DUAL_USE_POLICY_PROBE_V0_1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "inherited_risk": inherited.name,
        "unknown_risk": unknown.name,
        "high_request_decision": high_request,
        "high_execute_decision": high_execute,
        "low_execute_no_human_decision": low_execute_no_human,
        "low_execute_gated_decision": low_execute_gated,
        "policy_envelope": envelope,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
