from tools.gremlin_geometry_context_pack_v01 import (
    context_pack_prompt,
    naive_batch_prompt,
    pack_context,
    unpack_context,
)
from tools.gremlin_geometry_phase_scheduler_v01 import SCHEDULER_KEY


def _task(task_id: str, topic: str, index: int) -> dict:
    return {
        "task_id": task_id,
        "payload": {
            "topic": topic,
            "text": (
                "phase geometry resonance memory relation audit "
                f"candidate_{topic}_{index} "
                "evidence receipt bounded worker"
            ),
            "index": index,
            SCHEDULER_KEY: {
                "phase36": [0.1 + 0.001 * index] * 36,
                "noise": 0.05,
            },
        },
    }


def _semantic_core(task: dict) -> dict:
    return {k: v for k, v in task["payload"].items() if k != SCHEDULER_KEY}


def test_context_pack_roundtrips_semantic_payload_core_losslessly():
    tasks = [_task(f"t-{i}", "geometry", i) for i in range(4)]
    pack = pack_context(tasks)
    restored = unpack_context(pack)
    assert restored == {task["task_id"]: _semantic_core(task) for task in tasks}
    assert pack["lossless_semantic_payload_core"] is True
    assert pack["scheduler_metadata_included"] is False
    assert pack["actual_model_token_accounting"] is False
    assert pack["token_saving_claim"] is False


def test_context_pack_factors_shared_fields_and_string_context():
    tasks = [_task(f"t-{i}", "geometry", i) for i in range(5)]
    pack = pack_context(tasks)
    assert pack["shared_values"]["topic"] == "geometry"
    assert "text" in pack["string_factors"]
    assert len(pack["string_factors"]["text"]["prefix"]) > 20
    assert pack["packed_context_bytes"] < pack["raw_semantic_bytes"]


def test_context_pack_prompt_is_smaller_than_naive_prompt_on_coherent_fixture():
    tasks = [_task(f"t-{i}", "geometry", i) for i in range(12)]
    pack = pack_context(tasks)
    packed = context_pack_prompt(pack)
    naive = naive_batch_prompt(tasks)
    assert len(packed.encode("utf-8")) < len(naive.encode("utf-8"))


def test_scheduler_metadata_does_not_enter_model_context_pack():
    tasks = [_task("a", "geometry", 0), _task("b", "geometry", 1)]
    pack = pack_context(tasks)
    rendered = context_pack_prompt(pack)
    assert SCHEDULER_KEY not in rendered
