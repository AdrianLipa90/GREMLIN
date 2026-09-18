from __future__ import annotations

import json
from pathlib import Path

from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_geometry_context_pack_v01 import (
    context_pack_prompt,
    naive_batch_prompt,
    pack_context,
)
from tools.gremlin_geometry_phase_scheduler_bench_v01 import TOPICS, _payload

OUT = Path("provenance/GREMLIN_GEOMETRY_CONTEXT_TOKEN_BENCHMARK_V0_1.json")


def _encoding():
    try:
        import tiktoken
    except ImportError as exc:
        raise RuntimeError("tiktoken is required only for the tokenizer benchmark") from exc
    return tiktoken.get_encoding("cl100k_base")


def _count(encoding, text: str) -> int:
    return len(encoding.encode(text))


def run_token_benchmark(*, items_per_topic: int = 12) -> dict[str, object]:
    if isinstance(items_per_topic, bool) or not isinstance(items_per_topic, int) or items_per_topic < 2:
        raise ValueError("items_per_topic must be an integer >= 2")

    encoding = _encoding()
    broker = WorkerBroker()
    broker.register_worker(
        "geometry-token-bench",
        ["SERPENT"],
        capabilities=["phase-state-scheduling", "context-pack"],
        vector_width=8,
        max_batch=64,
    )

    payload_by_id: dict[str, dict[str, object]] = {}
    for item_index in range(items_per_topic):
        for topic_index, (topic, center, shared) in enumerate(TOPICS):
            task_id = f"{topic}-{item_index:03d}"
            payload = _payload(topic, center, shared, topic_index, item_index)
            payload_by_id[task_id] = payload
            broker.enqueue("SERPENT", payload, task_id=task_id)

    selected_naive_tokens = 0
    selected_packed_tokens = 0
    fifo_naive_tokens = 0
    fifo_packed_tokens = 0
    task_count = 0
    batch_count = 0
    selected_byte_saving_weighted = 0.0
    fifo_byte_saving_weighted = 0.0

    while True:
        lease = broker.claim("geometry-token-bench", species="SERPENT", limit=64)
        if lease["lease_id"] is None:
            break
        scheduler = lease["scheduler"]["batch_selection"]
        selected_ids = list(scheduler["selected_task_ids"])
        fifo_ids = list(scheduler["fifo_task_ids_proxy"])
        if not selected_ids:
            raise RuntimeError("token benchmark received an empty lease")

        selected_tasks = [
            {"task_id": task_id, "payload": payload_by_id[task_id]}
            for task_id in selected_ids
        ]
        fifo_tasks = [
            {"task_id": task_id, "payload": payload_by_id[task_id]}
            for task_id in fifo_ids
        ]

        selected_pack = lease["context_pack"]
        fifo_pack = pack_context(fifo_tasks)

        selected_naive_tokens += _count(encoding, naive_batch_prompt(selected_tasks))
        selected_packed_tokens += _count(encoding, context_pack_prompt(selected_pack))
        fifo_naive_tokens += _count(encoding, naive_batch_prompt(fifo_tasks))
        fifo_packed_tokens += _count(encoding, context_pack_prompt(fifo_pack))

        n = len(selected_ids)
        task_count += n
        batch_count += 1
        selected_byte_saving_weighted += n * float(selected_pack["byte_saving_fraction"])
        fifo_byte_saving_weighted += n * float(fifo_pack["byte_saving_fraction"])

        broker.submit(
            "geometry-token-bench",
            lease["lease_id"],
            [{"task_id": task_id, "output": {"ok": True}} for task_id in selected_ids],
        )

    expected = items_per_topic * len(TOPICS)
    if task_count != expected:
        raise RuntimeError("token benchmark did not drain the full queue")

    selected_saving = (
        0.0 if selected_naive_tokens <= 0
        else 1.0 - selected_packed_tokens / selected_naive_tokens
    )
    fifo_saving = (
        0.0 if fifo_naive_tokens <= 0
        else 1.0 - fifo_packed_tokens / fifo_naive_tokens
    )
    summary = {
        "tokenizer": "tiktoken/cl100k_base",
        "task_count": task_count,
        "batch_count": batch_count,
        "selected_naive_tokens": selected_naive_tokens,
        "selected_packed_tokens": selected_packed_tokens,
        "selected_token_saving_fraction": selected_saving,
        "fifo_naive_tokens_proxy": fifo_naive_tokens,
        "fifo_packed_tokens_proxy": fifo_packed_tokens,
        "fifo_token_saving_fraction_proxy": fifo_saving,
        "geometry_pack_token_advantage_vs_fifo_proxy": selected_saving - fifo_saving,
        "selected_mean_byte_saving_fraction": selected_byte_saving_weighted / task_count,
        "fifo_mean_byte_saving_fraction_proxy": fifo_byte_saving_weighted / task_count,
        "actual_tokenizer_accounting": True,
        "actual_model_billing_accounting": False,
        "cross_tokenizer_generality_claim": False,
        "external_effects": False,
        "canon_allowed": False,
    }
    verdict = (
        "PASS_CL100K_CONTEXT_PACK_TOKEN_REDUCTION"
        if selected_packed_tokens < selected_naive_tokens
        else "FAIL_CL100K_CONTEXT_PACK_TOKEN_REDUCTION"
    )
    return {
        "schema": "GREMLIN_GEOMETRY_CONTEXT_TOKEN_BENCHMARK_V0_1",
        "fixture": {
            "species": "SERPENT",
            "topics": [row[0] for row in TOPICS],
            "items_per_topic": items_per_topic,
            "enqueue_order": "ROUND_ROBIN_TOPIC_INTERLEAVE",
            "scheduler": "GEOMETRY_PHASE_STATE_CLUSTERED_V0_1",
            "context_pack": "GREMLIN_GEOMETRY_CONTEXT_PACK_V0_1",
        },
        "summary": summary,
        "verdict": verdict,
        "claim_scope": (
            "TOKEN_REDUCTION_FOR_THIS_SYNTHETIC_FIXTURE_AND_CL100K_BASE_ONLY; "
            "NOT A BILLING OR UNIVERSAL MODEL TOKEN CLAIM"
        ),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def main() -> int:
    receipt = run_token_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"verdict={receipt['verdict']}")
    print(f"claim_scope={receipt['claim_scope']}")
    print(f"receipt={OUT}")
    return 0 if receipt["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
