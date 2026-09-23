import math
import random
import unittest

from gremlin_mcp.relational_memory_encoder import encode_memory_text, retrieve_memory
from gremlin_mcp.orbital_hive_memory import OrbitalHiveMemory
from gremlin_mcp.holo_memory_hive_bridge import HoloMemoryBridgeError, materialize_orbital_hive
from gremlin_mcp.holo_memory_noema_bridge import (
    NoemaTraceBridgeError,
    materialize_noema_traces,
    packet_from_noema_trace,
)

from gremlin_mcp.holo_memory import (
    HoloMemoryError,
    HoloMemoryIndex,
    hex_neighborhood,
    moire_cross_term,
    remap_hive_record,
    settle_hex_patch,
    weighted_phase_coherence,
)


def packet(row, *, phase=0.0, jitter=0.0, seed=0, sem=None):
    rng = random.Random(seed)
    phases = []
    amps = []
    for r in range(6):
        for _ in range(6):
            phases.append(
                phase
                + (
                    rng.uniform(-jitter, jitter)
                    if r == row
                    else 0.0
                )
            )
            amps.append(1.0 if r == row else 0.0)
    return {
        "phase36": phases,
        "amplitude36": amps,
        "semantic_commitment": sem or f"s:{row}:{seed}",
    }


