import unittest
import json
from fastapi.testclient import TestClient

from api.main import app, passport_manager, tool_registry, agent_core


class TestE2EIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_passport_endpoint(self):
        response = self.client.get("/passport")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("agent_id", data)
        self.assertIn("capabilities", data)
        self.assertIn("tools", data)

    def test_get_tools_endpoint(self):
        response = self.client.get("/tools")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tools", data)
        self.assertIsInstance(data["tools"], list)
        self.assertGreater(len(data["tools"]), 0)
        tool_ids = [t["tool_id"] for t in data["tools"]]
        self.assertIn("weather_tool", tool_ids)
        self.assertIn("resource_location_tool", tool_ids)

    def test_execute_direct_core(self):
        payload = {
            "request_id": "req-e2e-1",
            "user_input": "Check weather",
            "context": {"location": {"latitude": 15.5, "longitude": 75.5}},
            "requested_capabilities": ["weather_monitoring"],
            "adapter_type": "direct_core"
        }
        response = self.client.post("/execute", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "awaiting_tools")
        self.assertEqual(data["request_id"], "req-e2e-1")

    def test_execute_portable_adapter(self):
        payload = {
            "request_id": "req-e2e-2",
            "user_input": "Find shelters",
            "context": {"location": {"latitude": 15.5, "longitude": 75.5}, "resource_type": "shelter"},
            "requested_capabilities": ["resource_location"],
            "adapter_type": "portable"
        }
        response = self.client.post("/execute", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "awaiting_tools")

    def test_execute_langchain_adapter(self):
        payload = {
            "request_id": "req-e2e-3",
            "user_input": "Check weather via LangChain",
            "context": {"location": {"latitude": 15.5, "longitude": 75.5}},
            "requested_capabilities": ["weather_monitoring"],
            "adapter_type": "langchain"
        }
        response = self.client.post("/execute", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "awaiting_tools")

    def test_unauthorized_capability_rejection(self):
        payload = {
            "request_id": "req-unauth-1",
            "user_input": "Run admin command",
            "context": {},
            "requested_capabilities": ["unauthorized_admin_capability"],
            "adapter_type": "direct_core"
        }
        response = self.client.post("/execute", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertGreater(len(data["errors"]), 0)
        self.assertIn("not authorized", data["errors"][0]["message"].lower())

    def test_verify_trust_endpoint(self):
        response = self.client.post("/verify/trust")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("is_valid", data)
        self.assertTrue(data["is_valid"])

    def test_verify_portability_endpoint(self):
        response = self.client.post("/verify/portability")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("is_valid", data)
        self.assertTrue(data["is_valid"])

    def test_malformed_request_validation(self):
        # Missing required field 'user_input'
        payload = {
            "adapter_type": "direct_core"
        }
        response = self.client.post("/execute", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_json_evidence_serialization(self):
        resp = self.client.get("/passport")
        data = resp.json()
        json_str = json.dumps(data)
        self.assertIsInstance(json_str, str)
        self.assertIn("agent_id", json_str)


if __name__ == "__main__":
    unittest.main()

