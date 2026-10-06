from __future__ import annotations

import copy

import pytest

from gremlin_mcp.action_relation_algebra import (
    RelationalActionAlgebraError,
    build_relational_action_contract,
    domain_transition,
    evaluate_relational_admission,
    meet_contracts,
    monotone_narrowing,
    relational_action_algebra_manifest,
    validate_relational_action_contract,
)


def _contract(**overrides):
    data = {
        "target": {
            "surface": "GITHUB",
            "domain": "AdrianLipa90/GREMLIN",
            "revision": "feat/relational-action-scope-algebra-v01-20260930",
        },
        "scope": {
            "operations": ["UPDATE_FILE", "CREATE_FILE"],
            "resources": ["gremlin_mcp/action_relation_algebra.py", "tests/test_action_relation_algebra.py"],
        },
        "visibility": "PRIVATE",
        "authority_modes": ["READ", "WRITE"],
        "reversibility": "REVERSIBLE",
        "provenance_refs": ["user-command:2026-09-30"],
        "relation_refs": ["relation:target-scope-authority"],
        "uncertainty": 0.0,
        "consequence_radius": "REPOSITORY",
        "fail_mode": "STOP",
        "consent_boundary": "EXPLICIT",
        "no_go_hits": [],
    }
    data.update(overrides)
    return build_relational_action_contract(**data)


def test_manifest_declares_no_implicit_fallback():
    manifest = relational_action_algebra_manifest()
    assert manifest["purpose"] == "FAIL_CLOSED_RELATIONAL_SCOPE_AND_AUTHORITY_ALGEBRA"
    assert "NO_IMPLICIT_FALLBACK" in manifest["invariants"]
    assert manifest["authority"]["execution_admitted"] is False


def test_high_consequence_exact_contract_allows_when_all_relations_are_closed():
    contract = _contract()
    decision = evaluate_relational_admission(
        contract,
        required_authority_modes=["WRITE"],
        high_consequence=True,
    )
    assert decision["decision"] == "ALLOW"
    assert decision["admissibility_scalar"] == 1


def test_nonzero_uncertainty_defers_high_consequence_action():
    contract = _contract(uncertainty=0.01)
    decision = evaluate_relational_admission(
        contract,
        required_authority_modes=["WRITE"],
        high_consequence=True,
    )
    assert decision["gate_state"]["UNCERTAINTY"] == 0
    assert decision["decision"] == "DEFER"


def test_no_go_hit_blocks_even_when_other_gates_pass():
    contract = _contract(no_go_hits=["NO_PUBLICATION"])
    decision = evaluate_relational_admission(
        contract,
        required_authority_modes=["WRITE"],
        high_consequence=True,
    )
    assert decision["gate_state"]["NO_GO"] == -1
    assert decision["decision"] == "DENY"


def test_missing_required_authority_blocks():
    contract = _contract(authority_modes=["READ"])
    decision = evaluate_relational_admission(
        contract,
        required_authority_modes=["WRITE"],
        high_consequence=True,
    )
    assert decision["gate_state"]["AUTHORITY"] == -1
    assert decision["decision"] == "DENY"


def test_domain_transition_requires_new_explicit_authorization():
    parent = _contract()
    candidate = _contract(
        target={
            "surface": "GITHUB",
            "domain": "AdrianLipa90/OTHER",
            "revision": "main",
        }
    )
    transition = domain_transition(parent, candidate)
    assert transition["domain_transition"] is True
    assert "domain" in transition["changed_target_dimensions"]
    assert transition["requires_new_explicit_authorization"] is True
    assert transition["admitted_by_parent_contract"] is False


def test_branch_change_is_also_a_domain_transition():
    parent = _contract()
    candidate = _contract(
        target={
            "surface": "GITHUB",
            "domain": "AdrianLipa90/GREMLIN",
            "revision": "main",
        }
    )
    transition = domain_transition(parent, candidate)
    assert transition["domain_transition"] is True
    assert transition["changed_target_dimensions"] == ["revision"]


def test_monotone_child_may_narrow_but_not_widen():
    parent = _contract()
    child = _contract(
        scope={
            "operations": ["UPDATE_FILE"],
            "resources": ["gremlin_mcp/action_relation_algebra.py"],
        },
        authority_modes=["WRITE"],
        consequence_radius="SINGLE_RESOURCE",
        parent_contract_sha256=parent["contract_sha256"],
    )
    verdict = monotone_narrowing(parent, child)
    assert verdict["status"] == "PASS"
    assert verdict["monotone_narrowing"] is True

    widened = _contract(
        scope={
            "operations": ["UPDATE_FILE", "CREATE_FILE", "DELETE_FILE"],
            "resources": [
                "gremlin_mcp/action_relation_algebra.py",
                "tests/test_action_relation_algebra.py",
                "README.md",
            ],
        },
        authority_modes=["READ", "WRITE", "PUBLISH"],
        visibility="PUBLIC",
        parent_contract_sha256=parent["contract_sha256"],
    )
    verdict = monotone_narrowing(parent, widened)
    assert verdict["status"] == "BLOCK"
    assert "SCOPE_OPERATIONS_WIDENED" in verdict["failures"]
    assert "AUTHORITY_WIDENED" in verdict["failures"]
    assert "VISIBILITY_WIDENED" in verdict["failures"]


