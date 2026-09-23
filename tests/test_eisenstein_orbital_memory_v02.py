import itertools
import math
import random
import unittest

from gremlin_mcp.eisenstein_orbital_memory import (
    DEFAULT_SPLIT_PRIMES,
    EISENSTEIN_UNITS,
    EisensteinMemoryError,
    EisensteinOrbitalIndex,
    RecursiveEisensteinAddress,
    centered_hex_count,
    centered_hex_eisenstein,
    packet_orbital_word,
    prefix_neighborhood,
    prime_channel_signature,
    split_prime_roots,
)


def packet_for_word(word, *, jitter=0.0, seed=0):
    rng = random.Random(seed)
    phase = [0.0] * 36
    amp = [0.0] * 36
    for row, direction in enumerate(word[:6]):
        base_phase = (
            direction * math.pi / 3.0
            - row * math.pi / 3.0
        )
        for col in range(6):
            i = row * 6 + col
            phase[i] = (
                base_phase
                + rng.uniform(-jitter, jitter)
            )
            amp[i] = 1.0
    return {
        "phase36": phase,
        "amplitude36": amp,
        "semantic_commitment": (
            "route:"
            + "".join(str(int(x) % 6) for x in word)
            + f":{seed}"
        ),
    }


class EisensteinMemoryV02Tests(unittest.TestCase):
    def test_six_units_have_norm_one(self):
        self.assertEqual(len(EISENSTEIN_UNITS), 6)
        self.assertEqual(
            {u.norm for u in EISENSTEIN_UNITS},
            {1},
        )
        self.assertEqual(
            {u.hex_radius for u in EISENSTEIN_UNITS},
            {1},
        )

    def test_centered_hex_is_exact_eisenstein_norm(self):
        for n in range(101):
            z = centered_hex_eisenstein(n)
            self.assertEqual(
                z.norm,
                centered_hex_count(n),
            )
            self.assertEqual(
                z.norm,
                3 * n * n + 3 * n + 1,
            )

    def test_split_prime_channel_has_two_radial_roots(self):
        for q in DEFAULT_SPLIT_PRIMES:
            roots = split_prime_roots(q)
            self.assertEqual(len(roots), 2)
            self.assertEqual(
                (roots[0] + roots[1]) % q,
                (-1) % q,
            )
            for n in roots:
                self.assertEqual(
                    centered_hex_count(n) % q,
                    0,
                )

    def test_non_split_prime_rejected(self):
        for q in (2, 3, 5, 11, 17, 23):
            with self.assertRaises(EisensteinMemoryError):
                split_prime_roots(q)

    def test_recursive_address_is_injective_at_depth_four(self):
        seen = set()
        for word in itertools.product(range(6), repeat=4):
            address = RecursiveEisensteinAddress.from_word(
                word,
                base=4,
            )
            key = (
                address.code.a,
                address.code.b,
            )
            self.assertNotIn(key, seen)
            seen.add(key)
        self.assertEqual(len(seen), 6 ** 4)

    def test_base_below_four_fails_closed(self):
        for base in (0, 1, 2, 3):
            with self.assertRaises(EisensteinMemoryError):
                RecursiveEisensteinAddress.root(
                    base=base
                )

    def test_root_is_zero_and_finite_paths_stay_in_disk(self):
        root = RecursiveEisensteinAddress.root(base=4)
        self.assertEqual(root.poincare_point(), 0j)
        self.assertEqual(root.poincare_radius, 0.0)

        previous = 0.0
        for depth in range(1, 10):
            address = RecursiveEisensteinAddress.from_word(
                [0] * depth,
                base=4,
            )
            expected = 1.0 - (4.0 ** (-depth))
            self.assertAlmostEqual(
                address.poincare_radius,
                expected,
                places=12,
            )
            self.assertLess(
                address.poincare_radius,
                1.0,
            )
            self.assertGreater(
                address.poincare_radius,
                previous,
            )
            previous = address.poincare_radius

    def test_packet_word_reads_six_oriented_projection_rows(self):
        packet = packet_for_word(
            (0, 1, 2, 3, 4, 5)
        )
        self.assertEqual(
            packet_orbital_word(packet),
            (0, 1, 2, 3, 4, 5),
        )

    def test_prefix_neighborhood_is_local_on_hex_cycle(self):
        self.assertEqual(
            set(
                prefix_neighborhood(
                    (2, 4, 0),
                    last_digit_tolerance=1,
                )
            ),
            {
                (2, 4, 5),
                (2, 4, 0),
                (2, 4, 1),
            },
        )

    def test_recursive_prefix_pruning(self):
        index = EisensteinOrbitalIndex(
            hex_scale=8.0,
            base=4,
            split_primes=(7, 13, 19),
        )
        packets = {}
        per_prefix = 12
        for a in range(6):
            for b in range(6):
                for c in range(6):
                    prefix = (a, b, c)
                    for j in range(per_prefix):
                        tail = (
                            j % 6,
                            (j // 2) % 6,
                            (j // 3) % 6,
                        )
                        word = prefix + tail
                        mid = (
                            f"{a}{b}{c}-"
                            f"{j:02d}"
                        )
                        packet = packet_for_word(
                            word,
                            jitter=0.004,
                            seed=(
                                a * 10000
                                + b * 1000
                                + c * 100
                                + j
                            ),
                        )
                        packets[mid] = packet
                        index.add(
                            memory_id=mid,
                            ledger_record_id=(
                                "hive:" + mid
                            ),
                            packet=packet,
                            semantic_orbit_id="test",
                        )

        target = "234-05"
        route = index.shortlist(
            packets[target],
            prefix_depth=3,
            last_digit_tolerance=0,
            min_candidates=8,
            semantic_orbit_ids=["test"],
        )
        self.assertIn(
            target,
            route["candidate_ids"],
        )
        self.assertEqual(
            route["prefix_depth_used"],
            3,
        )
        self.assertEqual(
            len(route["candidate_ids"]),
            per_prefix,
        )
        self.assertLess(
            route["evaluated_fraction"],
            0.01,
        )

    def test_priority_orbit_never_becomes_semantic_orbit(self):
        index = EisensteinOrbitalIndex(
            split_primes=(7,)
        )
        packet = packet_for_word(
            (0, 1, 2, 3, 4, 5)
        )
        index.add(
            memory_id="inner",
            ledger_record_id="hive:inner",
            packet=packet,
            priority_orbit_index=0,
            semantic_orbit_id="same",
        )
        index.add(
            memory_id="outer",
            ledger_record_id="hive:outer",
            packet={
                **packet,
                "semantic_commitment": "outer",
            },
            priority_orbit_index=35,
            semantic_orbit_id="same",
        )
        route = index.shortlist(
            packet,
            prefix_depth=2,
            min_candidates=1,
            semantic_orbit_ids=["same"],
        )
        self.assertEqual(
            set(route["candidate_ids"]),
            {"inner", "outer"},
        )

    def test_prime_filter_has_fail_open_candidate_fallback(self):
        index = EisensteinOrbitalIndex(
            split_primes=(7, 13)
        )
        query = packet_for_word((0,))
        index.add(
            memory_id="a",
            ledger_record_id="hive:a",
            packet=query,
            route_word=(0,),
        )
        out = index.shortlist(
            query,
            prefix_depth=1,
            min_candidates=1,
            prime_mode="filter",
            prime_radius="trajectory",
        )
        self.assertIn("a", out["candidate_ids"])
        self.assertIn(
            7,
            prime_channel_signature(
                1,
                primes=(7, 13),
            ),
        )

    def test_authority_remains_derived_only(self):
        index = EisensteinOrbitalIndex(
            split_primes=(7,)
        )
        packet = packet_for_word(
            (0, 1, 2, 3, 4, 5)
        )
        index.add(
            memory_id="m",
            ledger_record_id="hive:m",
            packet=packet,
        )
        out = index.shortlist(
            packet,
            prefix_depth=2,
            min_candidates=1,
        )
        self.assertFalse(
            out["authority"]["source_of_truth"]
        )
        self.assertFalse(
            out["authority"]["ledger_mutation"]
        )
        self.assertFalse(
            out["authority"]["canon_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
