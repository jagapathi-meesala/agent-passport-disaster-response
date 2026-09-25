"""
Framework-agnostic Core Agent engine implementation.

Implements AgentCore which validates incoming requests against the Agent Passport,
discovers registered tools via ToolRegistry, executes tools with authorization,
manages execution state, and returns structured AgentResponse models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List

from contracts.schemas import AgentRequest, AgentResponse, AgentStatus, AgentError
from contracts.tool_interface import ToolExecutionStatus
from core.state import AgentState, InvalidStateTransitionError
from core.execution import ExecutionContext
from passport.manager import PassportManager
from passport.schema import AgentPassport
from tools.base import ToolRegistry


class AbstractDisasterResponseAgent(ABC):
    """Abstract Base Class for portable disaster response agents."""

    @abstractmethod
    def initialize(self, passport_data: Dict[str, Any]) -> bool:
        """Initialize the agent instance with verified passport metadata."""
        pass

    @abstractmethod
    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a disaster response task within authorized capability limits."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Retrieve current operational status and active passport details."""
        pass


class AgentCore(AbstractDisasterResponseAgent):
    """
    Framework-independent Agent Core execution engine.
    
    Operates using injected ToolRegistry and PassportManager without hardcoded values,
    fake disaster data generation, or framework-specific dependencies.
    """

    def __init__(
        self,
        passport_manager: Optional[PassportManager] = None,
        tool_registry: Optional[ToolRegistry] = None
    ):
        self.passport_manager = passport_manager or PassportManager()
        self.tool_registry = tool_registry or ToolRegistry()
        self._active_passport: Optional[AgentPassport] = None

    def initialize(self, passport_data: Dict[str, Any]) -> bool:
        """Initialize agent by loading and binding an AgentPassport payload."""
        try:
            self._active_passport = self.passport_manager.load_from_dict(passport_data)
            return True
        except Exception:
            return False

    def load_passport(self, file_path: Optional[str] = None) -> AgentPassport:
        """Dynamically load passport from external configuration file."""
        self._active_passport = self.passport_manager.load_from_file(file_path)
        return self._active_passport

    def get_active_passport(self) -> Optional[AgentPassport]:
        """Return currently loaded passport instance, loading from file if not yet active."""
        if self._active_passport is None:
            self._active_passport = self.passport_manager.get_active_passport()
        if self._active_passport is None:
            self._active_passport = self.load_passport()
        return self._active_passport

    def get_status(self) -> Dict[str, Any]:
        """Retrieve core agent status and bound passport metadata."""
        passport = self.get_active_passport()
        return {
            "agent_core": "ready",
            "passport_loaded": passport is not None,
            "agent_id": passport.agent_id if passport else None,
            "registered_tools_count": len(self.tool_registry.list_tools())
        }

    def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        Execute the core agent processing pipeline for an incoming AgentRequest.
        
        Stages:
        1. Request Validation (handled by AgentRequest schema)
        2. Dynamic Passport Loading
        3. Capability Validation
        4. Tool Discovery & Availability Check via ToolRegistry
        5. Authorized Tool Execution / Awaiting Tools Transition
        6. Response Generation
        """
        exec_ctx = ExecutionContext()
        state = AgentState(request=request)

        try:
            # Step 1: Ensure Passport is loaded dynamically
            passport = self.get_active_passport()
            if passport is None:
                passport = self.load_passport()

            # Step 2: Transition state ACCEPTED -> RUNNING
            state.transition_to(AgentStatus.RUNNING)

            # Step 3: Validate requested capabilities against Passport
            requested_caps = request.requested_capabilities
            if requested_caps:
                for cap in requested_caps:
                    if cap not in passport.capabilities:
                        err_msg = f"Requested capability '{cap}' is not authorized under current Agent Passport capabilities."
                        state.record_error("UNSUPPORTED_CAPABILITY", err_msg, {"capability": cap})
                        state.transition_to(AgentStatus.FAILED)
                        exec_metadata = exec_ctx.finish()
                        return AgentResponse(
                            request_id=request.request_id,
                            status=AgentStatus.FAILED,
                            result=None,
                            used_capabilities=[],
                            used_tools=[],
                            execution_metadata=exec_metadata,
                            errors=state.errors
                        )
                state.selected_capabilities = requested_caps
            else:
                state.selected_capabilities = passport.capabilities.copy()

            # Step 4: Discover required tools via ToolRegistry for selected capabilities
            discovered_tools = []
            for cap in state.selected_capabilities:
                tools_for_cap = self.tool_registry.find_by_capability(cap)
                for tool in tools_for_cap:
                    if tool not in discovered_tools:
                        discovered_tools.append(tool)

            # Filter tools that are authorized in passport
            authorized_tool_names = set(passport.tools)
            if passport.allowed_tools is not None:
                authorized_tool_names = set(passport.allowed_tools)

            executable_tools = [
                t for t in discovered_tools
                if (t.contract.tool_id in authorized_tool_names or t.contract.name in authorized_tool_names or t.contract.capability in passport.capabilities)
            ]

            # If no operational tools are registered/executable for selected capabilities, transition to AWAITING_TOOLS
            if len(executable_tools) == 0 and len(state.selected_capabilities) > 0:
                state.transition_to(AgentStatus.AWAITING_TOOLS)
                exec_metadata = exec_ctx.finish()
                awaiting_result = {
                    "message": "Operational tools for selected capabilities are not currently registered in the ToolRegistry.",
                    "requested_capabilities": state.selected_capabilities,
                    "authorized_tools": passport.tools,
                    "registered_tools": [t.name for t in self.tool_registry.list_tools()]
                }
                return AgentResponse(
                    request_id=request.request_id,
                    status=AgentStatus.AWAITING_TOOLS,
                    result=awaiting_result,
                    used_capabilities=state.selected_capabilities,
                    used_tools=[],
                    execution_metadata=exec_metadata,
                    errors=state.errors
                )

            # Step 5: Execute operational tools through ToolRegistry
            executed_tools = []
            params = {"user_input": request.user_input, "context": request.context}

            for tool in executable_tools:
                tool_res = self.tool_registry.execute_tool(
                    tool_id_or_name=tool.contract.tool_id,
                    params=params,
                    passport=passport
                )
                if tool_res.status == ToolExecutionStatus.SUCCESS:
                    state.tool_results[tool.contract.name] = tool_res.result
                    executed_tools.append(tool.contract.name)
                else:
                    for err in tool_res.errors:
                        state.record_error(err.get("error_code", "TOOL_ERROR"), err.get("message", "Tool execution error"), err)

            state.selected_tools = executed_tools
            state.final_result = {
                "summary": "Core task evaluation processed.",
                "tool_outputs": state.tool_results
            }
            state.transition_to(AgentStatus.COMPLETED)
            exec_metadata = exec_ctx.finish()

            return AgentResponse(
                request_id=request.request_id,
                status=AgentStatus.COMPLETED,
                result=state.final_result,
                used_capabilities=state.selected_capabilities,
                used_tools=state.selected_tools,
                execution_metadata=exec_metadata,
                errors=state.errors
            )

        except InvalidStateTransitionError as e:
            exec_metadata = exec_ctx.finish()
            return AgentResponse(
                request_id=request.request_id,
                status=state.status,
                result=None,
                used_capabilities=state.selected_capabilities,
                used_tools=state.selected_tools,
                execution_metadata=exec_metadata,
                errors=state.errors
            )
        except Exception as e:
            err_msg = f"Unexpected execution error in AgentCore: {str(e)}"
            state.record_error("UNEXPECTED_EXECUTION_ERROR", err_msg)
            if state.status in (AgentStatus.ACCEPTED, AgentStatus.RUNNING, AgentStatus.AWAITING_TOOLS):
                state.transition_to(AgentStatus.FAILED)
            exec_metadata = exec_ctx.finish()
            return AgentResponse(
                request_id=request.request_id,
                status=AgentStatus.FAILED,
                result=None,
                used_capabilities=state.selected_capabilities,
                used_tools=state.selected_tools,
                execution_metadata=exec_metadata,
                errors=state.errors
            )

    def execute_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Adapter method processing task dictionary through process_request."""
        req_id = task_input.get("task_id") or task_input.get("request_id") or "task-default"
        user_input = task_input.get("user_input") or task_input.get("task_type") or "Evaluate disaster task"
        caps = task_input.get("requested_capabilities") or []
        context = task_input.get("payload") or task_input.get("context") or {}

        req = AgentRequest(
            request_id=req_id,
            user_input=user_input,
            context=context,
            requested_capabilities=caps
        )
        res = self.process_request(req)
        return res.to_dict()
