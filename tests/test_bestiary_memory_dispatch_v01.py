from __future__ import annotations

import pytest

from gremlin_mcp.memory_capabilities import (
    validate_access_receipt,
    validate_capability_token,
    validate_task_authorization_bundle,
)
from gremlin_mcp.persistent_workers import PersistentWorkerBroker
from gremlin_mcp.pipeline import fanout
from gremlin_mcp.router import route
from gremlin_mcp.workers import (
    MEMORY_AUTHORIZATION_KEY,
    MEMORY_REQUESTS_KEY,
    WorkerBroker,
)


def _request(
    *,
    layer: str,
    operation: str,
    artifact_type: str,
    subject_id: str = "spectroscopy:ring-6",
    generation_id: str = "gen-001",
) -> dict:
    return {
        "layer": layer,
        "operation": operation,
        "artifact_type": artifact_type,
        "subject_id": subject_id,
        "generation_id": generation_id,
    }


def test_direct_worker_enqueue_authorizes_memory_before_task_creation() -> None:
    broker = WorkerBroker()
    task = broker.enqueue(
        "SPIDER",
        {
            "work": "write relation graph",
            MEMORY_REQUESTS_KEY: [
                _request(
                    layer="RELATIONAL",
                    operation="GRAPH_APPEND",
                    artifact_type="GRAPH_SNAPSHOT",
                )
            ],
        },
        task_id="spider-direct",
    )

    payload = task["payload"]
    assert MEMORY_REQUESTS_KEY not in payload
    assert MEMORY_AUTHORIZATION_KEY in payload
    authorization = payload[MEMORY_AUTHORIZATION_KEY]
    assert authorization["beast"] == "SPIDER"
    assert authorization["task_id"] == "spider-direct"
    assert len(authorization["tokens"]) == 1
    assert len(authorization["receipts"]) == 1
    assert validate_task_authorization_bundle(authorization)["authorization_id"] == authorization["authorization_id"]
    assert validate_capability_token(authorization["tokens"][0])["beast"] == "SPIDER"
    assert validate_access_receipt(authorization["receipts"][0])["decision"] == "ALLOW"


def test_forbidden_direct_memory_request_does_not_create_task() -> None:
    broker = WorkerBroker()
    with pytest.raises(PermissionError):
        broker.enqueue(
            "RAVEN",
            {
                "work": "try graph write",
                MEMORY_REQUESTS_KEY: [
                    _request(
                        layer="RELATIONAL",
                        operation="GRAPH_APPEND",
                        artifact_type="GRAPH_SNAPSHOT",
                    )
                ],
            },
            task_id="raven-forbidden",
        )

    with pytest.raises(ValueError, match="unknown task_id"):
        broker.task_result("raven-forbidden")


def test_caller_cannot_forge_broker_owned_authorization_bundle() -> None:
    broker = WorkerBroker()
    with pytest.raises(ValueError, match="broker-owned"):
        broker.enqueue(
            "SPIDER",
            {
                "work": "forged",
                MEMORY_AUTHORIZATION_KEY: {"beast": "SPIDER", "claims": {"anything": True}},
            },
            task_id="forged-auth",
        )


def test_fanout_partitions_memory_requests_by_species() -> None:
    broker = WorkerBroker()
    broker.register_worker("spider-worker", ["SPIDER"], vector_width=4, max_batch=4)
    broker.register_worker("raven-worker", ["RAVEN"], vector_width=4, max_batch=4)

    result = fanout(
        broker,
        {
            "text": "compare memory and relation graph",
            MEMORY_REQUESTS_KEY: [
                {
                    "species": "SPIDER",
                    **_request(
                        layer="RELATIONAL",
                        operation="GRAPH_APPEND",
                        artifact_type="GRAPH_SNAPSHOT",
                    ),
                },
                {
                    "species": "RAVEN",
                    **_request(
                        layer="SEMANTIC",
                        operation="DERIVE",
                        artifact_type="MEMORY_INDEX",
                    ),
                },
            ],
        },
        ["SPIDER", "RAVEN"],
        request_id="partitioned",
    )
    assert result["status"] == "SPECIALISTS_QUEUED"

    spider = broker.claim("spider-worker", species="SPIDER", limit=1)
    raven = broker.claim("raven-worker", species="RAVEN", limit=1)

    spider_auth = spider["tasks"][0]["payload"][MEMORY_AUTHORIZATION_KEY]
    raven_auth = raven["tasks"][0]["payload"][MEMORY_AUTHORIZATION_KEY]

    assert [row["artifact_type"] for row in spider_auth["tokens"]] == ["GRAPH_SNAPSHOT"]
    assert [row["operation"] for row in spider_auth["tokens"]] == ["GRAPH_APPEND"]
    assert [row["artifact_type"] for row in raven_auth["tokens"]] == ["MEMORY_INDEX"]
    assert [row["operation"] for row in raven_auth["tokens"]] == ["DERIVE"]

    assert MEMORY_REQUESTS_KEY not in spider["tasks"][0]["payload"]
    assert MEMORY_REQUESTS_KEY not in raven["tasks"][0]["payload"]


def test_fanout_forbidden_species_request_fails_before_enqueue() -> None:
    broker = WorkerBroker()
    with pytest.raises(PermissionError):
        fanout(
            broker,
            {
                "text": "raven should not write spider graphs",
                MEMORY_REQUESTS_KEY: [
                    {
                        "species": "RAVEN",
                        **_request(
                            layer="RELATIONAL",
                            operation="GRAPH_APPEND",
                            artifact_type="GRAPH_SNAPSHOT",
                        ),
                    }
                ],
            },
            ["RAVEN"],
            request_id="fanout-deny",
        )

    assert broker.queue_status()["tasks"]["RAVEN"]["QUEUED"] == 0


