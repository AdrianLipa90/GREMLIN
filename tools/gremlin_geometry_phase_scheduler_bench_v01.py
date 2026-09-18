from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re

from gremlin_mcp.workers import WorkerBroker
from tools.gremlin_bestiary_phasenav_phase_gates_v01 import TAU
from tools.gremlin_geometry_context_pack_v01 import pack_context
from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY

OUT = Path("provenance/GREMLIN_GEOMETRY_PHASE_SCHEDULER_BENCHMARK_V0_1.json")
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:+-]+")


def _phase(center: float, topic_index: int, item_index: int) -> list[float]:
    return [
        (
            center
            + 0.018 * math.sin((axis + 1) * (item_index + 1) / 13.0)
            + 0.006 * math.cos((axis + 3) * (topic_index + 1) / 7.0)
        )
        % TAU
        for axis in range(36)
    ]


TOPICS = (
    (
        "geometry",
        0.35,
        "phase geometry torus relation isomorphism manifold winding topology state",
    ),
    (
        "memory",
        1.30,
        "memory recall similarity provenance lineage semantic archive relation state",
    ),
    (
        "anomaly",
        2.25,
        "anomaly contradiction residual drift falsification evidence test target state",
    ),
    (
        "planning",
        3.20,
        "planning decomposition dependency experiment information gain cost risk state",
    ),
    (
        "signal",
        4.15,
        "signal harmonic phase resonance coherence frequency weak pattern state",
    ),
    (
        "construction",
        5.10,
        "construction prototype artifact fixture verification build relation state",
    ),
)


def _payload(topic: str, center: float, shared: str, topic_index: int, item_index: int) -> dict[str, object]:
    return {
        "topic": topic,
        "text": (
            f"{shared} {shared} "
            f"candidate_{topic}_{item_index} evidence receipt bounded worker"
        ),
        "index": item_index,
        SCHEDULER_KEY: {
            "phase36": _phase(center, topic_index, item_index),
            "ready": True,
            "readiness": 1.0,
            "temperature": 0.25 + 0.10 * topic_index,
            "urgency": 0.0,
            "noise": 0.05 + 0.01 * (item_index % 3),
        },
    }


def _tokens(payload: dict[str, object]) -> set[str]:
    text = json.dumps(
        {k: v for k, v in payload.items() if k != SCHEDULER_KEY},
        sort_keys=True,
        ensure_ascii=False,
    ).casefold()
    return set(TOKEN_RE.findall(text))


def _pairwise_jaccard(ids: list[str], tokens_by_id: dict[str, set[str]]) -> float:
    if len(ids) < 2:
        return 1.0
    total = 0.0
    n = 0
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a = tokens_by_id[ids[i]]
            b = tokens_by_id[ids[j]]
            union = a | b
            total += 1.0 if not union else len(a & b) / len(union)
            n += 1
    return total / n


def _topic_purity(ids: list[str], topic_by_id: dict[str, str]) -> float:
    if not ids:
        return 0.0
    counts = Counter(topic_by_id[task_id] for task_id in ids)
    return max(counts.values()) / len(ids)


