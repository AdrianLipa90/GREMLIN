from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

from gremlin_mcp.role_registry import BESTIARY_ROLE_NAMES

TAU = 2.0 * math.pi
DIM = 36
OPEN = "OPEN"
TERMINAL_STATES = frozenset({"CLOSED", "FAILED", "QUARANTINED"})
MAX_IDENTIFIER_CHARS = 128
DEFAULT_MAX_NODES = 10_000


def _strict_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > MAX_IDENTIFIER_CHARS:
        raise ValueError(f"{field} must contain 1..{MAX_IDENTIFIER_CHARS} characters")
    return out


def _strict_species(value: Any) -> str:
    species = _strict_text(value, "species").upper()
    if species not in BESTIARY_ROLE_NAMES:
        raise ValueError(f"unsupported species: {species}")
    return species


def _strict_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise ValueError(f"{field} must be an iterable")
    out: list[str] = []
    for index, value in enumerate(values):
        item = _strict_text(value, f"{field}[{index}]")
        if item not in out:
            out.append(item)
    return tuple(out)


def _strict_phase36(value: Sequence[float] | None) -> tuple[float, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("phase36 must be a sequence")
    if len(value) != DIM:
        raise ValueError(f"phase36 must contain exactly {DIM} values")
    out = tuple(float(item) for item in value)
    if not all(math.isfinite(item) and 0.0 <= item < TAU for item in out):
        raise ValueError("phase36 must contain finite values in [0,2pi)")
    return out


def _phase_distance(
    left: tuple[float, ...] | None,
    right: tuple[float, ...] | None,
) -> float:
    if left is None or right is None:
        return 1.0
    rms = math.sqrt(
        sum(
            ((((a - b + math.pi) % TAU) - math.pi) ** 2)
            for a, b in zip(left, right)
        )
        / DIM
    )
    return min(1.0, rms / math.pi)


def _has_cycle(graph: Mapping[str, set[str]]) -> bool:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in done:
            return False
        if node_id in visiting:
            return True
        visiting.add(node_id)
        for dependency in graph.get(node_id, set()):
            if visit(dependency):
                return True
        visiting.remove(node_id)
        done.add(node_id)
        return False

    return any(visit(node_id) for node_id in graph)


@dataclass(frozen=True)
class NodeInstance:
    """Runtime node identity.

    caller_id is immutable invocation provenance.
    center_id is mutable non-causal orbital locality.
    authority_root_id is stable for the lifetime of the fabric.
    """

    node_id: str
    species: str
    authority_root_id: str
    caller_id: str | None
    center_id: str | None
    obligations: tuple[str, ...]
    phase36: tuple[float, ...] | None
    status: str
    execution_started: bool
    self_complete: bool
    result_commitment: str | None
    spawned_seq: int
    invocation_depth: int


@dataclass(frozen=True)
class SpawnRequest:
    species: str
    obligations: tuple[str, ...] = ()
    center_id: str | None = None
    causal_dependencies: tuple[str, ...] = ()
    join_to_caller: bool = True
    phase36: tuple[float, ...] | None = None
    node_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "species", _strict_species(self.species))
        object.__setattr__(
            self,
            "obligations",
            _strict_ids(self.obligations, "obligations"),
        )
        if self.center_id is not None:
            object.__setattr__(
                self,
                "center_id",
                _strict_text(self.center_id, "center_id"),
            )
        object.__setattr__(
            self,
            "causal_dependencies",
            _strict_ids(self.causal_dependencies, "causal_dependencies"),
        )
        if not isinstance(self.join_to_caller, bool):
            raise ValueError("join_to_caller must be boolean")
        object.__setattr__(self, "phase36", _strict_phase36(self.phase36))
        if self.node_id is not None:
            object.__setattr__(
                self,
                "node_id",
                _strict_text(self.node_id, "node_id"),
            )


@dataclass(frozen=True)
class CoordinationPoint:
    """Non-causal n-node rendezvous used only for execution locality."""

    point_id: str
    member_ids: tuple[str, ...]
    weight: float
    created_seq: int
    physical_claim: bool = False


__all__ = [
    "CoordinationPoint",
    "DEFAULT_MAX_NODES",
    "DIM",
    "MAX_IDENTIFIER_CHARS",
    "NodeInstance",
    "OPEN",
    "SpawnRequest",
    "TAU",
    "TERMINAL_STATES",
]
