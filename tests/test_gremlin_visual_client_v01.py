import unittest

from gremlin_mcp.workspace import system_payload
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

    def test_reference_dashboard_contract_matches_shared_workspace_surface(self):
        dashboard = system_payload(surface="reference")
        self.assertEqual(dashboard["surface"], "reference")
        self.assertEqual(dashboard["mcp"]["tool_count"], 32)
        self.assertEqual(dashboard["bestiary"]["species_count"], 18)
        self.assertFalse(dashboard["authority"]["execution_admitted"])

    def test_static_surface_is_exact_whitelist(self):
        self.assertEqual(set(STATIC_FILES), {"/", "/index.html", "/app.js", "/styles.css"})
        for _, (name, _) in STATIC_FILES.items():
            self.assertTrue((WEB_ROOT / name).is_file())

    def test_three_pane_workspace_and_evidence_tabs_are_present(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Problem & candidate", html)
        self.assertIn("Operator graph", html)
        self.assertIn("Prototype & receipt", html)
        for tab in ("Prototype", "BELZEBUB", "Tests", "Receipt"):
            self.assertIn(f">{tab}<", html)
        self.assertIn("execution admission: off", html)
        self.assertIn("GREMLIN at a glance", html)
        self.assertIn("Bestiary map", html)
        self.assertIn('id="bestiary-grid"', html)
        self.assertIn('id="system-tool-count"', html)
        self.assertIn('id="refresh-system"', html)
        self.assertIn('id="technical-toggle"', html)
        self.assertIn('id="activity-list"', html)
        self.assertIn('id="retry-error"', html)
        self.assertIn('id="error-guidance"', html)
        self.assertIn('title="Ctrl/Cmd+Enter"', html)
        self.assertIn('aria-live="polite"', html)

    def test_browser_surface_uses_text_content_not_html_injection(self):
        script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("eval(", script)
        self.assertIn("textContent", script)
        self.assertIn('fetchJson("/api/prototype"', script)
        self.assertIn('fetchJson("/api/system"', script)
        self.assertIn("WorkspaceHttpError", script)
        self.assertIn("error_contract", script)
        self.assertIn("user_action", script)
        self.assertIn("sessionStorage", script)
        self.assertIn("TECHNICAL_MODE_STORAGE_KEY", script)
        self.assertNotIn("localStorage", script)
        self.assertIn('document.addEventListener("keydown"', script)
        self.assertIn('event.key === "Enter"', script)
        self.assertIn("event.ctrlKey || event.metaKey", script)
        self.assertIn("refreshSystemButton", script)
        self.assertIn("retryErrorButton.hidden = contract.retryable !== true", script)
        self.assertIn("recordActivity", script)
        self.assertIn("createElementNS", script)
        self.assertIn("bestiaryGrid", script)

    def test_workspace_session_storage_is_preference_only(self):
        script = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn(
            'window.sessionStorage.setItem(TECHNICAL_MODE_STORAGE_KEY, enabled ? "true" : "false")',
            script,
        )
        self.assertNotIn('sessionStorage.setItem("candidate', script)
        self.assertNotIn('sessionStorage.setItem("problem', script)
        self.assertNotIn("candidateEditor.value,", script)
        self.assertNotIn("problemBrief.value,", script)

    def test_reference_server_exposes_status_bestiary_and_system_without_product_claims(self):
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

        dashboard = system_payload(surface="reference")
        self.assertEqual(dashboard["surface"], "reference")
        self.assertEqual(dashboard["mcp"]["tool_count"], 32)

    def test_visual_client_does_not_add_external_frontend_dependencies(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)
        self.assertIn('src="/app.js"', html)
        self.assertIn('href="/styles.css"', html)


if __name__ == "__main__":
    unittest.main()
