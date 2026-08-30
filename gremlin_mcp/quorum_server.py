from __future__ import annotations

from typing import Any

from gremlin_mcp.evidence_quorum import assess_family_quorum
from gremlin_mcp.semantic_quorum_bridge import apply_semantic_producer_output_with_quorum
from gremlin_mcp.server import mcp, main as _server_main


@mcp.tool()
def gremlin_evidence_family_quorum(
    evidence: list[dict[str, Any]],
    min_unipolar_families: int = 2,
) -> dict[str, Any]:
    """Assess provenance-family diversity without treating family count as independence proof."""
    return assess_family_quorum(
        evidence,
        min_unipolar_families=min_unipolar_families,
    )


@mcp.tool()
def gremlin_semantic_quorum_apply(
    execution: dict[str, Any],
    producer_output: dict[str, Any],
    hound_receipt: dict[str, Any] | None = None,
    require_complete_coverage: bool = True,
    min_unipolar_families: int = 2,
) -> dict[str, Any]:
    """Apply semantic provenance validation plus strict unipolar provenance-family quorum."""
    return apply_semantic_producer_output_with_quorum(
        execution,
        producer_output=producer_output,
        hound_receipt=hound_receipt,
        require_complete_coverage=require_complete_coverage,
        min_unipolar_families=min_unipolar_families,
    )


def main() -> None:
    """Run normal GREMLIN MCP with strict family-quorum tools registered."""
    _server_main()


if __name__ == "__main__":
    main()
