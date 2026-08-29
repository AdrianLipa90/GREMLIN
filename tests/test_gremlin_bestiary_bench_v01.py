import unittest

from tools.gremlin_bestiary_bench_v01 import (
    DEFAULT_WORKERS,
    bestiary_makespan,
    make_workload,
    run,
)


class GremlinBestiaryBenchTests(unittest.TestCase):
    def test_workload_is_deterministic(self):
        self.assertEqual(make_workload(32, 616), make_workload(32, 616))
        self.assertNotEqual(make_workload(32, 616), make_workload(32, 617))

    def test_default_topology_crosses_candidate_threshold(self):
        result = run(10_000, 616)
        self.assertGreaterEqual(result["throughput_speedup"], 10.0)
        self.assertTrue(result["candidate"])
        self.assertEqual(result["validation_scope"], "DETERMINISTIC_VIRTUAL_SERVICE_TOPOLOGY_ONLY")

    def test_single_worker_per_species_is_below_order_of_magnitude(self):
        one_each = {name: 1 for name in DEFAULT_WORKERS}
        result = run(10_000, 616, one_each)
        self.assertLess(result["throughput_speedup"], 10.0)
        self.assertGreater(result["throughput_speedup"], 5.0)

    def test_belzebub_replica_alone_nearly_reaches_threshold(self):
        cfg = {name: 1 for name in DEFAULT_WORKERS}
        cfg["BELZEBUB"] = 2
        result = run(10_000, 616, cfg)
        self.assertLess(result["throughput_speedup"], 10.0)
        self.assertGreater(result["throughput_speedup"], 9.0)

    def test_mole_and_belzebub_replication_breaks_bottleneck(self):
        cfg = {name: 1 for name in DEFAULT_WORKERS}
        cfg["MOLE"] = 2
        cfg["BELZEBUB"] = 2
        result = run(10_000, 616, cfg)
        self.assertGreater(result["throughput_speedup"], 13.0)

    def test_missing_worker_fails_closed(self):
        cfg = dict(DEFAULT_WORKERS)
        cfg["OWL"] = 0
        with self.assertRaises(ValueError):
            bestiary_makespan(make_workload(8), cfg)


if __name__ == "__main__":
    unittest.main()
