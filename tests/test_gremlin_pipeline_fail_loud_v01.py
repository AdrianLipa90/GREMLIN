from __future__ import annotations

import pytest

from gremlin_mcp.pipeline import collect, fanout


class _Broker:
    def enqueue(self, species, payload, *, task_id):
        return {"task_commitment": "c" * 64}

    def task_result(self, task_id):
        return {"task_id": task_id, "state": "DONE"}


def test_species_items_must_be_strings() -> None:
    with pytest.raises(ValueError, match=r"species\[0\] must be a string"):
        fanout(_Broker(), {"x": 1}, [7])  # type: ignore[list-item,arg-type]


def test_species_argument_cannot_be_one_string_iterated_as_characters() -> None:
    with pytest.raises(ValueError, match="species must be an iterable of strings"):
        fanout(_Broker(), {"x": 1}, "SPIDER")  # type: ignore[arg-type]


def test_empty_or_non_string_request_id_does_not_generate_replacement_id() -> None:
    with pytest.raises(ValueError, match="request_id must be non-empty"):
        fanout(_Broker(), {"x": 1}, ["SPIDER"], request_id="")
    with pytest.raises(ValueError, match="request_id must be a string"):
        fanout(_Broker(), {"x": 1}, ["SPIDER"], request_id=0)  # type: ignore[arg-type]


def test_collect_rejects_non_string_task_ids_and_scalar_string_container() -> None:
    with pytest.raises(ValueError, match=r"task_ids\[0\] must be a string"):
        collect(_Broker(), [123])  # type: ignore[list-item,arg-type]
    with pytest.raises(ValueError, match="task_ids must be an iterable of strings"):
        collect(_Broker(), "task-1")  # type: ignore[arg-type]
