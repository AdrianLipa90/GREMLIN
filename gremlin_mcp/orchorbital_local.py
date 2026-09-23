from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
import inspect
import json
from typing import Any

from gremlin_mcp.role_registry import LOCAL_EXECUTION_SPECIES

SCHEMA = "GREMLIN_ORCHORBITAL_LOCAL_ADAPTERS_V0_1"
VERSION = "0.1.0"

LocalHandler = Callable[[dict[str, Any]], Any]


def _strict_text(value: Any, field: str, *, maximum: int = 128) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    out = value.strip()
    if not out or len(out) > maximum:
        raise ValueError(f"{field} must contain 1..{maximum} characters")
    return out


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("local adapter values must be finite JSON data") from exc


@dataclass(frozen=True)
class LocalAdapter:
    species: str
    adapter_id: str
    version: str
    handler: LocalHandler
    reducer: LocalHandler | None
    replay_safe: bool
    side_effects: bool

    def public_view(self) -> dict[str, object]:
        return {
            "species": self.species,
            "adapter_id": self.adapter_id,
            "version": self.version,
            "replay_safe": self.replay_safe,
            "side_effects": self.side_effects,
            "reducer_available": self.reducer is not None,
            "callable_code_included": False,
        }


class LocalAdapterRegistry:
    """Explicit in-process adapters for roles without external worker carriers.

    This registry intentionally admits only LOCAL_EXECUTION_SPECIES. Core
    architectural boundaries such as OCTOPUS/GREMLIN/FERRET are not ordinary
    execution adapters and cannot be registered here.

    Adapters must declare replay-safe and side-effect-free semantics because a
    local node may be retried after a crash between execution and result commit.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, LocalAdapter] = {}

    def register(
        self,
        species: str,
        handler: LocalHandler,
        *,
        adapter_id: str,
        version: str = "0.1.0",
        reducer: LocalHandler | None = None,
        replay_safe: bool = True,
        side_effects: bool = False,
    ) -> LocalAdapter:
        if not isinstance(species, str):
            raise ValueError("species must be a string")
        name = species.strip().upper()
        if name not in LOCAL_EXECUTION_SPECIES:
            raise ValueError(
                f"species is not eligible for a local execution adapter: {name}"
            )
        if not callable(handler):
            raise ValueError("handler must be callable")
        if reducer is not None and not callable(reducer):
            raise ValueError("reducer must be callable when supplied")
        if replay_safe is not True:
            raise ValueError("local adapters must be replay_safe=true")
        if side_effects is not False:
            raise ValueError("local adapters must be side_effects=false")

        entry = LocalAdapter(
            species=name,
            adapter_id=_strict_text(adapter_id, "adapter_id"),
            version=_strict_text(version, "version"),
            handler=handler,
            reducer=reducer,
            replay_safe=True,
            side_effects=False,
        )
        prior = self._adapters.get(name)
        if prior is not None:
            if prior.public_view() != entry.public_view():
                raise ValueError(f"local adapter already registered for {name}")
            if prior.handler is not handler or prior.reducer is not reducer:
                raise ValueError(
                    f"local adapter callable drift detected for {name}"
                )
            return prior
        self._adapters[name] = entry
        return entry

    def has(self, species: str) -> bool:
        return isinstance(species, str) and species.strip().upper() in self._adapters

    def has_reducer(self, species: str) -> bool:
        if not isinstance(species, str):
            return False
        entry = self._adapters.get(species.strip().upper())
        return entry is not None and entry.reducer is not None

    def adapter(self, species: str) -> LocalAdapter:
        if not isinstance(species, str):
            raise ValueError("species must be a string")
        name = species.strip().upper()
        entry = self._adapters.get(name)
        if entry is None:
            raise ValueError(f"no local adapter registered for {name}")
        return entry

    def _invoke(
        self,
        callable_: LocalHandler,
        request: Mapping[str, Any],
        *,
        operation: str,
    ) -> Any:
        if not isinstance(request, Mapping):
            raise ValueError("local adapter request must be a mapping")
        body = deepcopy(dict(request))
        _canonical(body)
        output = callable_(body)
        if inspect.isawaitable(output):
            raise RuntimeError(
                f"local adapter {operation} must be synchronous in v0.1"
            )
        _canonical(output)
        return deepcopy(output)

    def execute(self, species: str, request: Mapping[str, Any]) -> Any:
        entry = self.adapter(species)
        return self._invoke(entry.handler, request, operation="handler")

    def reduce(self, species: str, request: Mapping[str, Any]) -> Any:
        entry = self.adapter(species)
        if entry.reducer is None:
            raise RuntimeError(f"no local reduction adapter registered for {entry.species}")
        return self._invoke(entry.reducer, request, operation="reducer")

    def manifest(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "adapters": [
                self._adapters[name].public_view()
                for name in sorted(self._adapters)
            ],
            "species": sorted(self._adapters),
            "replay_safe_required": True,
            "side_effects_allowed": False,
            "authority": "COGNITIVE_ROUTING_ONLY",
            "canon_allowed": False,
        }


__all__ = [
    "LocalAdapter",
    "LocalAdapterRegistry",
    "LocalHandler",
    "SCHEMA",
    "VERSION",
]
