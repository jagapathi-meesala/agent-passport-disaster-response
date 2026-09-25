"""
Unit tests for Portability Verification Engine.

Tests PortabilityResult, Direct Core vs PortableAdapter vs LangChainAdapter semantic equivalence,
request ID normalization, status/tool/result/error matching, unauthorized capability enforcement,
framework isolation, hardcoding audit, JSON evidence export, and failure detection.
"""

import unittest
from typing import Dict, Any

from contracts.schemas import AgentRequest, AgentResponse, AgentStatus
from verification.portability_verifier import PortabilityVerifier, PortabilityResult
from core.agent import AgentCore
from passport.manager import PassportManager
from tools.base import ToolRegistry
from tools.weather_tool import WeatherTool
from tools.weather_client import WeatherProviderClient


class MockWeatherClient(WeatherProviderClient):
    """Local offline mock client for deterministic tool execution testing."""
    def __init__(self):
        super().__init__(service_url="https://test-weather.example/v1")

    def fetch_weather(self, latitude: float, longitude: float) -> dict:
        return {
            "current_weather": {
                "temperature": 25.0,
                "windspeed": 10.0,
                "winddirection": 90.0,
                "time": "2026-09-25T12:00:00Z"
            }
        }


class TestPortabilityVerifierSystem(unittest.TestCase):

    def setUp(self):
        self.passport_manager = PassportManager()
        self.passport_manager.load_from_file("config/passport.json")
        self.tool_registry = ToolRegistry()
        self.core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.tool_registry)
        self.verifier = PortabilityVerifier()

    def test_1_portability_result_creation(self):
        """1. Test PortabilityResult serialization and field access."""
        res = PortabilityResult(
            is_valid=True,
            execution_paths_tested=["direct_core", "portable_adapter", "langchain_adapter"],
            status_match=True
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.execution_paths_tested), 3)
        self.assertIsInstance(res.to_dict(), dict)
        self.assertIn("is_valid", res.to_json())

    def test_2_direct_core_execution(self):
        """2. Test Direct AgentCore execution path normalization."""
        norm = self.verifier.normalize_response(
            self.core.process_request(
                self.core.passport_manager.load_from_dict({
                    "passport_version": "1.0.0",
                    "agent_id": "test-agent",
                    "name": "TestAgent",
                    "version": "1.0.0",
                    "description": "Test",
                    "capabilities": ["situational_assessment"],
                    "input_types": ["text"],
                    "output_types": ["text"],
                    "tools": ["t1"],
                    "contract_version": "1.0.0"
                }) and None or self.core.process_request(
                    self.core.passport_manager.get_active_passport() and None or
                    type("Req", (), {"request_id": "req-1", "user_input": "Assess", "context": {}, "requested_capabilities": ["situational_assessment"]})()
                )
            ) if False else self.core.process_request(
                type("Req", (), {"request_id": "req-1", "user_input": "Assess", "context": {}, "requested_capabilities": ["situational_assessment"]})()
            ) if False else self.core.process_request(
                self.core.load_passport() and
                self.core.process_request(
                    type("Req", (), {})()
                ) if False else None
            ) if False else None
        ) if False else None
        # Clean test execution
        from contracts.schemas import AgentRequest
        req = AgentRequest(request_id="req-direct-02", user_input="Assess situational risks", requested_capabilities=["situational_assessment"])
        resp = self.core.process_request(req)
        norm = self.verifier.normalize_response(resp)
        self.assertEqual(norm["status"], "awaiting_tools")
        self.assertEqual(norm["used_capabilities"], ["situational_assessment"])

    def test_3_portable_adapter_execution(self):
        """3. Test PortableAdapter execution path normalization."""
        from adapters.portable_adapter import PortableAdapter
        adapter = PortableAdapter(core_agent=self.core)
        payload = {"request_id": "req-port-03", "input": "Assess risks", "requested_capabilities": ["situational_assessment"]}
        resp = adapter.run_framework_task(payload)
        norm = self.verifier.normalize_response(resp)
        self.assertEqual(norm["status"], "awaiting_tools")

    def test_4_langchain_adapter_execution(self):
        """4. Test LangChainAdapter execution path normalization."""
        from adapters.langchain_adapter import LangChainAdapter
        adapter = LangChainAdapter(core_agent=self.core)
        payload = {"request_id": "req-lc-04", "input": "Assess risks", "requested_capabilities": ["situational_assessment"]}
        resp = adapter.run_framework_task(payload)
        norm = self.verifier.normalize_response(resp)
        self.assertEqual(norm["status"], "awaiting_tools")

    def test_5_valid_request_semantic_equivalence(self):
        """5. Test verify_equivalence asserts 100% equivalence across all 3 execution paths."""
        payload = {
            "request_id": "req-eq-05",
            "input": "Evaluate risks",
            "context": {"region": "north"},
            "requested_capabilities": ["situational_assessment"]
        }
        res = self.verifier.verify_equivalence(self.core, payload)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.status_match)
        self.assertTrue(res.capabilities_match)
        self.assertTrue(res.tools_match)
        self.assertTrue(res.result_match)
        self.assertTrue(res.errors_match)

    def test_6_status_equivalence(self):
        """6. Test status_match property."""
        res = self.verifier.verify_equivalence(self.core, {"request_id": "req-6", "input": "Assess"})
        self.assertTrue(res.status_match)

    def test_7_result_equivalence(self):
        """7. Test result_match property."""
        res = self.verifier.verify_equivalence(self.core, {"request_id": "req-7", "input": "Assess"})
        self.assertTrue(res.result_match)

    def test_8_capability_equivalence(self):
        """8. Test capabilities_match property."""
        res = self.verifier.verify_equivalence(self.core, {"request_id": "req-8", "input": "Assess", "requested_capabilities": ["situational_assessment"]})
        self.assertTrue(res.capabilities_match)

    def test_9_tool_equivalence(self):
        """9. Test tools_match property."""
        res = self.verifier.verify_equivalence(self.core, {"request_id": "req-9", "input": "Assess"})
        self.assertTrue(res.tools_match)

    def test_10_error_equivalence(self):
        """10. Test errors_match property."""
        res = self.verifier.verify_equivalence(self.core, {"request_id": "req-10", "input": "Assess"})
        self.assertTrue(res.errors_match)

    def test_11_generated_request_id_normalization(self):
        """11. Test that missing request_id does not cause portability equivalence failure."""
        payload = {"input": "Evaluate risks without explicit request_id", "requested_capabilities": ["situational_assessment"]}
        res = self.verifier.verify_equivalence(self.core, payload)
        self.assertTrue(res.is_valid)

    def test_12_unauthorized_capability_equivalence(self):
        """12. Test unauthorized capability request fails identically across all 3 entry points."""
        res = self.verifier.verify_unauthorized_capability(self.core, "unauthorized_cyber_attack")
        self.assertTrue(res.is_valid)
        self.assertTrue(res.status_match)
        self.assertEqual(res.details["direct_core"]["status"], "failed")
        self.assertEqual(res.details["portable_adapter"]["status"], "failed")
        self.assertEqual(res.details["langchain_adapter"]["status"], "failed")

    def test_13_tool_execution_equivalence_using_local_mock(self):
        """13. Test operational tool execution produces identical results across all 3 entry points."""
        weather_tool = WeatherTool(client=MockWeatherClient())
        self.tool_registry.register_tool(weather_tool)

        payload = {
            "request_id": "req-tool-13",
            "input": "Monitor weather conditions",
            "context": {"location": {"latitude": 10.0, "longitude": 20.0}},
            "requested_capabilities": ["weather_monitoring"]
        }

        res = self.verifier.verify_equivalence(self.core, payload)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.details["direct_core"]["status"], "completed")
        self.assertEqual(res.details["portable_adapter"]["status"], "completed")
        self.assertEqual(res.details["langchain_adapter"]["status"], "completed")
        self.assertEqual(res.details["direct_core"]["used_tools"], ["weather_tool"])
        self.assertEqual(res.details["portable_adapter"]["used_tools"], ["weather_tool"])
        self.assertEqual(res.details["langchain_adapter"]["used_tools"], ["weather_tool"])

    def test_14_framework_isolation_audit(self):
        """14. Test verify_framework_isolation asserts zero forbidden framework imports in core/tools/contracts/passport."""
        isolation_ok = self.verifier.verify_framework_isolation()
        self.assertTrue(isolation_ok)

    def test_15_hardcoding_audit(self):
        """15. Test verify_hardcoding_audit asserts zero embedded secrets/defaults."""
        audit_ok = self.verifier.verify_hardcoding_audit()
        self.assertTrue(audit_ok)

    def test_16_json_serialization_of_portability_result(self):
        """16. Test serialization of PortabilityResult to dict and JSON."""
        res = self.verifier.run_full_verification(self.core)
        res_dict = res.to_dict()
        res_json = res.to_json()
        self.assertIsInstance(res_dict, dict)
        self.assertIsInstance(res_json, str)
        self.assertIn("is_valid", res_dict)
        self.assertIn("execution_paths_tested", res_json)

    def test_17_overall_verification_pass(self):
        """17. Test run_full_verification returns overall pass for current repository state."""
        res = self.verifier.run_full_verification(self.core)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.framework_isolation_passed)
        self.assertTrue(res.hardcoding_audit_passed)

    def test_18_overall_verification_failure_detection(self):
        """18. Test PortabilityVerifier detects mismatch if one path returns different status."""
        # Create a mock core that simulates failure on adapter call
        class MismatchedCore(AgentCore):
            def process_request(self, request):
                resp = super().process_request(request)
                if request.request_id.startswith("lc-req-"):
                    resp.status = AgentStatus.FAILED
                return resp

        mismatched_core = MismatchedCore(passport_manager=self.passport_manager, tool_registry=self.tool_registry)
        res = self.verifier.verify_equivalence(mismatched_core, {"input": "Test mismatch"})
        self.assertFalse(res.is_valid)
        self.assertFalse(res.status_match)


if __name__ == "__main__":
    unittest.main()
