from __future__ import annotations

from typing import Any

from gremlin_mcp.evidence_origin import (
    assess_evidence_origin_lineage,
    build_evidence_origin_assignment,
    verify_evidence_origin_assignment,
)
from gremlin_mcp.semantic_origin_bridge import apply_semantic_producer_output_with_origin_lineage
from gremlin_mcp.server import mcp, main as _server_main


@mcp.tool()
def gremlin_evidence_origin_assign(
    source_receipt: dict[str, Any],
    origin_refs: list[dict[str, Any]] | None,
    producer_id: str,
    producer_version: str,
    mode: str,
    rationale_code: str = "EXPLICIT_ORIGIN_ASSIGNMENT",
    model_id: str | None = None,
) -> dict[str, Any]:
    """Create a commitment-bound candidate underlying-evidence origin assignment."""
    return build_evidence_origin_assignment(
        source_receipt=source_receipt,
        origin_refs=origin_refs,
        producer_id=producer_id,
        producer_version=producer_version,
        mode=mode,
        rationale_code=rationale_code,
        model_id=model_id,
    )


@mcp.tool()
def gremlin_evidence_origin_verify(
    assignment: dict[str, Any],
    source_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify one origin assignment against exact execution source receipts."""
    return verify_evidence_origin_assignment(
        assignment,
        source_receipts=source_receipts,
    )


@mcp.tool()
def gremlin_evidence_origin_policy(
    guard_evidence: list[dict[str, Any]],
    evidence_kind_assignments: list[dict[str, Any]],
    origin_assignments: list[dict[str, Any]],
    claim_mode: str | None,
    min_origin_groups: int | None = None,
) -> dict[str, Any]:
    """Assess explicit underlying-origin lineage groups for direct claim evidence."""
    return assess_evidence_origin_lineage(
        guard_evidence,
        evidence_kind_assignments=evidence_kind_assignments,
        origin_assignments=origin_assignments,
        claim_mode=claim_mode,
        min_origin_groups=min_origin_groups,
    )


@mcp.tool()
def gremlin_semantic_origin_apply(
    execution: dict[str, Any],
    producer_output: dict[str, Any],
    evidence_kind_assignments: list[dict[str, Any]],
    evidence_origin_assignments: list[dict[str, Any]],
    claim_mode: str | None,
    hound_receipt: dict[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
    min_direct_families: int = 1,
    min_origin_groups: int | None = None,
) -> dict[str, Any]:
    """Apply semantic, provenance-family, evidence-kind and origin-lineage gates."""
    return apply_semantic_producer_output_with_origin_lineage(
        execution,
        producer_output=producer_output,
        evidence_kind_assignments=evidence_kind_assignments,
        evidence_origin_assignments=evidence_origin_assignments,
        claim_mode=claim_mode,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
        min_unipolar_families=min_unipolar_families,
        min_direct_families=min_direct_families,
        min_origin_groups=min_origin_groups,
    )


def main() -> None:
    """Run normal GREMLIN MCP with strict evidence-origin lineage tools registered."""
    _server_main()


if __name__ == "__main__":
    main()
