from __future__ import annotations

from typing import Any

from gremlin_mcp.evidence_kind import (
    assess_evidence_kind_policy,
    build_evidence_kind_assignment,
    verify_evidence_kind_assignment,
)
from gremlin_mcp.semantic_kind_bridge import apply_semantic_producer_output_with_kind_policy
from gremlin_mcp.server import mcp, main as _server_main


@mcp.tool()
def gremlin_evidence_kind_assign(
    source_receipt: dict[str, Any],
    evidence_kind: str | None,
    producer_id: str,
    producer_version: str,
    mode: str,
    rationale_code: str = "EXPLICIT_TYPED_ASSIGNMENT",
    model_id: str | None = None,
) -> dict[str, Any]:
    """Create a commitment-bound candidate evidence-kind assignment; no automatic kind inference."""
    return build_evidence_kind_assignment(
        source_receipt=source_receipt,
        evidence_kind=evidence_kind,
        producer_id=producer_id,
        producer_version=producer_version,
        mode=mode,
        rationale_code=rationale_code,
        model_id=model_id,
    )


@mcp.tool()
def gremlin_evidence_kind_verify(
    assignment: dict[str, Any],
    source_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify one evidence-kind assignment against exact execution source receipts."""
    return verify_evidence_kind_assignment(
        assignment,
        source_receipts=source_receipts,
    )


@mcp.tool()
def gremlin_evidence_kind_policy(
    guard_evidence: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    claim_mode: str | None,
    min_direct_families: int = 1,
) -> dict[str, Any]:
    """Evaluate explicit evidence kinds against a declared claim mode."""
    return assess_evidence_kind_policy(
        guard_evidence,
        assignments=assignments,
        claim_mode=claim_mode,
        min_direct_families=min_direct_families,
    )


@mcp.tool()
def gremlin_semantic_kind_apply(
    execution: dict[str, Any],
    producer_output: dict[str, Any],
    evidence_kind_assignments: list[dict[str, Any]],
    claim_mode: str | None,
    hound_receipt: dict[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
    min_direct_families: int = 1,
) -> dict[str, Any]:
    """Apply semantic integrity, family quorum and explicit claim-mode evidence-kind gates."""
    return apply_semantic_producer_output_with_kind_policy(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=evidence_kind_assignments,
        claim_mode=claim_mode,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
        min_unipolar_families=min_unipolar_families,
        min_direct_families=min_direct_families,
    )


def main() -> None:
    """Run normal GREMLIN MCP with strict evidence-kind policy tools registered."""
    _server_main()


if __name__ == "__main__":
    main()