def test_fanout_requires_explicit_species_selector_for_memory_requests() -> None:
    broker = WorkerBroker()
    with pytest.raises(ValueError, match="requires explicit species selector"):
        fanout(
            broker,
            {
                "text": "ambiguous memory request",
                MEMORY_REQUESTS_KEY: [
                    _request(
                        layer="SEMANTIC",
                        operation="READ_PAYLOAD",
                        artifact_type="MEMORY_INDEX",
                    )
                ],
            },
            ["RAVEN"],
            request_id="missing-selector",
        )


def test_memory_request_metadata_does_not_influence_octopus_route() -> None:
    decision = route(
        {
            "text": "plain neutral payload",
            MEMORY_REQUESTS_KEY: [
                {
                    "species": "SPIDER",
                    **_request(
                        layer="RELATIONAL",
                        operation="GRAPH_APPEND",
                        artifact_type="GRAPH_SNAPSHOT",
                    ),
                }
            ],
        }
    )
    assert decision["status"] == "NO_CONFIDENT_ROUTE"
    assert decision["route_mask"] == []


def test_no_memory_request_means_no_memory_authorization_bundle() -> None:
    broker = WorkerBroker()
    task = broker.enqueue(
        "MOLE",
        {"work": "ordinary derivation task without memory disclosure"},
        task_id="no-memory-access",
    )
    assert MEMORY_REQUESTS_KEY not in task["payload"]
    assert MEMORY_AUTHORIZATION_KEY not in task["payload"]



def test_sqlite_worker_broker_persists_memory_authorization_bundle(tmp_path) -> None:
    path = tmp_path / "workers.sqlite3"
    first = PersistentWorkerBroker(str(path))
    first.register_worker("spider-worker", ["SPIDER"], vector_width=4, max_batch=4)
    task = first.enqueue(
        "SPIDER",
        {
            "work": "durable graph task",
            MEMORY_REQUESTS_KEY: [
                _request(
                    layer="RELATIONAL",
                    operation="GRAPH_APPEND",
                    artifact_type="GRAPH_SNAPSHOT",
                )
            ],
        },
        task_id="durable-spider",
    )
    expected_auth = task["payload"][MEMORY_AUTHORIZATION_KEY]
    first.close()

    second = PersistentWorkerBroker(str(path))
    lease = second.claim("spider-worker", species="SPIDER", limit=1)
    second.close()

    actual_auth = lease["tasks"][0]["payload"][MEMORY_AUTHORIZATION_KEY]
    assert actual_auth == expected_auth
    assert actual_auth["task_id"] == "durable-spider"
    assert actual_auth["claims"]["all_requests_allowed"] is True



def test_fanout_rejects_forged_broker_authorization_field() -> None:
    broker = WorkerBroker()
    with pytest.raises(ValueError, match="broker-owned"):
        fanout(
            broker,
            {
                "text": "forged fanout authorization",
                MEMORY_AUTHORIZATION_KEY: {
                    "beast": "SPIDER",
                    "claims": {"all_requests_allowed": True},
                },
            },
            ["SPIDER"],
            request_id="fanout-forged-auth",
        )
    assert broker.queue_status()["tasks"]["SPIDER"]["QUEUED"] == 0


def test_broker_authorization_metadata_does_not_influence_octopus_route() -> None:
    decision = route(
        {
            "text": "plain neutral payload",
            MEMORY_AUTHORIZATION_KEY: {
                "beast": "SPIDER",
                "operation": "GRAPH_APPEND",
                "artifact_type": "GRAPH_SNAPSHOT",
            },
        }
    )
    assert decision["status"] == "NO_CONFIDENT_ROUTE"
    assert decision["route_mask"] == []



def test_worker_claim_revalidates_authorization_and_rejects_tamper() -> None:
    broker = WorkerBroker()
    broker.register_worker("spider-worker", ["SPIDER"], vector_width=4, max_batch=4)
    broker.enqueue(
        "SPIDER",
        {
            MEMORY_REQUESTS_KEY: [
                _request(
                    layer="RELATIONAL",
                    operation="GRAPH_APPEND",
                    artifact_type="GRAPH_SNAPSHOT",
                )
            ],
        },
        task_id="claim-tamper",
    )

    broker._tasks["claim-tamper"].payload[MEMORY_AUTHORIZATION_KEY]["policy_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="policy commitment"):
        broker.claim("spider-worker", species="SPIDER", limit=1)

    assert broker.queue_status()["tasks"]["SPIDER"]["QUEUED"] == 1
    assert broker.queue_status()["tasks"]["SPIDER"]["LEASED"] == 0


def test_task_authorization_bundle_rejects_token_receipt_rebinding() -> None:
    broker = WorkerBroker()
    task = broker.enqueue(
        "RAVEN",
        {
            MEMORY_REQUESTS_KEY: [
                _request(
                    layer="SEMANTIC",
                    operation="DERIVE",
                    artifact_type="MEMORY_INDEX",
                    subject_id="subject-a",
                    generation_id="gen-a",
                )
            ],
        },
        task_id="bundle-binding",
    )
    authorization = task["payload"][MEMORY_AUTHORIZATION_KEY]
    bad = {
        **authorization,
        "tokens": [dict(authorization["tokens"][0])],
        "receipts": [dict(authorization["receipts"][0])],
    }
    bad["receipts"][0]["token_id"] = "bmc:" + ("0" * 64)

    with pytest.raises(ValueError):
        validate_task_authorization_bundle(bad)
