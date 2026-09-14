from __future__ import annotations

import pytest

from gremlin_mcp.worker_client import GremlinWorkerClient


def _handler(batch):
    return []


def test_worker_id_and_species_are_not_stringified() -> None:
    with pytest.raises(ValueError, match="worker_id must be a string"):
        GremlinWorkerClient(object(), worker_id=7, species=["SPIDER"], handler=_handler)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"species\[0\] must be a string"):
        GremlinWorkerClient(object(), worker_id="w", species=[7], handler=_handler)  # type: ignore[list-item]


def test_species_and_capabilities_must_be_real_string_iterables() -> None:
    with pytest.raises(ValueError, match="species must be an iterable of strings"):
        GremlinWorkerClient(object(), worker_id="w", species="SPIDER", handler=_handler)
    with pytest.raises(ValueError, match="capabilities must be an iterable of strings"):
        GremlinWorkerClient(object(), worker_id="w", species=["SPIDER"], capabilities="gpu", handler=_handler)


def test_width_and_batch_reject_boolean_or_string_coercion() -> None:
    with pytest.raises(ValueError, match="vector_width must be an integer"):
        GremlinWorkerClient(object(), worker_id="w", species=["SPIDER"], handler=_handler, vector_width="8")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_batch must be an integer"):
        GremlinWorkerClient(object(), worker_id="w", species=["SPIDER"], handler=_handler, max_batch=True)  # type: ignore[arg-type]


def test_handler_must_be_callable() -> None:
    with pytest.raises(ValueError, match="handler must be callable"):
        GremlinWorkerClient(object(), worker_id="w", species=["SPIDER"], handler=None)  # type: ignore[arg-type]