def run_benchmark(*, items_per_topic: int = 24) -> dict[str, object]:
    broker = WorkerBroker()
    broker.register_worker(
        "geometry-bench",
        ["SERPENT"],
        capabilities=["phase-state-scheduling"],
        vector_width=8,
        max_batch=64,
    )

    topic_by_id: dict[str, str] = {}
    tokens_by_id: dict[str, set[str]] = {}
    payload_by_id: dict[str, dict[str, object]] = {}

    # Round-robin enqueue deliberately makes FIFO context alternate across topics.
    for item_index in range(items_per_topic):
        for topic_index, (topic, center, shared) in enumerate(TOPICS):
            task_id = f"{topic}-{item_index:03d}"
            payload = _payload(topic, center, shared, topic_index, item_index)
            broker.enqueue("SERPENT", payload, task_id=task_id)
            topic_by_id[task_id] = topic
            tokens_by_id[task_id] = _tokens(payload)
            payload_by_id[task_id] = payload

    selected_transition = 0.0
    fifo_transition = 0.0
    selected_noise_weighted = 0.0
    fifo_noise_weighted = 0.0
    selected_overlap_weighted = 0.0
    fifo_overlap_weighted = 0.0
    selected_purity_weighted = 0.0
    fifo_purity_weighted = 0.0
    task_weight = 0
    batch_sizes: list[int] = []
    selected_raw_context_bytes = 0
    selected_packed_context_bytes = 0
    fifo_raw_context_bytes = 0
    fifo_packed_context_bytes = 0

    while True:
        lease = broker.claim("geometry-bench", species="SERPENT", limit=64)
        if lease["lease_id"] is None:
            break
        sched = lease["scheduler"]["batch_selection"]
        selected_ids = list(sched["selected_task_ids"])
        fifo_ids = list(sched["fifo_task_ids_proxy"])
        n = len(selected_ids)
        if n <= 0:
            raise RuntimeError("scheduler emitted empty leased batch")
        batch_sizes.append(n)
        task_weight += n

        selected_transition += float(sched["transition_cost_selected"])
        fifo_transition += float(sched["transition_cost_fifo_proxy"])
        selected_noise_weighted += n * float(sched["noise_cost_selected"])
        fifo_noise_weighted += n * float(sched["noise_cost_fifo_proxy"])
        selected_overlap_weighted += n * _pairwise_jaccard(selected_ids, tokens_by_id)
        fifo_overlap_weighted += n * _pairwise_jaccard(fifo_ids, tokens_by_id)
        selected_purity_weighted += n * _topic_purity(selected_ids, topic_by_id)
        fifo_purity_weighted += n * _topic_purity(fifo_ids, topic_by_id)

        selected_pack = lease["context_pack"]
        fifo_pack = pack_context([
            {"task_id": task_id, "payload": payload_by_id[task_id]}
            for task_id in fifo_ids
        ])
        selected_raw_context_bytes += int(selected_pack["raw_semantic_bytes"])
        selected_packed_context_bytes += int(selected_pack["packed_context_bytes"])
        fifo_raw_context_bytes += int(fifo_pack["raw_semantic_bytes"])
        fifo_packed_context_bytes += int(fifo_pack["packed_context_bytes"])

        broker.submit(
            "geometry-bench",
            lease["lease_id"],
            [{"task_id": task_id, "output": {"ok": True}} for task_id in selected_ids],
        )

    if task_weight != items_per_topic * len(TOPICS):
        raise RuntimeError("benchmark did not drain the full synthetic queue")

    selected_noise = selected_noise_weighted / task_weight
    fifo_noise = fifo_noise_weighted / task_weight
    selected_overlap = selected_overlap_weighted / task_weight
    fifo_overlap = fifo_overlap_weighted / task_weight
    selected_purity = selected_purity_weighted / task_weight
    fifo_purity = fifo_purity_weighted / task_weight

    summary = {
        "task_count": task_weight,
        "batch_count": len(batch_sizes),
        "mean_batch_size": sum(batch_sizes) / len(batch_sizes),
        "max_batch_size": max(batch_sizes),
        "selected_transition_cost": selected_transition,
        "fifo_transition_cost_proxy": fifo_transition,
        "transition_reduction_vs_fifo_proxy": (
            0.0 if fifo_transition <= 1e-15 else 1.0 - selected_transition / fifo_transition
        ),
        "selected_noise_cost": selected_noise,
        "fifo_noise_cost_proxy": fifo_noise,
        "noise_reduction_vs_fifo_proxy": (
            0.0 if fifo_noise <= 1e-15 else 1.0 - selected_noise / fifo_noise
        ),
        "selected_lexical_overlap": selected_overlap,
        "fifo_lexical_overlap_proxy": fifo_overlap,
        "lexical_overlap_gain": selected_overlap - fifo_overlap,
        "selected_topic_purity": selected_purity,
        "fifo_topic_purity_proxy": fifo_purity,
        "topic_purity_gain": selected_purity - fifo_purity,
        "selected_raw_context_bytes": selected_raw_context_bytes,
        "selected_packed_context_bytes": selected_packed_context_bytes,
        "selected_context_byte_saving_fraction": (
            0.0 if selected_raw_context_bytes <= 0
            else 1.0 - selected_packed_context_bytes / selected_raw_context_bytes
        ),
        "fifo_raw_context_bytes_proxy": fifo_raw_context_bytes,
        "fifo_packed_context_bytes_proxy": fifo_packed_context_bytes,
        "fifo_context_byte_saving_fraction_proxy": (
            0.0 if fifo_raw_context_bytes <= 0
            else 1.0 - fifo_packed_context_bytes / fifo_raw_context_bytes
        ),
        "context_pack_advantage_vs_fifo_proxy": (
            (0.0 if selected_raw_context_bytes <= 0 else 1.0 - selected_packed_context_bytes / selected_raw_context_bytes)
            - (0.0 if fifo_raw_context_bytes <= 0 else 1.0 - fifo_packed_context_bytes / fifo_raw_context_bytes)
        ),
        "actual_model_token_accounting": False,
        "token_saving_claim": False,
        "external_effects": False,
        "canon_allowed": False,
    }

    return {
        "schema": "GREMLIN_GEOMETRY_PHASE_SCHEDULER_BENCHMARK_V0_1",
        "fixture": {
            "species": "SERPENT",
            "topics": [row[0] for row in TOPICS],
            "items_per_topic": items_per_topic,
            "enqueue_order": "ROUND_ROBIN_TOPIC_INTERLEAVE",
            "phase_dimension": 36,
            "explicit_phase": True,
        },
        "summary": summary,
        "verdict": (
            "PASS_SYNTHETIC_GEOMETRY_SCHEDULING"
            if summary["transition_reduction_vs_fifo_proxy"] > 0.20
            and summary["lexical_overlap_gain"] > 0.05
            and summary["topic_purity_gain"] > 0.20
            else "FAIL_SYNTHETIC_GEOMETRY_SCHEDULING"
        ),
        "authority": {
            "production_runtime_write": False,
            "execution_admitted": False,
            "canon_allowed": False,
        },
    }


def main() -> int:
    receipt = run_benchmark()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt["summary"], sort_keys=True))
    print(f"verdict={receipt['verdict']}")
    print(f"receipt={OUT}")
    return 0 if receipt["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
