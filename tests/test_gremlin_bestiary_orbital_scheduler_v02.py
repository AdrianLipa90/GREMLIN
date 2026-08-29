from __future__ import annotations

import math
import unittest

from tools.gremlin_bestiary_orbital_scheduler_v02 import (
    OMEGA0,
    PROFILES,
    bounded_batch_size,
    cadence_rank,
    ideal_scalar_ceiling,
    service_omega,
    service_period,
)


class BestiaryOrbitalSchedulerTests(unittest.TestCase):
    def test_hummingbird_is_faster_than_belzebub(self):
        self.assertGreater(
            service_omega(PROFILES["HUMMINGBIRD"]),
            service_omega(PROFILES["BELZEBUB"]),
        )

    def test_cadence_rank_places_mercury_before_jupiter(self):
        self.assertEqual(
            cadence_rank(("BELZEBUB", "HUMMINGBIRD")),
            ("HUMMINGBIRD", "BELZEBUB"),
        )

    def test_period_is_inverse_frequency(self):
        p = PROFILES["MOLE"]
        self.assertAlmostEqual(
            service_period(p) * service_omega(p),
            2.0 * math.pi,
            places=12,
        )

    def test_tau_scales_frequency_linearly(self):
        p = PROFILES["SPIDER"]
        self.assertAlmostEqual(service_omega(p, tau=2.0), 2.0 * service_omega(p), places=12)

    def test_invalid_parameters_fail_closed(self):
        with self.assertRaises(ValueError):
            service_omega(PROFILES["OWL"], tau=0.0)

    def test_live_workload_profile_selects_bounded_batch(self):
        counts = {
            "SPIDER": 1000,
            "RAVEN": 1100,
            "HOUND": 900,
            "MOLE": 1200,
            "OWL": 1000,
            "ANT": 950,
            "MANTIS": 800,
        }
        size = bounded_batch_size(counts, 2000, 5)
        self.assertGreaterEqual(size, 8)
        self.assertLessEqual(size, 128)

    def test_five_cpu_scalar_ceiling_is_below_ten_for_frozen_cost_model(self):
        serial_work = 8600.0
        expected_routed_specialist = (23.0 / 6.0) * (7300.0 / 7.0)
        routed_work = expected_routed_specialist + 1300.0
        ceiling = ideal_scalar_ceiling(serial_work, routed_work, 5)
        self.assertGreater(ceiling, 8.0)
        self.assertLess(ceiling, 10.0)

    def test_omega0_anchor(self):
        self.assertAlmostEqual(OMEGA0, 2.0 * math.pi * 7.83, places=12)


if __name__ == "__main__":
    unittest.main()
