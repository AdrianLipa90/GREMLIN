import math
import random
import unittest

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


if __name__ == "__main__":
    unittest.main()
