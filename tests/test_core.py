"""
Unit tests for Framework-Independent Agent Core, state transitions, schemas, and behavior contracts.
"""

import unittest
import json
import inspect
from pydantic import ValidationError

from contracts.schemas import AgentRequest, AgentResponse, AgentStatus
from contracts.behavior import BehaviorContract, LifecycleStage
from core.state import AgentState, InvalidStateTransitionError
from core.execution import ExecutionContext
from core.agent import AgentCore
from passport.manager import PassportManager
from tools.base import ToolRegistry


class TestAgentCoreSystem(unittest.TestCase):

    def setUp(self):
        self.passport_manager = PassportManager()
        self.passport_manager.load_from_file("config/passport.json")
        self.tool_registry = ToolRegistry()
        self.core = AgentCore(
            passport_manager=self.passport_manager,
            tool_registry=self.tool_registry
        )

    def test_1_agent_core_initialization(self):
        """1. AgentCore initializes successfully with a valid passport."""
        status = self.core.get_status()
        self.assertEqual(status["agent_core"], "ready")
        self.assertTrue(status["passport_loaded"])
        self.assertEqual(status["agent_id"], "disaster-response-agent-01")

    def test_2_valid_agent_request_accepted(self):
        """2. Valid AgentRequest is accepted."""
        req = AgentRequest(
            request_id="req-valid-101",
            user_input="Analyze situation assessment request.",
            context={"session": "test-session"},
            requested_capabilities=["situational_assessment"]
        )
        self.assertEqual(req.request_id, "req-valid-101")
        self.assertEqual(req.user_input, "Analyze situation assessment request.")

    def test_3_empty_user_input_rejected(self):
        """3. Empty user_input is rejected with ValidationError."""
        with self.assertRaises(ValidationError):
            AgentRequest(request_id="req-102", user_input="   ")

    def test_4_invalid_request_id_rejected(self):
        """4. Invalid (empty) request_id is rejected with ValidationError."""
        with self.assertRaises(ValidationError):
            AgentRequest(request_id="", user_input="Valid input text.")

    def test_5_unsupported_capability_rejected(self):
        """5. Unsupported capability is rejected and sets status = FAILED."""
        req = AgentRequest(
            request_id="req-unsupported-105",
            user_input="Perform unauthorized action.",
            requested_capabilities=["unauthorized_capability_xyz"]
        )
        response = self.core.process_request(req)
        self.assertEqual(response.status, AgentStatus.FAILED)
        self.assertTrue(len(response.errors) > 0)
        self.assertEqual(response.errors[0].error_code, "UNSUPPORTED_CAPABILITY")

    def test_6_missing_tool_produces_awaiting_tools(self):
        """6. Missing tool produces status = awaiting_tools."""
        req = AgentRequest(
            request_id="req-awaiting-106",
            user_input="Request assessment capability without registered operational tool.",
            requested_capabilities=["situational_assessment"]
        )
        response = self.core.process_request(req)
        self.assertEqual(response.status, AgentStatus.AWAITING_TOOLS)
        self.assertIsNotNone(response.result)
        self.assertIn("message", response.result)

    def test_7_agent_state_valid_transitions(self):
        """7. AgentState transitions correctly through valid states."""
        req = AgentRequest(request_id="req-state-107", user_input="Valid task.")
        state = AgentState(request=req)
        self.assertEqual(state.status, AgentStatus.ACCEPTED)
        
        state.transition_to(AgentStatus.RUNNING)
        self.assertEqual(state.status, AgentStatus.RUNNING)

        state.transition_to(AgentStatus.COMPLETED)
        self.assertEqual(state.status, AgentStatus.COMPLETED)

    def test_8_invalid_state_transition_handled(self):
        """8. Invalid state transition raises InvalidStateTransitionError."""
        req = AgentRequest(request_id="req-state-108", user_input="Valid task.")
        state = AgentState(request=req)
        
        with self.assertRaises(InvalidStateTransitionError):
            state.transition_to(AgentStatus.COMPLETED)  # Cannot jump ACCEPTED -> COMPLETED

    def test_9_agent_response_serialization(self):
        """9. AgentResponse serializes to JSON cleanly."""
        res = AgentResponse(
            request_id="req-res-109",
            status=AgentStatus.COMPLETED,
            result={"output": "test"},
            used_capabilities=["situational_assessment"]
        )
        json_str = res.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn("req-res-109", json_str)

        deserialized = AgentResponse.from_json(json_str)
        self.assertEqual(deserialized.request_id, "req-res-109")
        self.assertEqual(deserialized.status, AgentStatus.COMPLETED)

    def test_10_passport_loaded_dynamically(self):
        """10. Passport is loaded dynamically by AgentCore."""
        core_fresh = AgentCore()
        passport = core_fresh.get_active_passport()
        self.assertIsNotNone(passport)
        self.assertEqual(passport.agent_id, "disaster-response-agent-01")

    def test_11_framework_independence_of_core(self):
        """11. Verify AgentCore source files contain NO framework imports."""
        import core.agent
        import core.execution
        import core.state

        for module in (core.agent, core.execution, core.state):
            source = inspect.getsource(module)
            for forbidden in ("fastapi", "langchain", "crewai", "autogen", "lyzr"):
                self.assertNotIn(
                    f"import {forbidden}",
                    source,
                    f"Forbidden import '{forbidden}' found in {module.__name__}!"
                )
                self.assertNotIn(
                    f"from {forbidden}",
                    source,
                    f"Forbidden import '{forbidden}' found in {module.__name__}!"
                )

    def test_12_no_fake_disaster_result_when_tools_unavailable(self):
        """12. No fake disaster result is returned when operational tools are missing."""
        req = AgentRequest(
            request_id="req-no-fake-112",
            user_input="Assess flood damage in region X",
            requested_capabilities=["situational_assessment"]
        )
        response = self.core.process_request(req)
        self.assertEqual(response.status, AgentStatus.AWAITING_TOOLS)
        # Ensure result does NOT contain fake hospital/weather/coordinate values
        res_str = json.dumps(response.result)
        self.assertNotIn("hospital", res_str.lower())
        self.assertNotIn("temperature", res_str.lower())
        self.assertNotIn("latitude", res_str.lower())

    def test_13_runtime_execution_metadata_generated_dynamically(self):
        """13. Runtime execution metadata is generated dynamically."""
        ctx = ExecutionContext()
        self.assertTrue(ctx.execution_id.startswith("exec-"))
        self.assertIn("T", ctx.start_time)  # ISO 8601 format check
        
        meta = ctx.finish()
        self.assertIsNotNone(meta["end_time"])
        self.assertGreaterEqual(meta["duration_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
