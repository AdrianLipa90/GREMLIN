import copy
import unittest

from tools.gremlin_client_protocol_v01 import (
    GremlinClientProtocolError,
    REQUEST_SCHEMA,
    run_client_request,
)
from tools.gremlin_experiment_harness_v01 import run_reference_experiment
from tools.gremlin_phasenav_compiler_v01 import (
    CANDIDATE_SCHEMA,
    GremlinPhaseNavCompilerError,
    compile_phasenav_ir,
    evaluate_ir,
    validate_phasenav_ir,
)
from tools.gremlin_prototype_builder_v01 import (
    GremlinPrototypeBuilderError,
    build_python_reference_prototype,
    validate_prototype,
)


def candidate():
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-qhtri-001",
        "status": "SURVIVED_AUDIT",
        "audit": {
            "belzebub_result": "SURVIVED",
            "counterexamples_checked": 4,
        },
        "relations": [
            {"kind": "phase_lock", "a": 0, "b": 1, "gain": 1.25, "source_ref": "lock"},
            {"kind": "anti_lock", "a": 2, "b": 3, "gain": 0.5, "source_ref": "anti"},
            {"kind": "anchor", "lane": 4, "tau": 0.3, "gain": 0.75, "source_ref": "anchor"},
            {"kind": "torsion", "i": 5, "j": 6, "m": 4, "n": 2, "tau": -0.2, "gain": 0.9, "source_ref": "torsion"},
        ],
    }


class GremlinPhaseNavPrototypePipelineV01Tests(unittest.TestCase):
    def test_unaudited_candidate_is_fail_closed(self):
        c = candidate()
        c["status"] = "CANDIDATE"
        with self.assertRaisesRegex(GremlinPhaseNavCompilerError, "survive audit"):
            compile_phasenav_ir(c)

    def test_compile_is_deterministic_and_preserves_integer_harmonic_order(self):
        a = compile_phasenav_ir(candidate())
        b = compile_phasenav_ir(candidate())
        self.assertTrue(validate_phasenav_ir(a))
        self.assertEqual(a["ir_commitment"], b["ir_commitment"])
        self.assertFalse(a["normalization"]["gcd_reduction"])
        torsion = next(t for t in a["terms"] if t["source_ref"] == "torsion")
        self.assertEqual(torsion["ell"][5], 2)
        self.assertEqual(torsion["ell"][6], -4)

    def test_reference_prototype_is_valid_python_and_untrusted(self):
        ir = compile_phasenav_ir(candidate())
        p = build_python_reference_prototype(ir)
        self.assertTrue(validate_prototype(p, ir))
        compile(p["source"], "<test-prototype>", "exec")
        self.assertIn("float.fromhex", p["source"])
        self.assertEqual(p["status"], "UNTRUSTED_PROTOTYPE")
        self.assertFalse(p["production_runtime_write"])
        self.assertFalse(p["execution_admitted"])
        self.assertFalse(p["canon_allowed"])

    def test_tampered_prototype_source_is_rejected(self):
        ir = compile_phasenav_ir(candidate())
        p = build_python_reference_prototype(ir)
        p["source"] += "\nopen('/tmp/x','w')\n"
        with self.assertRaisesRegex(GremlinPrototypeBuilderError, "not deterministic"):
            validate_prototype(p, ir)

    def test_experiment_harness_matches_ir_reference(self):
        ir = compile_phasenav_ir(candidate())
        p = build_python_reference_prototype(ir)
        receipt = run_reference_experiment(ir, p, sample_count=48, tolerance=1e-12)
        self.assertEqual(receipt["status"], "VALIDATED_PROTOTYPE")
        self.assertEqual(receipt["validation_scope"], "REFERENCE_CONFORMANCE_ONLY")
        self.assertTrue(all(v == "PASS" for v in receipt["tests"].values()))
        self.assertFalse(receipt["production_runtime_write"])
        self.assertFalse(receipt["execution_admitted"])
        self.assertFalse(receipt["canon_allowed"])

    def test_ir_reference_output_is_finite(self):
        ir = compile_phasenav_ir(candidate())
        potential, force = evaluate_ir([0.1] * 36, ir)
        self.assertEqual(len(force), 36)
        self.assertTrue(abs(potential) < 100.0)
        self.assertTrue(all(abs(v) < 100.0 for v in force))

    def test_client_end_to_end_returns_lineage_artifacts(self):
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": "req-001",
            "target": "python_reference",
            "candidate": candidate(),
            "sample_count": 32,
        }
        response = run_client_request(request)
        self.assertEqual(response["status"], "VALIDATED_PROTOTYPE")
        self.assertEqual(response["pipeline"], [
            "SURVIVED_AUDIT",
            "PHASENAV_IR_CANDIDATE",
            "UNTRUSTED_PROTOTYPE",
            "VALIDATED_PROTOTYPE",
        ])
        self.assertIn("phasenav_ir", response["artifacts"])
        self.assertIn("prototype", response["artifacts"])
        self.assertIn("experiment_receipt", response["artifacts"])
        self.assertFalse(response["production_runtime_write"])
        self.assertFalse(response["execution_admitted"])
        self.assertFalse(response["canon_allowed"])

    def test_client_response_is_deterministic(self):
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": "req-deterministic",
            "candidate": candidate(),
            "sample_count": 16,
        }
        a = run_client_request(copy.deepcopy(request))
        b = run_client_request(copy.deepcopy(request))
        self.assertEqual(a["response_commitment"], b["response_commitment"])

    def test_client_cannot_request_execution_or_canon_authority(self):
        for key in ("request_execution_admission", "request_canon_promotion"):
            request = {
                "schema": REQUEST_SCHEMA,
                "candidate": candidate(),
                key: True,
            }
            with self.assertRaises(GremlinClientProtocolError):
                run_client_request(request)


if __name__ == "__main__":
    unittest.main()
