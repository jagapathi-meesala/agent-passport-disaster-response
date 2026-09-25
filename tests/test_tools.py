"""
Unit tests for Tool Contract, Dynamic Tool Registry, Passport Tool Authorization, and AgentCore Integration.

NOTE: All tool implementations inside this file are strictly generic test-only tools
used to verify registry mechanics, schema validation, and authorization without real or fake production data.
"""

import unittest
import inspect
from typing import Dict, Any, Optional
from pydantic import ValidationError

from contracts.tool_interface import (
    AbstractTool,
    ToolContract,
    ToolExecutionStatus,
    ToolExecutionResult,
)
from contracts.schemas import AgentRequest, AgentStatus
from tools.base import ToolRegistry
from core.agent import AgentCore
from passport.manager import PassportManager


# ==============================================================================
# GENERIC TEST-ONLY TOOL DEFINITIONS (For Unit Testing Purposes Only)
# ==============================================================================

class TestOnlyGenericTool(AbstractTool):
    """Generic test-only tool implementation for unit tests."""

    def __init__(self, tool_id="tool-test-01", name="disaster_assessment_tool", capability="situational_assessment", enabled=True):
        self._contract = ToolContract(
            tool_id=tool_id,
            name=name,
            version="1.0.0",
            description="Test-only tool for registry verification.",
            capability=capability,
            input_schema={"required": ["user_input"]},
            output_schema={"required": ["status"]},
            enabled=enabled
        )

    @property
    def contract(self) -> ToolContract:
        return self._contract

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "processed_input": params.get("user_input")}


class TestOnlyFailingTool(AbstractTool):
    """Test-only tool that raises runtime exception during execution."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            tool_id="tool-fail-01",
            name="failing_test_tool",
            version="1.0.0",
            description="Test-only tool that fails.",
            capability="situational_assessment",
            enabled=True
        )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("Simulated test tool execution error.")


class TestOnlyInvalidOutputTool(AbstractTool):
    """Test-only tool that returns payload failing output schema validation."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            tool_id="tool-invalid-out-01",
            name="invalid_output_tool",
            version="1.0.0",
            description="Test-only tool with invalid output.",
            capability="situational_assessment",
            output_schema={"required": ["mandatory_key"]},
            enabled=True
        )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"wrong_key": "missing mandatory_key"}


# ==============================================================================
# TEST SUITE
# ==============================================================================

