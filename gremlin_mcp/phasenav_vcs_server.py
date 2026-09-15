from __future__ import annotations

import argparse
from typing import Any

from mcp.server import MCPServer

from gremlin_mcp import __version__
from gremlin_mcp.phasenav_vcs_capability import (
    CAPABILITY_SCHEMA,
    branch_prepare,
    bundle_prepare,
    checkpoint_prepare,
    commit_prepare,
    execution_receipt_build,
    tag_prepare,
    test_receipt_bind,
    validate_preflight,
    writes_prepare,
)

mcp = MCPServer(
    "GREMLIN-PHASENAV-VCS",
    title="GREMLIN PhaseNav VCS Capability",
    description=(
        "Fail-closed MCP surface for preparing and binding bounded PhaseNav-native VCS operations "
        "without shell, Git CLI, subprocess or direct canon authority."
    ),
    instructions=(
        "This server does not grant repository-write or canon authority. Every operation must be "
        "bound to PHASENAV_ACTION_PACKET_V1, an explicit gate receipt, ACTIVE tether and a valid "
        "GREMLIN same-generation triple-pulse attestation. v0.1 is COPY_ONLY and refuses direct "
        "main/master mutation, delete, move, rename, force-push, reset and rebase semantics. "
        "Checkpoint, tag and bundle records are preparations until a separately authorized "
        "PhaseNav-native VCS adapter returns execution evidence with shell_used=false."
    ),
    version=__version__,
)


@mcp.tool()
def gremlin_vcs_status() -> dict[str, Any]:
    """Return candidate capability status and authority firewalls."""
    return {
        "schema": CAPABILITY_SCHEMA,
        "status": "CANDIDATE_AVAILABLE",
        "copy_only": True,
        "shell_used": False,
        "git_cli_allowed": False,
        "subprocess_allowed": False,
        "direct_main_mutation": False,
        "native_adapter_execution_required": True,
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


@mcp.tool()
def gremlin_vcs_preflight(
    action_packet: dict[str, Any],
    gate_receipt: str,
    tether_status: str,
    gremlin_attestation: dict[str, Any],
    shell_used: bool = False,
    copy_only: bool = True,
) -> dict[str, Any]:
    """Validate the mandatory PhaseNav/GREMLIN authorization envelope and fail closed."""
    return validate_preflight(
        action_packet=action_packet,
        gate_receipt=gate_receipt,
        tether_status=tether_status,
        gremlin_attestation=gremlin_attestation,
        shell_used=shell_used,
        copy_only=copy_only,
    )


@mcp.tool()
def gremlin_vcs_checkpoint_prepare(
    preflight: dict[str, Any],
    repository: str,
    base_ref: str,
    expected_head: str,
) -> dict[str, Any]:
    """Prepare an immutable checkpoint descriptor before any logical VCS step."""
    return checkpoint_prepare(
        preflight=preflight,
        repository=repository,
        base_ref=base_ref,
        expected_head=expected_head,
    )


@mcp.tool()
def gremlin_vcs_branch_prepare(
    checkpoint: dict[str, Any],
    branch_name: str,
) -> dict[str, Any]:
    """Prepare a non-main candidate branch descriptor bound to the checkpoint."""
    return branch_prepare(checkpoint=checkpoint, branch_name=branch_name)


@mcp.tool()
def gremlin_vcs_writes_prepare(
    branch: dict[str, Any],
    writes: list[dict[str, Any]],
    copy_only: bool = True,
) -> dict[str, Any]:
    """Prepare exact UTF-8 create-only path/content commitments for first migration."""
    return writes_prepare(branch=branch, writes=writes, copy_only=copy_only)


@mcp.tool()
def gremlin_vcs_commit_prepare(
    prepared_writes: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    """Bind one logical-step commit message to the exact prepared writes."""
    return commit_prepare(prepared_writes=prepared_writes, message=message)


@mcp.tool()
def gremlin_vcs_tag_prepare(
    checkpoint: dict[str, Any],
    tag_name: str,
) -> dict[str, Any]:
    """Prepare the required pre-step checkpoint tag descriptor."""
    return tag_prepare(checkpoint=checkpoint, tag_name=tag_name)


@mcp.tool()
def gremlin_vcs_bundle_prepare(
    checkpoint: dict[str, Any],
    tag: dict[str, Any],
    branch: dict[str, Any],
) -> dict[str, Any]:
    """Prepare a portable bundle manifest commitment for the native VCS adapter."""
    return bundle_prepare(checkpoint=checkpoint, tag=tag, branch=branch)


@mcp.tool()
def gremlin_vcs_test_receipt_bind(
    logical_step: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Bind test evidence to one exact logical step without inventing PASS state."""
    return test_receipt_bind(logical_step=logical_step, evidence=evidence)


@mcp.tool()
def gremlin_vcs_execution_receipt_build(
    preflight: dict[str, Any],
    checkpoint: dict[str, Any],
    branch: dict[str, Any],
    prepared_writes: dict[str, Any],
    prepared_commit: dict[str, Any],
    tag: dict[str, Any],
    bundle: dict[str, Any],
    test_binding: dict[str, Any],
    adapter_evidence: dict[str, Any],
    before_head: str,
    after_head: str,
) -> dict[str, Any]:
    """Build PHASENAV_EXECUTION_RECEIPT_V1 only from successful native-adapter evidence."""
    return execution_receipt_build(
        preflight=preflight,
        checkpoint=checkpoint,
        branch=branch,
        prepared_writes=prepared_writes,
        prepared_commit=prepared_commit,
        tag=tag,
        bundle=bundle,
        test_binding=test_binding,
        adapter_evidence=adapter_evidence,
        before_head=before_head,
        after_head=after_head,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GREMLIN PhaseNav VCS MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", default=8771, type=int, help="HTTP bind port")
    parser.add_argument("--path", default="/mcp", help="Streamable HTTP MCP path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.transport == "stdio":
        mcp.run("stdio")
        return
    mcp.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        json_response=True,
    )


if __name__ == "__main__":
    main()
