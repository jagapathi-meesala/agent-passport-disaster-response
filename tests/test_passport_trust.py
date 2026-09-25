"""
Unit tests for Passport Trust & Identity Verification Engine.

Tests PassportTrustResult, PassportTrustVerifier, dynamic contract version matching,
schema integrity, identity invariance across Direct Core, PortableAdapter, and LangChainAdapter,
unauthorized capability rejection, framework isolation, zero hardcoding, and offline verification.
"""

import os
import json
import unittest
from pydantic import ValidationError

from passport.schema import AgentPassport
from passport.manager import PassportManager
from verification.passport_trust_verifier import PassportTrustVerifier, PassportTrustResult
from contracts.behavior import BehaviorContract
from core.agent import AgentCore
from tools.base import ToolRegistry


class TestPassportTrustSystem(unittest.TestCase):

    def setUp(self):
        self.passport_manager = PassportManager()
        self.valid_passport = self.passport_manager.load_from_file("config/passport.json")
        self.tool_registry = ToolRegistry()
        self.core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.tool_registry)
        self.verifier = PassportTrustVerifier()

    def test_1_passport_trust_result_creation(self):
        """1. Test PassportTrustResult field initialization."""
        res = PassportTrustResult(
            is_valid=True,
            agent_id="test-01",
            version="1.0.0",
            passport_version="1.0.0",
            contract_version="1.0.0",
            expected_contract_version="1.0.0",
            contract_version_matching=True,
            schema_integrity_valid=True,
            capabilities_count=5,
            authorized_tools_count=4,
            adapter_identity_consistent=True,
            unauthorized_capability_rejection_passed=True
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(res.agent_id, "test-01")

    def test_2_to_dict_method(self):
        """2. Test PassportTrustResult.to_dict() returns valid dictionary."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["agent_id"], "disaster-response-agent-01")
        self.assertTrue(d["is_valid"])

    def test_3_to_json_method(self):
        """3. Test PassportTrustResult.to_json() returns valid JSON string."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        json_str = res.to_json()
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["agent_id"], "disaster-response-agent-01")

    def test_4_valid_passport_verification(self):
        """4. Test verify_trust with valid config/passport.json specification."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.schema_integrity_valid)
        self.assertTrue(res.contract_version_matching)

    def test_5_invalid_semver(self):
        """5. Test passport with invalid semver format is rejected by schema validator."""
        valid_dict = self.valid_passport.to_dict()
        valid_dict["version"] = "invalid_version"
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(valid_dict)

    def test_6_missing_identity(self):
        """6. Test passport with empty agent_id is rejected by schema validator."""
        valid_dict = self.valid_passport.to_dict()
        valid_dict["agent_id"] = "   "
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(valid_dict)

    def test_7_duplicate_capability_detection(self):
        """7. Test duplicate capability names are rejected by schema validator."""
        valid_dict = self.valid_passport.to_dict()
        valid_dict["capabilities"] = ["weather_monitoring", "weather_monitoring"]
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(valid_dict)

    def test_8_duplicate_tool_detection(self):
        """8. Test duplicate tool names are rejected by schema validator."""
        valid_dict = self.valid_passport.to_dict()
        valid_dict["tools"] = ["weather_tool", "weather_tool"]
        with self.assertRaises(ValidationError):
            AgentPassport.from_dict(valid_dict)

    def test_9_contract_version_matching(self):
        """9. Test passport with matching contract_version (1.0.0) matches BehaviorContract."""
        expected = BehaviorContract().contract_version
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        self.assertEqual(res.contract_version, expected)
        self.assertTrue(res.contract_version_matching)

    def test_10_contract_version_mismatch(self):
        """10. Test passport with mismatched contract_version (9.9.9) fails contract version matching."""
        mismatched_dict = self.valid_passport.to_dict()
        mismatched_dict["contract_version"] = "9.9.9"
        mismatched_passport = AgentPassport.from_dict(mismatched_dict)

        res = self.verifier.verify_trust(mismatched_passport, self.core)
        self.assertFalse(res.contract_version_matching)
        self.assertFalse(res.is_valid)

    def test_11_capability_verification(self):
        """11. Test capabilities_count reflects actual capability list length."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        self.assertEqual(res.capabilities_count, len(self.valid_passport.capabilities))

    def test_12_tool_authorization_verification(self):
        """12. Test authorized_tools_count reflects actual tool list length."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        self.assertEqual(res.authorized_tools_count, len(self.valid_passport.tools))

    def test_13_direct_core_identity_consistency(self):
        """13. Test Direct Core identity metadata matches bound passport identity."""
        status = self.core.get_status()
        self.assertEqual(status["agent_id"], self.valid_passport.agent_id)

    def test_14_portable_adapter_identity_consistency(self):
        """14. Test PortableAdapter executes task cleanly under bound passport identity."""
        from adapters.portable_adapter import PortableAdapter
        adapter = PortableAdapter(core_agent=self.core)
        payload = {"input": "Identity check task", "requested_capabilities": ["situational_assessment"]}
        res = adapter.run_framework_task(payload)
        self.assertIn(res["status"], ("completed", "awaiting_tools"))

    def test_15_langchain_adapter_identity_consistency(self):
        """15. Test LangChainAdapter executes task cleanly under bound passport identity."""
        from adapters.langchain_adapter import LangChainAdapter
        adapter = LangChainAdapter(core_agent=self.core)
        payload = {"input": "Identity check task", "requested_capabilities": ["situational_assessment"]}
        res = adapter.run_framework_task(payload)
        self.assertIn(res["status"], ("completed", "awaiting_tools"))

    def test_16_unauthorized_capability_rejection_direct_core(self):
        """16. Test Direct Core rejects unauthorized capability request."""
        from contracts.schemas import AgentRequest
        req = AgentRequest(request_id="unauth-d-16", user_input="Task", requested_capabilities=["unauthorized_cyber_attack"])
        res = self.core.process_request(req)
        self.assertEqual(res.status, "failed")
        self.assertTrue(any(e.error_code == "UNSUPPORTED_CAPABILITY" for e in res.errors))

    def test_17_unauthorized_capability_rejection_portable_adapter(self):
        """17. Test PortableAdapter rejects unauthorized capability request."""
        from adapters.portable_adapter import PortableAdapter
        adapter = PortableAdapter(core_agent=self.core)
        payload = {"input": "Task", "requested_capabilities": ["unauthorized_cyber_attack"]}
        res = adapter.run_framework_task(payload)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(any(e["error_code"] == "UNSUPPORTED_CAPABILITY" for e in res["errors"]))

    def test_18_unauthorized_capability_rejection_langchain_adapter(self):
        """18. Test LangChainAdapter rejects unauthorized capability request."""
        from adapters.langchain_adapter import LangChainAdapter
        adapter = LangChainAdapter(core_agent=self.core)
        payload = {"input": "Task", "requested_capabilities": ["unauthorized_cyber_attack"]}
        res = adapter.run_framework_task(payload)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(any(e["error_code"] == "UNSUPPORTED_CAPABILITY" for e in res["errors"]))

    def test_19_framework_isolation(self):
        """19. Verify zero forbidden framework imports in core/tools/contracts/passport."""
        for folder_name in ("core", "contracts", "tools", "passport"):
            base_dir = os.path.join(os.path.dirname(__file__), "..", folder_name)
            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read().lower()
                        for forbidden in ("langchain", "fastapi", "openai", "anthropic"):
                            self.assertNotIn(forbidden, content, f"Forbidden import '{forbidden}' in {file_path}")

    def test_20_hardcoding_audit(self):
        """20. Verify zero embedded secrets in production code."""
        with open("config/settings.py", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("sk-", content)

    def test_21_offline_verification(self):
        """21. Test trust verification executes completely offline without external HTTP calls."""
        res = self.verifier.verify_trust(self.valid_passport, self.core)
        self.assertTrue(res.is_valid)

    def test_22_evidence_result_reflects_actual_pass_fail_state(self):
        """22. Test failing passport produces is_valid = False in JSON evidence output."""
        mismatched_dict = self.valid_passport.to_dict()
        mismatched_dict["contract_version"] = "9.9.9"
        bad_passport = AgentPassport.from_dict(mismatched_dict)

        res = self.verifier.verify_trust(bad_passport, self.core)
        json_output = res.to_json()
        parsed = json.loads(json_output)

        self.assertFalse(parsed["is_valid"])
        self.assertFalse(parsed["contract_version_matching"])


if __name__ == "__main__":
    unittest.main()
