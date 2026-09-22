from __future__ import annotations

from gremlin_mcp.hive_authority import HiveAuthorityRuntime


def test_hive_genetic_snapshot_round_trips_exact_head_without_mutation(tmp_path) -> None:
    runtime = HiveAuthorityRuntime(tmp_path / "hive.sqlite3")
    try:
        head = runtime.place(
            subject_id="genetic-memory-fixture",
            payload={"kind": "MEMORY_INDEX", "facts": ["a", "b"], "confidence": 0.75},
            priority=0.82,
            semantic_key="memory/genetic-fixture",
            relation_phase=0.375,
            provenance=("fixture:source",),
            dependencies=("fixture:dependency",),
        )
        before = runtime.persisted()
        packet = runtime.genetic_snapshot(head.subject_id)
        restored = runtime.genetic_restore_preview(packet)
        after = runtime.persisted()

        assert restored == before[-1]
        assert packet["source_id"] == head.record_id
        assert packet["parent_id"] == head.parent_record_id
        assert before == after
    finally:
        runtime.close()


def test_hive_hypercrystal_expression_is_read_only_and_genome_bound(tmp_path) -> None:
    runtime = HiveAuthorityRuntime(tmp_path / "hive.sqlite3")
    try:
        head = runtime.place(
            subject_id="genetic-expression-fixture",
            payload={"kind": "RELATION_EDGE", "left": "x", "right": "y"},
            priority=0.91,
            semantic_key="memory/expression-fixture",
            relation_phase=1.25,
            provenance=("fixture:expression",),
        )
        packet = runtime.genetic_snapshot(head.subject_id)
        before = runtime.persisted()
        expression = runtime.genetic_expression(
            head.subject_id,
            [index / 13.0 for index in range(36)],
            top_k=12,
            phase_source="TEST_HYPERCRYSTAL_36D",
        )
        after = runtime.persisted()

        assert expression["genome_id"] == packet["genome_id"]
        assert expression["phase_dim"] == 36
        assert expression["memory_mutation_allowed"] is False
        assert expression["canon_allowed"] is False
        assert expression["phase_source"] == "TEST_HYPERCRYSTAL_36D"
        assert before == after
    finally:
        runtime.close()
