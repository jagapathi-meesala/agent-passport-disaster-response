"""
Unit tests for Agent Passport schemas, dynamic file loader, validators, verifier, and API endpoint.
"""

import unittest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from passport.schema import AgentPassport
from passport.manager import PassportManager
from verification.passport_verifier import PassportVerifier
from api.main import app


class TestPassportSystem(unittest.TestCase):

    def setUp(self):
        self.valid_data = {
            "passport_version": "1.0.0",
            "agent_id": "test-agent-01",
            "name": "TestDisasterAgent",
            "version": "1.0.0",
            "description": "Test disaster response agent specification.",
            "capabilities": ["situational_assessment", "logistics_coordination"],
            "input_types": ["text", "json"],
            "output_types": ["text", "json"],
            "tools": ["tool_a", "tool_b"],
            "contract_version": "1.0.0"
        }

    def test_1_valid_passport_loads(self):
        """1. Test that a valid passport dictionary loads successfully."""
        passport = AgentPassport.from_dict(self.valid_data)
        self.assertEqual(passport.agent_id, "test-agent-01")
        self.assertEqual(passport.name, "TestDisasterAgent")
        self.assertEqual(passport.version, "1.0.0")

    def test_2_invalid_passport_rejected(self):
        """2. Test that an invalid passport with empty agent_id is rejected."""
        invalid_data = self.valid_data.copy()
        invalid_data["agent_id"] = "   "
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(invalid_data)

    def test_3_missing_required_field_rejected(self):
        """3. Test that missing required field (description) is rejected."""
        missing_data = self.valid_data.copy()
        del missing_data["description"]
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(missing_data)

    def test_4_duplicate_capabilities_rejected(self):
        """4. Test that duplicate capability names are rejected."""
        dup_data = self.valid_data.copy()
        dup_data["capabilities"] = ["situational_assessment", "situational_assessment"]
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(dup_data)

    def test_5_duplicate_tools_rejected(self):
        """5. Test that duplicate tool names are rejected."""
        dup_data = self.valid_data.copy()
        dup_data["tools"] = ["tool_a", "tool_a"]
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(dup_data)

    def test_6_invalid_version_rejected(self):
        """6. Test that invalid semantic version format is rejected."""
        invalid_ver_data = self.valid_data.copy()
        invalid_ver_data["version"] = "1.0"
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(invalid_ver_data)

    def test_7_passport_serialization(self):
        """7. Test that passport serialization (to_dict, to_json) works."""
        passport = AgentPassport.from_dict(self.valid_data)
        dict_data = passport.to_dict()
        self.assertIsInstance(dict_data, dict)
        self.assertEqual(dict_data["agent_id"], "test-agent-01")

        json_str = passport.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn("test-agent-01", json_str)

    def test_8_passport_deserialization(self):
        """8. Test that passport deserialization (from_dict, from_json) works."""
        passport = AgentPassport.from_dict(self.valid_data)
        json_str = passport.to_json()

        deserialized_from_json = AgentPassport.from_json(json_str)
        self.assertEqual(deserialized_from_json.agent_id, passport.agent_id)

        deserialized_from_dict = AgentPassport.from_dict(self.valid_data)
        self.assertEqual(deserialized_from_dict.agent_id, passport.agent_id)

    def test_9_loading_from_external_configuration(self):
        """9. Test loading from external configuration file config/passport.json."""
        manager = PassportManager()
        passport = manager.load_from_file("config/passport.json")
        self.assertIsNotNone(passport)
        self.assertEqual(passport.agent_id, "disaster-response-agent-01")
        self.assertEqual(passport.name, "DisasterResponseAgent")
        self.assertIn("situational_assessment", passport.capabilities)

    def test_10_passport_verifier(self):
        """10. Test PassportVerifier integrity check and permission checking."""
        passport = AgentPassport.from_dict(self.valid_data)
        verifier = PassportVerifier()
        result = verifier.verify(passport)
        self.assertTrue(result.is_valid)
        self.assertTrue(verifier.check_permission(passport, "tool_a"))
        self.assertFalse(verifier.check_permission(passport, "unauthorized_tool"))

    def test_11_api_get_passport_endpoint(self):
        """11. Test GET /passport REST API endpoint returns validated passport payload."""
        client = TestClient(app)
        response = client.get("/passport")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["agent_id"], "disaster-response-agent-01")
        self.assertEqual(payload["name"], "DisasterResponseAgent")


if __name__ == "__main__":
    unittest.main()
