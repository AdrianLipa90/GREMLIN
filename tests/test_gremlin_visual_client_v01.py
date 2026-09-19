import unittest

from client.gremlin_web_server_v01 import (
    STATIC_FILES,
    WEB_ROOT,
    WEB_SCHEMA,
    bestiary_payload,
    health_payload,
    load_example_request,
    process_prototype_request,
    status_payload,
)


class GremlinVisualClientV01Tests(unittest.TestCase):
    def test_example_request_runs_end_to_end_through_visual_api(self):
        request = load_example_request()
        wrapper = process_prototype_request(request)
        self.assertEqual(wrapper["ui_schema"], WEB_SCHEMA)
        self.assertEqual(wrapper["response"]["status"], "VALIDATED_PROTOTYPE")
        self.assertEqual(wrapper["response"]["validation_scope"], "REFERENCE_CONFORMANCE_ONLY")
        self.assertIn("phasenav_ir", wrapper["response"]["artifacts"])
        self.assertIn("prototype", wrapper["response"]["artifacts"])
        self.assertIn("experiment_receipt", wrapper["response"]["artifacts"])
        self.assertFalse(wrapper["authority"]["production_runtime_write"])
        self.assertFalse(wrapper["authority"]["execution_admitted"])
        self.assertFalse(wrapper["authority"]["canon_allowed"])

    def test_health_payload_is_fail_closed_for_authority(self):
        health = health_payload()
        self.assertEqual(health["status"], "READY")
        self.assertEqual(health["api"], "/api/prototype")
        self.assertFalse(health["production_runtime_write"])
        self.assertFalse(health["execution_admitted"])
        self.assertFalse(health["canon_allowed"])

    def test_static_surface_is_exact_whitelist(self):
        self.assertEqual(set(STATIC_FILES), {"/", "/index.html", "/app.js", "/styles.css"})
        for _, (name, _) in STATIC_FILES.items():
            self.assertTrue((WEB_ROOT / name).is_file())

    def test_workspace_cockpit_and_evidence_tabs_are_present(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("GREMLIN Workspace", html)
        self.assertIn("Product state", html)
        self.assertIn("Active vocabulary", html)
        self.assertIn("Activity", html)
        self.assertIn("Technical view", html)
        self.assertIn("Problem & candidate", html)
        self.assertIn("Operator graph", html)
        self.assertIn("Prototype & receipt", html)
        for tab in ("Prototype", "BELZEBUB", "Tests", "Receipt"):
            self.assertIn(f">{tab}<", html)

    def test_browser_surface_uses_text_content_not_html_injection(self):
        script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("eval(", script)
        self.assertIn("textContent", script)
        self.assertIn('fetchJson("/api/prototype"', script)
        self.assertIn('fetchJson("/api/status"', script)
        self.assertIn('fetchJson("/api/bestiary"', script)
        self.assertIn("textContent", script)
        self.assertIn("createElementNS", script)

    def test_reference_server_exposes_cockpit_status_and_bestiary_without_product_claims(self):
        status = status_payload()
        self.assertEqual(status["status"], "READY")
        self.assertEqual(status["product"]["status"], "REFERENCE_VALIDATION")
        self.assertEqual(status["capabilities"]["surface"], "reference")
        self.assertEqual(status["capabilities"]["tool_count"], 32)
        self.assertFalse(status["authority"]["execution_admitted"])

        bestiary = bestiary_payload()
        self.assertEqual(bestiary["status"], "READY")
        self.assertEqual(bestiary["species_count"], 18)
        self.assertEqual(len(bestiary["species"]), 18)
        self.assertFalse(bestiary["authority"]["canon_allowed"])


    def test_visual_client_does_not_add_external_frontend_dependencies(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)
        self.assertIn('src="/app.js"', html)
        self.assertIn('href="/styles.css"', html)


if __name__ == "__main__":
    unittest.main()