def test_provenance_and_no_go_cannot_silently_disappear_from_child():
    parent = _contract(
        no_go_hits=["NO_PUBLICATION"],
        provenance_refs=["evidence:a", "evidence:b"],
    )
    child = _contract(
        no_go_hits=[],
        provenance_refs=["evidence:a"],
        parent_contract_sha256=parent["contract_sha256"],
    )
    verdict = monotone_narrowing(parent, child)
    assert "PROVENANCE_DROPPED" in verdict["failures"]
    assert "NO_GO_EVIDENCE_DROPPED" in verdict["failures"]


def test_contract_meet_intersects_permissions_and_accumulates_evidence():
    first = _contract(
        authority_modes=["READ", "WRITE"],
        provenance_refs=["evidence:a"],
        relation_refs=["relation:a"],
        consequence_radius="REPOSITORY",
    )
    second = _contract(
        scope={
            "operations": ["UPDATE_FILE"],
            "resources": ["gremlin_mcp/action_relation_algebra.py"],
        },
        authority_modes=["WRITE", "MERGE"],
        provenance_refs=["evidence:b"],
        relation_refs=["relation:b"],
        consequence_radius="ORGANIZATION",
    )
    combined = meet_contracts(first, second)
    assert combined["scope"]["operations"] == ["UPDATE_FILE"]
    assert combined["scope"]["resources"] == ["gremlin_mcp/action_relation_algebra.py"]
    assert combined["authority_modes"] == ["WRITE"]
    assert combined["provenance_refs"] == ["evidence:a", "evidence:b"]
    assert combined["relation_refs"] == ["relation:a", "relation:b"]
    assert combined["consequence_radius"] == "ORGANIZATION"


def test_cross_domain_meet_is_forbidden():
    first = _contract()
    second = _contract(
        target={
            "surface": "GITHUB",
            "domain": "AdrianLipa90/OTHER",
            "revision": "main",
        }
    )
    with pytest.raises(RelationalActionAlgebraError, match="new explicit authorization"):
        meet_contracts(first, second)


def test_implicit_fallback_cannot_be_encoded():
    with pytest.raises(RelationalActionAlgebraError, match="fail_mode"):
        _contract(fail_mode="FALLBACK")


def test_commitment_detects_tampering():
    contract = _contract()
    validate_relational_action_contract(contract)
    forged = copy.deepcopy(contract)
    forged["visibility"] = "PUBLIC"
    with pytest.raises(RelationalActionAlgebraError, match="commitment mismatch"):
        validate_relational_action_contract(forged)


def test_meet_keeps_unknown_visibility_unresolved_instead_of_guessing_private():
    known = _contract(visibility="PRIVATE")
    unknown = _contract(visibility="UNKNOWN")
    combined = meet_contracts(known, unknown)
    assert combined["visibility"] == "UNKNOWN"
    decision = evaluate_relational_admission(
        combined,
        required_authority_modes=["WRITE"],
        high_consequence=True,
    )
    assert decision["gate_state"]["VISIBILITY"] == 0
    assert decision["decision"] == "DEFER"


def test_uncertainty_reduction_requires_new_provenance():
    parent = _contract(uncertainty=0.2, provenance_refs=["evidence:a"])
    unsupported = _contract(
        uncertainty=0.1,
        provenance_refs=["evidence:a"],
        parent_contract_sha256=parent["contract_sha256"],
    )
    verdict = monotone_narrowing(parent, unsupported)
    assert "UNCERTAINTY_REDUCTION_WITHOUT_NEW_PROVENANCE" in verdict["failures"]

    supported = _contract(
        uncertainty=0.1,
        provenance_refs=["evidence:a", "evidence:b"],
        parent_contract_sha256=parent["contract_sha256"],
    )
    verdict = monotone_narrowing(parent, supported)
    assert verdict["status"] == "PASS"


def test_operation_scope_is_case_canonical():
    contract = _contract(
        scope={
            "operations": ["update_file", "UPDATE_FILE"],
            "resources": ["gremlin_mcp/action_relation_algebra.py"],
        }
    )
    assert contract["scope"]["operations"] == ["UPDATE_FILE"]
