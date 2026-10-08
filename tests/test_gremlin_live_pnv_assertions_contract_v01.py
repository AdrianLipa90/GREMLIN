"""Regression for the live PNV gate's previously missing request assertions.

The source under test is the GitHub repository policy file, not a synthesized
replacement. Keep expected rejection behaviour explicit and deterministic.
"""
from __future__ import annotations

import pytest

from gremlin_mcp.pnv_native_admission import (
    LIVE_PNV_RESOURCE,
    PNVNativeAdmissionError,
    _execute,
    _parse,
    _program_text,
)


def _verified_sources() -> dict[str, object]:
    generation = "test-generation"
    return {
        "current.identity_status": "VERIFIED",
        "current.domain_status": "ACTIVE",
        "current.authority_status": "VERIFIED",
        "current.tether_status": "ACTIVE",
        "current.guard_status": "ACTIVE",
        "current.guard_failures_count": 0,
        "current.generation": generation,
        "current.identity_generation": generation,
        "current.domain_generation": generation,
        "current.authority_generation": generation,
        "current.system_sync_status": "ALIGNED_CANDIDATE",
        "current.system_sync_generation": generation,
        "request.key_mutation": False,
        "request.production_effect": False,
    }


def test_live_gate_assertions_are_all_defined() -> None:
    program = _parse(_program_text(LIVE_PNV_RESOURCE))
    defined = {operation.name for operation in program.ops}
    assert set(program.assertions).issubset(defined)
    assert set(program.emits).issubset(defined)


def test_live_gate_evaluates_both_request_facts() -> None:
    program = _parse(_program_text(LIVE_PNV_RESOURCE))
    sources = _verified_sources()
    _, receipt = _execute(program, sources)
    assert receipt["emitted"]["MCP.ADMISSION.RETURN"]


@pytest.mark.parametrize("key", ["request.key_mutation", "request.production_effect"])
def test_live_gate_rejects_unadmitted_effects(key: str) -> None:
    program = _parse(_program_text(LIVE_PNV_RESOURCE))
    sources = _verified_sources()
    sources[key] = True
    with pytest.raises(PNVNativeAdmissionError, match="PNV_NATIVE_ASSERT_FAILED"):
        _execute(program, sources)
