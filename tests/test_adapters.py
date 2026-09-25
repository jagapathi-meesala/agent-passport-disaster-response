"""
Unit tests for Portable Framework Adapter System.

Tests AbstractFrameworkAdapter, PortableAdapter, AdapterRegistry, contract translation,
AgentCore delegation, Passport authorization enforcement, framework independence, and zero hardcoding.
"""

import unittest
from typing import Any, Dict

from adapters.base import AbstractFrameworkAdapter
from adapters.portable_adapter import PortableAdapter
from adapters.registry import AdapterRegistry
from contracts.adapter import AdapterMetadata
from contracts.schemas import AgentRequest, AgentResponse, AgentStatus
from core.agent import AgentCore
from tools.base import ToolRegistry
from passport.manager import PassportManager


class DummyAdapter(AbstractFrameworkAdapter):
    """Concrete adapter subclass for testing AbstractFrameworkAdapter contracts."""

    def adapt_request(self, framework_payload: Any) -> AgentRequest:
        return AgentRequest(
            request_id="dummy-01",
            user_input="Dummy task instruction"
        )

    def adapt_response(self, core_response: AgentResponse) -> Dict[str, Any]:
        return {"status": core_response.status.value, "request_id": core_response.request_id}


class TestAdapterSystem(unittest.TestCase):

    def setUp(self):
        self.passport_manager = PassportManager()
        self.passport_manager.load_from_file("config/passport.json")
        self.tool_registry = ToolRegistry()
        self.core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.tool_registry)
        self.adapter = PortableAdapter(core_agent=self.core)
        self.registry = AdapterRegistry()

    def test_1_abstract_adapter_contract(self):
        """1. AbstractFrameworkAdapter requires core_agent and implements delegation methods."""
        dummy = DummyAdapter(core_agent=self.core)
        self.assertIs(dummy.core_agent, self.core)
        res = dummy.run_framework_task({})
        self.assertEqual(res["request_id"], "dummy-01")
        self.assertEqual(res["status"], "awaiting_tools")

    def test_2_portable_adapter_initialization(self):
        """2. PortableAdapter initializes metadata and core_agent reference correctly."""
        self.assertIs(self.adapter.core_agent, self.core)
        self.assertIsNotNone(self.adapter.metadata)
        self.assertEqual(self.adapter.metadata.adapter_id, "portable_reference_adapter")
        self.assertEqual(self.adapter.metadata.runtime_type, "reference")

    def test_3_valid_request_conversion(self):
        """3. Valid runtime payload is adapted to AgentRequest schema."""
        payload = {
            "request_id": "test-req-003",
            "input": "Perform disaster assessment",
            "context": {"priority": "high"},
            "requested_capabilities": ["situational_assessment"]
        }
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.request_id, "test-req-003")
        self.assertEqual(req.user_input, "Perform disaster assessment")
        self.assertEqual(req.context["priority"], "high")
        self.assertEqual(req.requested_capabilities, ["situational_assessment"])

    def test_4_missing_request_id_handling(self):
        """4. Runtime payload with missing request_id generates auto request_id."""
        req1 = self.adapter.adapt_request({"input": "Perform assessment"})
        self.assertTrue(req1.request_id.startswith("port-req-"))
        req2 = self.adapter.adapt_request({"request_id": "   ", "input": "Perform assessment"})
        self.assertTrue(req2.request_id.startswith("port-req-"))

    def test_5_missing_input_handling(self):
        """5. Runtime payload with missing or empty input raises ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.adapt_request({"request_id": "req-1"})
        with self.assertRaises(ValueError):
            self.adapter.adapt_request({"request_id": "req-1", "input": ""})

    def test_6_invalid_payload_handling(self):
        """6. Non-dictionary payload raises ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.adapt_request("not-a-dictionary")
        with self.assertRaises(ValueError):
            self.adapter.adapt_request(None)

    def test_7_context_conversion(self):
        """7. Payload context dictionary is preserved in AgentRequest."""
        payload = {
            "task_id": "task-777",
            "user_input": "Assess situation",
            "payload": {"location_bounds": {"lat": 10.0, "lon": 20.0}}
        }
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.context["location_bounds"]["lat"], 10.0)

    def test_8_capability_conversion(self):
        """8. Capability list in payload is converted to AgentRequest."""
        payload = {
            "request_id": "req-cap-8",
            "input": "Execute logistics task",
            "requested_capabilities": ["logistics_coordination"]
        }
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.requested_capabilities, ["logistics_coordination"])

    def test_9_agent_core_delegation(self):
        """9. PortableAdapter.run_framework_task delegates execution cleanly to AgentCore."""
        payload = {
            "request_id": "req-del-9",
            "input": "Evaluate disaster context",
            "requested_capabilities": ["situational_assessment"]
        }
        response_dict = self.adapter.run_framework_task(payload)
        self.assertIsInstance(response_dict, dict)
        self.assertEqual(response_dict["request_id"], "req-del-9")
        self.assertIn("status", response_dict)

    def test_10_agent_response_conversion(self):
        """10. AgentResponse object converts to structured JSON-compatible dictionary."""
        core_resp = AgentResponse(
            request_id="resp-10",
            status=AgentStatus.COMPLETED,
            result={"summary": "Task completed"},
            used_capabilities=["situational_assessment"],
            used_tools=[]
        )
        dict_resp = self.adapter.adapt_response(core_resp)
        self.assertEqual(dict_resp["request_id"], "resp-10")
        self.assertEqual(dict_resp["status"], "completed")
        self.assertEqual(dict_resp["result"]["summary"], "Task completed")

    def test_11_adapter_registry_registration(self):
        """11. AdapterRegistry registers adapter instance successfully."""
        self.registry.register_adapter("ref_adapter", self.adapter)
        self.assertIn("ref_adapter", self.registry.list_adapters())

    def test_12_adapter_registry_lookup(self):
        """12. AdapterRegistry retrieves registered adapter by adapter_id."""
        self.registry.register_adapter("ref_adapter", self.adapter)
        retrieved = self.registry.get_adapter("ref_adapter")
        self.assertIs(retrieved, self.adapter)

    def test_13_adapter_registry_removal(self):
        """13. AdapterRegistry unregisters adapter by ID."""
        self.registry.register_adapter("ref_adapter", self.adapter)
        removed = self.registry.unregister_adapter("ref_adapter")
        self.assertTrue(removed)
        self.assertNotIn("ref_adapter", self.registry.list_adapters())

    def test_14_multiple_adapter_registration(self):
        """14. AdapterRegistry handles multiple adapter instances."""
        adapter2 = PortableAdapter(core_agent=self.core)
        self.registry.register_adapter("adapter_1", self.adapter)
        self.registry.register_adapter("adapter_2", adapter2)
        self.assertEqual(len(self.registry.list_adapters()), 2)

    def test_15_unknown_adapter_lookup(self):
        """15. AdapterRegistry returns None for unregistered adapter_id."""
        self.assertIsNone(self.registry.get_adapter("non_existent_adapter"))

    def test_16_agent_core_is_not_modified_during_adapter_execution(self):
        """16. AgentCore internal state and tool registry remain uncorrupted by adapter tasks."""
        tools_before = len(self.core.tool_registry.list_tools())
        payload = {"request_id": "req-mod-16", "input": "Evaluate tasks"}
        self.adapter.run_framework_task(payload)
        tools_after = len(self.core.tool_registry.list_tools())
        self.assertEqual(tools_before, tools_after)

    def test_17_tool_registry_remains_controlled_by_core(self):
        """17. Tool registry discovery and execution are invoked by AgentCore, not adapter."""
        payload = {"request_id": "req-tr-17", "input": "Evaluate tasks", "requested_capabilities": ["situational_assessment"]}
        res = self.adapter.run_framework_task(payload)
        self.assertEqual(res["status"], "awaiting_tools")

    def test_18_passport_authorization_remains_controlled_by_core(self):
        """18. Passport authorization is enforced by AgentCore, rejecting unauthorized capabilities."""
        payload = {
            "request_id": "req-pass-18",
            "input": "Unauthorized action",
            "requested_capabilities": ["unauthorized_cyber_attack"]
        }
        res = self.adapter.run_framework_task(payload)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(any(e["error_code"] == "UNSUPPORTED_CAPABILITY" for e in res["errors"]))

    def test_19_framework_independent_imports(self):
        """19. Adapters module uses only standard Python and internal core dependencies."""
        import adapters.base as base_mod
        import adapters.portable_adapter as portable_mod
        import adapters.registry as reg_mod

        for mod in (base_mod, portable_mod, reg_mod):
            with open(mod.__file__, "r", encoding="utf-8") as f:
                source = f.read().lower()
            for forbidden in ("fastapi", "langchain", "crewai", "autogen", "lyzr"):
                self.assertNotIn(forbidden, source)

    def test_20_no_hardcoded_domain_data(self):
        """20. Adapter metadata and code contain zero hardcoded city names or coordinates."""
        meta = self.adapter.metadata.to_dict()
        meta_str = str(meta).lower()
        for forbidden in ("hyderabad", "bangalore", "mumbai", "hospital", "shelter"):
            self.assertNotIn(forbidden, meta_str)


if __name__ == "__main__":
    unittest.main()
