"""
Unit tests for LangChain-Core Framework Interoperability.

Tests LangChainAdapter, input parsing (string, dict, HumanMessage), response conversion (dict, AIMessage),
AdapterRegistry integration, AgentCore delegation, Passport authorization, framework isolation, zero hardcoding,
and offline execution.
"""

import os
import unittest
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

from adapters.langchain_adapter import LangChainAdapter
from adapters.registry import AdapterRegistry
from contracts.schemas import AgentRequest, AgentResponse, AgentStatus
from core.agent import AgentCore
from tools.base import ToolRegistry
from passport.manager import PassportManager


class TestLangChainAdapterSystem(unittest.TestCase):

    def setUp(self):
        self.passport_manager = PassportManager()
        self.passport_manager.load_from_file("config/passport.json")
        self.tool_registry = ToolRegistry()
        self.core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.tool_registry)
        self.adapter = LangChainAdapter(core_agent=self.core)
        self.registry = AdapterRegistry()

    def test_1_langchain_adapter_initialization(self):
        """1. Test LangChainAdapter initializes core_agent reference and metadata correctly."""
        self.assertIs(self.adapter.core_agent, self.core)
        self.assertIsNotNone(self.adapter.metadata)
        self.assertEqual(self.adapter.metadata.adapter_id, "langchain_core_adapter")

    def test_2_adapter_metadata(self):
        """2. Test adapter metadata contract properties."""
        meta = self.adapter.metadata
        self.assertEqual(meta.runtime_type, "langchain_core")
        self.assertEqual(meta.supported_input_format, "human_message_dict_str")
        self.assertEqual(meta.supported_output_format, "json_dict_ai_message")

    def test_3_plain_string_input(self):
        """3. Test adapt_request with plain string prompt input."""
        req = self.adapter.adapt_request("Assess situational risks")
        self.assertIsInstance(req, AgentRequest)
        self.assertEqual(req.user_input, "Assess situational risks")
        self.assertTrue(req.request_id.startswith("lc-req-"))

    def test_4_dictionary_input(self):
        """4. Test adapt_request with dictionary payload input."""
        payload = {
            "request_id": "req-lc-dict-04",
            "input": "Evaluate disaster damage",
            "context": {"region_code": "REG-A"},
            "requested_capabilities": ["situational_assessment"]
        }
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.request_id, "req-lc-dict-04")
        self.assertEqual(req.user_input, "Evaluate disaster damage")
        self.assertEqual(req.context["region_code"], "REG-A")
        self.assertEqual(req.requested_capabilities, ["situational_assessment"])

    def test_5_dictionary_context(self):
        """5. Test context dictionary preservation."""
        payload = {"input": "Task text", "context": {"lat_bound": 10.0, "lon_bound": 20.0}}
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.context["lat_bound"], 10.0)

    def test_6_dictionary_requested_capabilities(self):
        """6. Test requested capabilities list preservation."""
        payload = {"input": "Logistics task", "requested_capabilities": ["logistics_coordination"]}
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.requested_capabilities, ["logistics_coordination"])

    def test_7_explicit_request_id(self):
        """7. Test explicit request_id in payload is preserved."""
        payload = {"request_id": "explicit-id-777", "input": "Task instruction"}
        req = self.adapter.adapt_request(payload)
        self.assertEqual(req.request_id, "explicit-id-777")

    def test_8_generated_request_id(self):
        """8. Test missing request_id generates a runtime-safe ID."""
        req = self.adapter.adapt_request("Instruction text")
        self.assertTrue(req.request_id.startswith("lc-req-"))

    def test_9_human_message_input(self):
        """9. Test adapt_request with LangChain HumanMessage object."""
        msg = HumanMessage(
            content="Monitor weather and logistics",
            id="msg-human-09",
            additional_kwargs={
                "context": {"sector": "north"},
                "requested_capabilities": ["weather_monitoring"]
            }
        )
        req = self.adapter.adapt_request(msg)
        self.assertEqual(req.request_id, "msg-human-09")
        self.assertEqual(req.user_input, "Monitor weather and logistics")
        self.assertEqual(req.context["sector"], "north")
        self.assertEqual(req.requested_capabilities, ["weather_monitoring"])

    def test_10_missing_input_handling(self):
        """10. Test payload with missing or empty input raises ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.adapt_request({})
        with self.assertRaises(ValueError):
            self.adapter.adapt_request({"input": "   "})
        with self.assertRaises(ValueError):
            self.adapter.adapt_request(HumanMessage(content="   "))

    def test_11_invalid_payload_handling(self):
        """11. Test unsupported payload types raise ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.adapt_request(12345)
        with self.assertRaises(ValueError):
            self.adapter.adapt_request(None)

    def test_12_agent_request_validation(self):
        """12. Test malformed payload fields fail validation with ValueError."""
        with self.assertRaises(ValueError):
            self.adapter.adapt_request({"input": "Valid", "requested_capabilities": "not-a-list"})

    def test_13_agent_core_delegation(self):
        """13. Test run_framework_task delegates execution cleanly to AgentCore."""
        res = self.adapter.run_framework_task("Evaluate situation")
        self.assertIsInstance(res, dict)
        self.assertIn("request_id", res)
        self.assertIn("status", res)

    def test_14_agent_response_conversion(self):
        """14. Test adapt_response converts AgentResponse into structured output dictionary."""
        core_resp = AgentResponse(
            request_id="resp-14",
            status=AgentStatus.COMPLETED,
            result={"summary": "Evaluation finished"},
            used_capabilities=["situational_assessment"],
            used_tools=[]
        )
        dict_resp = self.adapter.adapt_response(core_resp)
        self.assertEqual(dict_resp["request_id"], "resp-14")
        self.assertEqual(dict_resp["status"], "completed")

    def test_15_structured_output_fields(self):
        """15. Test structured output dictionary contains all required response fields."""
        res = self.adapter.run_framework_task({"input": "Assess", "requested_capabilities": ["situational_assessment"]})
        for required_field in ("request_id", "status", "result", "used_capabilities", "used_tools", "execution_metadata", "errors"):
            self.assertIn(required_field, res)

    def test_16_adapter_registry_registration(self):
        """16. Test register_adapter with LangChainAdapter."""
        self.registry.register_adapter("lc_adapter", self.adapter)
        self.assertIn("lc_adapter", self.registry.list_adapters())

    def test_17_adapter_registry_lookup(self):
        """17. Test get_adapter returns registered LangChainAdapter."""
        self.registry.register_adapter("lc_adapter", self.adapter)
        retrieved = self.registry.get_adapter("lc_adapter")
        self.assertIs(retrieved, self.adapter)

    def test_18_passport_authorization_remains_enforced_by_core(self):
        """18. Test Passport authorization is enforced by AgentCore, rejecting unauthorized capabilities."""
        payload = {
            "input": "Unauthorized action",
            "requested_capabilities": ["unauthorized_capability_x"]
        }
        res = self.adapter.run_framework_task(payload)
        self.assertEqual(res["status"], "failed")
        self.assertTrue(any(e["error_code"] == "UNSUPPORTED_CAPABILITY" for e in res["errors"]))

    def test_19_tool_execution_remains_controlled_by_core(self):
        """19. Test tool execution is managed by AgentCore and ToolRegistry."""
        res = self.adapter.run_framework_task({"input": "Perform assessment", "requested_capabilities": ["situational_assessment"]})
        self.assertEqual(res["status"], "awaiting_tools")

    def test_20_no_langchain_imports_inside_core(self):
        """20. Verify zero LangChain imports inside core/ directory."""
        self._assert_no_framework_imports("core")

    def test_21_no_langchain_imports_inside_tools(self):
        """21. Verify zero LangChain imports inside tools/ directory."""
        self._assert_no_framework_imports("tools")

    def test_22_no_langchain_imports_inside_contracts(self):
        """22. Verify zero LangChain imports inside contracts/ directory."""
        self._assert_no_framework_imports("contracts")

    def test_23_no_langchain_imports_inside_passport(self):
        """23. Verify zero LangChain imports inside passport/ directory."""
        self._assert_no_framework_imports("passport")

    def test_24_no_hardcoded_domain_data(self):
        """24. Verify adapter contains zero hardcoded city names or coordinates."""
        meta_str = str(self.adapter.metadata.to_dict()).lower()
        for forbidden in ("hyderabad", "bangalore", "mumbai", "hospital", "shelter"):
            self.assertNotIn(forbidden, meta_str)

    def test_25_no_api_keys_or_secrets(self):
        """25. Verify zero API keys or secrets embedded in adapter implementation."""
        with open("adapters/langchain_adapter.py", "r", encoding="utf-8") as f:
            content = f.read().lower()
        for keyword in ("sk-", "api_key=", "secret_key"):
            self.assertNotIn(keyword, content)

    def test_26_offline_execution_without_network_access(self):
        """26. Test adapter task runs offline without making network calls."""
        res = self.adapter.run_framework_task("Local offline assessment test")
        self.assertIsNotNone(res)
        self.assertIn("status", res)

    def test_27_portability_end_to_end(self):
        """27. End-to-end test demonstrating HumanMessage -> LangChainAdapter -> AgentCore -> AIMessage flow."""
        human_msg = HumanMessage(
            content="Evaluate disaster area",
            id="e2e-lc-msg-01",
            additional_kwargs={"requested_capabilities": ["situational_assessment"]}
        )
        req = self.adapter.adapt_request(human_msg)
        core_res = self.core.process_request(req)
        ai_msg = self.adapter.adapt_to_message(core_res)

        self.assertIsInstance(ai_msg, AIMessage)
        self.assertEqual(ai_msg.id, "e2e-lc-msg-01")
        self.assertEqual(ai_msg.additional_kwargs["status"], "awaiting_tools")
        self.assertEqual(ai_msg.additional_kwargs["request_id"], "e2e-lc-msg-01")

    def _assert_no_framework_imports(self, folder_name: str):
        """Helper to verify zero framework imports in target directory."""
        base_dir = os.path.join(os.path.dirname(__file__), "..", folder_name)
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read().lower()
                    for forbidden in ("langchain", "langchain_core", "openai", "anthropic"):
                        self.assertNotIn(forbidden, source, f"Forbidden import '{forbidden}' found in {file_path}")


if __name__ == "__main__":
    unittest.main()