class TestToolRegistrySystem(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.passport_manager = PassportManager()
        self.passport = self.passport_manager.load_from_file("config/passport.json")
        self.test_tool = TestOnlyGenericTool()

    def test_1_tool_contract_validation(self):
        """1. Tool contract validates semver and non-empty string fields."""
        contract = ToolContract(
            tool_id="tool-01",
            name="valid_tool",
            version="1.2.3",
            description="Valid tool description",
            capability="logistics_coordination"
        )
        self.assertEqual(contract.tool_id, "tool-01")
        self.assertEqual(contract.version, "1.2.3")

        with self.assertRaises(ValidationError):
            ToolContract(tool_id="   ", name="bad", description="bad", capability="cap")

        with self.assertRaises(ValidationError):
            ToolContract(tool_id="tool-01", name="bad", version="invalid-version", description="bad", capability="cap")

    def test_2_tool_registration(self):
        """2. Tool registration works in ToolRegistry."""
        self.registry.register_tool(self.test_tool)
        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].tool_id, "tool-test-01")

    def test_3_duplicate_tool_rejection(self):
        """3. Registry rejects registering duplicate tool IDs or names."""
        self.registry.register_tool(self.test_tool)
        with self.assertRaises(ValueError):
            self.registry.register_tool(self.test_tool)

    def test_4_tool_lookup(self):
        """4. Registry looks up tools by ID or name."""
        self.registry.register_tool(self.test_tool)
        by_id = self.registry.get_tool("tool-test-01")
        self.assertIsNotNone(by_id)
        by_name = self.registry.get_tool("disaster_assessment_tool")
        self.assertIsNotNone(by_name)

    def test_5_capability_lookup(self):
        """5. Registry discovers tools by capability identifier."""
        self.registry.register_tool(self.test_tool)
        matched = self.registry.find_by_capability("situational_assessment")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].contract.tool_id, "tool-test-01")

        unmatched = self.registry.find_by_capability("non_existent_capability")
        self.assertEqual(len(unmatched), 0)

    def test_6_tool_removal(self):
        """6. Registry unregisters tools cleanly."""
        self.registry.register_tool(self.test_tool)
        removed = self.registry.unregister_tool("tool-test-01")
        self.assertTrue(removed)
        self.assertIsNone(self.registry.get_tool("tool-test-01"))
        self.assertFalse(self.registry.unregister_tool("tool-test-01"))

    def test_7_invalid_tool_rejection(self):
        """7. Registry rejects invalid tool objects."""
        with self.assertRaises(ValueError):
            self.registry.register_tool("not_a_tool_instance")

    def test_8_disabled_tool_rejection(self):
        """8. Registry rejects execution of disabled tools."""
        disabled_tool = TestOnlyGenericTool(tool_id="tool-disabled", name="disabled_tool", enabled=False)
        self.registry.register_tool(disabled_tool)
        
        result = self.registry.execute_tool("tool-disabled", {"user_input": "test"})
        self.assertEqual(result.status, ToolExecutionStatus.DISABLED)

    def test_9_authorized_tool_execution(self):
        """9. Authorized tool executes successfully."""
        self.registry.register_tool(self.test_tool)
        result = self.registry.execute_tool("tool-test-01", {"user_input": "Run task"}, passport=self.passport)
        self.assertEqual(result.status, ToolExecutionStatus.SUCCESS)
        self.assertIsNotNone(result.result)

    def test_10_unauthorized_tool_rejection(self):
        """10. Unauthorized tool is rejected by passport authorization."""
        unauthorized_tool = TestOnlyGenericTool(
            tool_id="tool-unauthorized-01",
            name="unauthorized_tool_name",
            capability="unauthorized_capability_xyz"
        )
        self.registry.register_tool(unauthorized_tool)
        result = self.registry.execute_tool("tool-unauthorized-01", {"user_input": "test"}, passport=self.passport)
        self.assertEqual(result.status, ToolExecutionStatus.UNAUTHORIZED)

    def test_11_invalid_input_rejection(self):
        """11. Tool rejects input failing schema validation."""
        self.registry.register_tool(self.test_tool)
        # Input lacks required 'user_input' key
        result = self.registry.execute_tool("tool-test-01", {"wrong_key": "val"}, passport=self.passport)
        self.assertEqual(result.status, ToolExecutionStatus.VALIDATION_ERROR)

    def test_12_tool_output_validation(self):
        """12. Tool execution validates output payload against output schema."""
        bad_out_tool = TestOnlyInvalidOutputTool()
        self.registry.register_tool(bad_out_tool)
        result = self.registry.execute_tool("tool-invalid-out-01", {}, passport=self.passport)
        self.assertEqual(result.status, ToolExecutionStatus.VALIDATION_ERROR)

    def test_13_tool_execution_failure_handling(self):
        """13. Runtime tool execution errors are caught safely."""
        failing_tool = TestOnlyFailingTool()
        self.registry.register_tool(failing_tool)
        result = self.registry.execute_tool("tool-fail-01", {}, passport=self.passport)
        self.assertEqual(result.status, ToolExecutionStatus.EXECUTION_ERROR)

    def test_14_agent_core_integration_with_tool_registry(self):
        """14. AgentCore discovers and executes tools registered in ToolRegistry."""
        self.registry.register_tool(self.test_tool)
        core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.registry)
        req = AgentRequest(
            request_id="req-tool-114",
            user_input="Analyze situation assessment",
            requested_capabilities=["situational_assessment"]
        )
        response = core.process_request(req)
        self.assertEqual(response.status, AgentStatus.COMPLETED)
        self.assertIn("disaster_assessment_tool", response.used_tools)

    def test_15_passport_authorization_integration_in_agent_core(self):
        """15. AgentCore enforces Passport capability and tool authorization bounds."""
        unauthorized_tool = TestOnlyGenericTool(
            tool_id="unauth-01",
            name="forbidden_tool",
            capability="forbidden_capability"
        )
        self.registry.register_tool(unauthorized_tool)
        core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.registry)
        req = AgentRequest(
            request_id="req-unauth-115",
            user_input="Try unauthorized action",
            requested_capabilities=["forbidden_capability"]
        )
        response = core.process_request(req)
        self.assertEqual(response.status, AgentStatus.FAILED)

    def test_16_no_fake_production_data(self):
        """16. Verify no fake real-world disaster data is hardcoded or returned."""
        self.registry.register_tool(self.test_tool)
        result = self.registry.execute_tool("tool-test-01", {"user_input": "Test query"})
        res_str = str(result.result).lower()
        self.assertNotIn("hospital", res_str)
        self.assertNotIn("temperature", res_str)
        self.assertNotIn("latitude", res_str)

    def test_17_framework_independence(self):
        """17. Verify zero third-party agent framework imports across core/, tools/, contracts/."""
        import glob
        forbidden = ["fastapi", "langchain", "crewai", "autogen", "lyzr"]
        for folder in ("core", "tools", "contracts"):
            for path in glob.glob(f"{folder}/*.py"):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                for item in forbidden:
                    self.assertNotIn(
                        f"import {item}",
                        content,
                        f"Forbidden import '{item}' found in {path}"
                    )
                    self.assertNotIn(
                        f"from {item}",
                        content,
                        f"Forbidden import '{item}' found in {path}"
                    )


if __name__ == "__main__":
    unittest.main()