class HoloMemoryTests(unittest.TestCase):
    def test_hex_neighborhood_cardinality(self):
        for r in range(5):
            self.assertEqual(
                len(hex_neighborhood((0, 0), r)),
                1 + 3 * r * (r + 1),
            )

    def test_identical_and_antiphase_moire(self):
        a = packet(0, phase=0.0)
        b = packet(0, phase=0.0)
        c = packet(0, phase=math.pi)
        self.assertAlmostEqual(
            moire_cross_term(a, b), 1.0, places=12
        )
        self.assertAlmostEqual(
            moire_cross_term(a, c), -1.0, places=12
        )
        self.assertAlmostEqual(
            weighted_phase_coherence(a, b), 1.0, places=12
        )
        self.assertAlmostEqual(
            weighted_phase_coherence(a, c), 1.0, places=12
        )

    def test_rebuild_is_deterministic(self):
        rows = [
            {
                "memory_id": f"m{i}",
                "ledger_record_id": f"hive:{i}",
                "packet": packet(i % 6, seed=i),
                "orbit_index": i % 3,
                "priority": 0.5,
            }
            for i in range(20)
        ]
        idx = HoloMemoryIndex()
        a = idx.rebuild(rows)
        snap1 = idx.snapshot_commitment()
        b = idx.rebuild(rows)
        snap2 = idx.snapshot_commitment()
        self.assertEqual(a, b)
        self.assertEqual(snap1, snap2)
        self.assertEqual(idx.count, 20)

    def test_duplicate_fails_closed(self):
        idx = HoloMemoryIndex()
        p = packet(0)
        idx.add(
            memory_id="m",
            ledger_record_id="hive:1",
            packet=p,
        )
        with self.assertRaises(HoloMemoryError):
            idx.add(
                memory_id="m",
                ledger_record_id="hive:2",
                packet=p,
            )

    def test_hive_remap_is_non_mutating_and_preserves_lineage(self):
        rec = {
            "record_id": "hive:abc",
            "subject_id": "subject-a",
            "priority": 0.8,
            "coordinate": {"orbit_index": 7},
        }
        original = dict(rec)
        row = remap_hive_record(rec, packet(2, seed=9))
        self.assertEqual(rec, original)
        self.assertEqual(row["ledger_record_id"], "hive:abc")
        self.assertEqual(row["memory_id"], "subject-a")
        self.assertEqual(row["orbit_index"], 7)

    def test_patch_moire_is_candidate_only(self):
        idx = HoloMemoryIndex()
        idx.add(
            memory_id="a",
            ledger_record_id="hive:a",
            packet=packet(0),
        )
        idx.add(
            memory_id="b",
            ledger_record_id="hive:b",
            packet=packet(0, phase=0.2),
        )
        out = idx.patch_moire(["a", "b"])
        self.assertEqual(out["status"], "CANDIDATE_ONLY")
        self.assertFalse(out["ledger_mutation"])
        self.assertFalse(out["authority"]["canon_allowed"])

    def test_hex_shortlist_recall_and_cost(self):
        idx = HoloMemoryIndex(hex_scale=12.0)
        packets = {}
        for row in range(6):
            for j in range(80):
                mid = f"r{row}-{j:03d}"
                p = packet(
                    row,
                    phase=0.25 * row,
                    jitter=0.012,
                    seed=1000 * row + j,
                    sem=mid,
                )
                packets[mid] = p
                idx.add(
                    memory_id=mid,
                    ledger_record_id="hive:" + mid,
                    packet=p,
                    orbit_index=row,
                    priority=0.5,
                )
        target = "r3-017"
        cue = packets[target]
        full = []
        for mid, p in packets.items():
            score = (
                0.75 * weighted_phase_coherence(cue, p)
                + 0.25 * ((moire_cross_term(cue, p) + 1) / 2)
            )
            full.append((score, mid))
        full.sort(key=lambda x: (-x[0], x[1]))
        out = idx.retrieve(
            cue,
            patch_radius=0,
            fallback_full=False,
        )
        self.assertEqual(full[0][1], target)
        self.assertEqual(out["picked"], target)
        self.assertLess(out["fraction_evaluated"], 0.30)
        self.assertGreater(out["evaluated"], 0)

    def test_orbital_pruning_compounds_hex_pruning(self):
        idx = HoloMemoryIndex(hex_scale=12.0)
        packets = {}
        for orbit in range(12):
            for row in range(6):
                for j in range(12):
                    mid = f"o{orbit}-r{row}-{j}"
                    p = packet(
                        row,
                        phase=0.2 * row + 0.003 * orbit,
                        jitter=0.008,
                        seed=orbit * 1000 + row * 100 + j,
                        sem=mid,
                    )
                    packets[mid] = p
                    idx.add(
                        memory_id=mid,
                        ledger_record_id="hive:" + mid,
                        packet=p,
                        orbit_index=orbit,
                    )
        target = "o7-r4-5"
        out = idx.retrieve(
            packets[target],
            patch_radius=0,
            orbit_radius=0,
            orbit_index=7,
            fallback_full=False,
        )
        self.assertEqual(out["picked"], target)
        self.assertLessEqual(out["evaluated"], 12)
        self.assertLess(out["fraction_evaluated"], 0.02)

    def test_kuramoto_hex_settle_increases_coherence(self):
        coords = (
            (0, 0),
            (1, 0),
            (1, -1),
            (0, -1),
            (-1, 0),
            (-1, 1),
            (0, 1),
        )
        phases = (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4)
        out = settle_hex_patch(
            phases,
            coords,
            coupling=1.0,
            dt=0.04,
            steps=120,
        )
        self.assertGreater(out["after"], out["before"])
        self.assertEqual(out["edge_count"], 12)


    def test_existing_18_paraphrases_survive_holo_remap(self):
        memories = {
            "stella": "stella octangula: two shared poles and six lateral vertices",
            "projections": "six projections share the poles and expose six lateral channels each",
            "36d": "36 = 6 projections x 6 relational channels",
            "moire": "six projections may have distinct frequencies and slight relative rotations",
            "elephant": "ELEPHANT consolidates relational memory, replay and retention",
            "bees": "BEES checks overlap coherence, anti-entropy delta and reconciliation proposals",
        }
        cues = {
            "stella": [
                "compound tetrahedral geometry with a common antipodal pole pair and six side points",
                "two opposite poles organize six remaining vertices of the interpenetrating tetrahedra",
                "dwa wspólne bieguny i sześć bocznych wierzchołków stella octangula",
            ],
            "projections": [
                "six views use the same two poles, each carrying six side channels",
                "each of the six slices keeps one common axis and carries six lateral degrees",
                "sześć rzutów ma te same bieguny, każdy ma sześć bocznych kanałów",
            ],
            "36d": [
                "thirty six dimensions factor into six views with six relation channels per view",
                "state factorizes into 6 by 6 relation coordinates",
                "trzydzieści sześć wymiarów to sześć rzutów po sześć kanałów relacji",
            ],
            "moire": [
                "slightly twisted layers oscillating at different rates create the interference pattern",
                "small angular offsets plus unequal carrier rates produce a beat pattern",
                "lekko obrócone warstwy z różnymi częstotliwościami tworzą interferencję moire",
            ],
            "elephant": [
                "long-term memory is strengthened through consolidation, replay and retention planning",
                "rehearsal and retention deepen the memory trace",
                "słoń odpowiada za konsolidację pamięci, replay i retencję",
            ],
            "bees": [
                "distributed fragments are compared for overlap consistency and proposed anti-entropy reconciliation",
                "replicas are checked for consistency and an anti entropy repair is only proposed",
                "pszczoły sprawdzają spójność nakładających się śladów i proponują rekoncyliację",
            ],
        }
        idx = HoloMemoryIndex(hex_scale=2.0)
        for memory_id, text in memories.items():
            idx.add(
                memory_id=memory_id,
                ledger_record_id="hive:" + memory_id,
                packet=encode_memory_text(text),
            )

        passed = 0
        for expected, variants in cues.items():
            for cue_text in variants:
                baseline = retrieve_memory(cue_text, memories)
                self.assertEqual(baseline["picked"], expected)
                out = idx.retrieve_reference(
                    encode_memory_text(cue_text),
                    patch_radius=2,
                    fallback_full=False,
                )
                self.assertEqual(
                    out["picked"],
                    expected,
                    msg=(expected, cue_text, out),
                )
                passed += 1
        self.assertEqual(passed, 18)


    def test_orbital_hive_bridge_materializes_without_mutation(self):
        hive = OrbitalHiveMemory()
        inputs = {
            "stella": "stella octangula: two shared poles and six lateral vertices",
            "moire": "six projections may have distinct frequencies and slight relative rotations",
            "bees": "BEES checks overlap coherence, anti-entropy delta and reconciliation proposals",
        }
        for i, (subject, text) in enumerate(inputs.items()):
            hive.place(
                subject_id=subject,
                payload={"text": text},
                priority=0.9 - 0.1 * i,
                semantic_key=subject,
                relation_phase=0.1 * i,
            )
        before = [record.record_id for record in hive.flat_ring_table()]
        index, receipt = materialize_orbital_hive(
            hive,
            hex_scale=2.0,
            strict=True,
        )
        after = [record.record_id for record in hive.flat_ring_table()]
        self.assertEqual(before, after)
        self.assertEqual(index.count, 3)
        self.assertEqual(receipt["mapped_count"], 3)
        self.assertEqual(receipt["skipped_count"], 0)
        self.assertFalse(receipt["ledger_mutation"])
        self.assertFalse(receipt["canon_allowed"])

    def test_orbital_hive_bridge_fails_closed_on_opaque_payload(self):
        hive = OrbitalHiveMemory()
        hive.place(
            subject_id="opaque",
            payload={"opaque": {"no": "phase-or-text"}},
            priority=0.5,
            semantic_key="opaque",
            relation_phase=0.0,
        )
        with self.assertRaises(HoloMemoryBridgeError):
            materialize_orbital_hive(hive, strict=True)


    def test_noema_trace_bridge_derives_phase_from_semantic_body_not_hash(self):
        trace = {
            "schema": "NOEMA_MEMORY_TRACE_V1",
            "trace_id": "V18:M3:CURRENT_HALF:EXPANDED_V1",
            "layer": "M3",
            "content": {
                "binding_semantics": {
                    "control": "semantic command class and learned constraints",
                    "cognition": "concept claim semantics and hypothesis identities",
                },
                "source_fragments": {
                    "theory_hotset": [
                        "CP1 Bloch Euler tetrahedra Poincare holonomy 36D crystal",
                        "ethics relational scalar",
                    ]
                },
            },
            "semantic_tags": ["m0-m11", "m3"],
            "phase_binding": {
                "status": "UNAVAILABLE",
                "vector": None,
            },
            "epistemic_state": "RECONSTRUCTED_FROM_VERIFIED_CANONICAL_SOURCES",
            "trace_sha256": "a" * 64,
        }
        packet, provenance = packet_from_noema_trace(trace)
        self.assertEqual(len(packet["phase36"]), 36)
        self.assertEqual(len(packet["amplitude36"]), 36)
        self.assertEqual(
            provenance["native_phase_binding_status"],
            "UNAVAILABLE",
        )
        self.assertFalse(provenance["exact_legacy_phase_recovered"])
        self.assertFalse(provenance["hash_used_as_semantic_coordinate"])
        self.assertTrue(
            provenance["phase_source"].startswith(
                "DERIVED_FROM_RECEIPTED_TRACE_TEXT/"
            )
        )

    def test_noema_trace_bridge_does_not_conflate_layer_with_orbit(self):
        traces = []
        for layer in ("M1", "M3"):
            traces.append(
                {
                    "schema": "NOEMA_MEMORY_TRACE_V1",
                    "trace_id": f"V18:{layer}:CURRENT_HALF:EXPANDED_V1",
                    "layer": layer,
                    "content": {
                        "binding_semantics": {
                            "control": f"{layer} control semantics",
                            "cognition": f"{layer} cognition semantics",
                        },
                        "source_fragments": {
                            "memory": ["memory", "relational context"]
                        },
                    },
                    "semantic_tags": ["m0-m11", layer.lower()],
                    "phase_binding": {
                        "status": "UNAVAILABLE",
                        "vector": None,
                    },
                    "epistemic_state": "RECONSTRUCTED",
                    "trace_sha256": (
                        "1" * 64 if layer == "M1" else "3" * 64
                    ),
                }
            )
        index, receipt = materialize_noema_traces(
            traces,
            hex_scale=2.0,
        )
        self.assertEqual(index.count, 2)
        self.assertFalse(receipt["orbit_map_bound"])
        self.assertTrue(
            all(
                origin["orbit_source"] == "UNBOUND_DEFAULT_ZERO"
                for origin in receipt["origins"]
            )
        )
        self.assertFalse(receipt["hash_used_as_semantic_coordinate"])
        self.assertFalse(receipt["ledger_mutation"])
        self.assertFalse(receipt["canon_allowed"])

    def test_noema_trace_bridge_requires_complete_explicit_orbit_map(self):
        trace = {
            "schema": "NOEMA_MEMORY_TRACE_V1",
            "trace_id": "V18:M1:CURRENT_HALF:EXPANDED_V1",
            "layer": "M1",
            "content": {
                "binding_semantics": {
                    "control": "active gate working set",
                    "cognition": "active thought state",
                },
                "source_fragments": {"memory": ["memory context"]},
            },
            "semantic_tags": ["m1"],
            "phase_binding": {"status": "UNAVAILABLE"},
            "epistemic_state": "RECONSTRUCTED",
            "trace_sha256": "1" * 64,
        }
        with self.assertRaises(NoemaTraceBridgeError):
            materialize_noema_traces(
                [trace],
                orbit_map={},
            )


if __name__ == "__main__":
    unittest.main()
