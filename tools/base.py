"""
Dynamic Tool Registry for managing disaster response operational tools.

Handles tool registration, unregistration, capability discovery, authorization checks
against Agent Passports, parameter validation, and execution results.
"""

from typing import Dict, List, Optional, Any, Set
from contracts.tool_interface import (
    AbstractTool,
    ToolContract,
    ToolSpecification,
    ToolExecutionResult,
    ToolExecutionStatus,
)
from passport.schema import AgentPassport


class ToolRegistry:
    """
    Dynamic container registry for operational tools.
    Provides registration, capability discovery, passport authorization, and safe execution.
    """

    def __init__(self):
        self._tools_by_id: Dict[str, AbstractTool] = {}
        self._tools_by_name: Dict[str, AbstractTool] = {}

    def validate_tool(self, tool: AbstractTool) -> bool:
        """Verify that a tool object correctly implements AbstractTool and has valid metadata."""
        if not isinstance(tool, AbstractTool):
            return False
        try:
            contract = tool.contract
            return bool(contract.tool_id and contract.name and contract.capability)
        except Exception:
            return False

    def register_tool(self, tool: AbstractTool) -> None:
        """
        Register a new tool instance in the registry.
        Raises ValueError if tool is invalid or if a tool with the same ID or name is already registered.
        """
        if not self.validate_tool(tool):
            raise ValueError("Invalid tool instance or malformed tool contract.")

        contract = tool.contract

        if contract.tool_id in self._tools_by_id or contract.name in self._tools_by_name:
            raise ValueError(
                f"Duplicate tool registration rejected: Tool with ID '{contract.tool_id}' or Name '{contract.name}' already exists."
            )

        self._tools_by_id[contract.tool_id] = tool
        self._tools_by_name[contract.name] = tool

    def unregister_tool(self, tool_id_or_name: str) -> bool:
        """Unregister a tool by ID or name. Returns True if removed, False if not found."""
        tool = self.get_tool(tool_id_or_name)
        if not tool:
            return False

        contract = tool.contract
        self._tools_by_id.pop(contract.tool_id, None)
        self._tools_by_name.pop(contract.name, None)
        return True

    def get_tool(self, tool_id_or_name: str) -> Optional[AbstractTool]:
        """Retrieve a registered tool instance by tool_id or name."""
        return self._tools_by_id.get(tool_id_or_name) or self._tools_by_name.get(tool_id_or_name)

    def list_tools(self, include_disabled: bool = False) -> List[ToolContract]:
        """List specifications/contracts of all registered tools."""
        unique_tools = set(self._tools_by_id.values())
        contracts = [t.contract for t in unique_tools]
        if not include_disabled:
            contracts = [c for c in contracts if c.enabled]
        return contracts

    def find_by_capability(self, capability: str, include_disabled: bool = False) -> List[AbstractTool]:
        """Discover registered tools providing the specified capability identifier."""
        unique_tools = set(self._tools_by_id.values())
        matched = []
        for tool in unique_tools:
            contract = tool.contract
            if contract.capability == capability:
                if include_disabled or contract.enabled:
                    matched.append(tool)
        return matched

    def execute_tool(
        self,
        tool_id_or_name: str,
        params: Dict[str, Any],
        passport: Optional[AgentPassport] = None
    ) -> ToolExecutionResult:
        """
        Execute a tool with full validation, authorization, and error handling.
        
        Steps:
        1. Tool Lookup
        2. Enabled Check
        3. Passport Authorization Check
        4. Input Validation
        5. Execution & Output Validation
        """
        tool = self.get_tool(tool_id_or_name)
        if not tool:
            return ToolExecutionResult(
                tool_id=tool_id_or_name,
                status=ToolExecutionStatus.UNAVAILABLE,
                result=None,
                errors=[{"error_code": "TOOL_UNAVAILABLE", "message": f"Tool '{tool_id_or_name}' is not registered."}]
            )

        contract = tool.contract

        # Check if tool is disabled
        if not contract.enabled:
            return ToolExecutionResult(
                tool_id=contract.tool_id,
                status=ToolExecutionStatus.DISABLED,
                result=None,
                errors=[{"error_code": "TOOL_DISABLED", "message": f"Tool '{contract.tool_id}' is disabled."}]
            )

        # Passport Authorization Check
        if passport is not None:
            authorized_tools = passport.tools
            if passport.allowed_tools is not None:
                authorized_tools = passport.allowed_tools

            # Check tool permission
            tool_authorized = (contract.tool_id in authorized_tools) or (contract.name in authorized_tools)
            cap_authorized = contract.capability in passport.capabilities

            if not (tool_authorized or cap_authorized):
                return ToolExecutionResult(
                    tool_id=contract.tool_id,
                    status=ToolExecutionStatus.UNAUTHORIZED,
                    result=None,
                    errors=[{
                        "error_code": "UNAUTHORIZED_TOOL_EXECUTION",
                        "message": f"Tool '{contract.tool_id}' (capability: '{contract.capability}') is not authorized under active Agent Passport."
                    }]
                )

        # Input Validation Check
        if not tool.validate_input(params):
            return ToolExecutionResult(
                tool_id=contract.tool_id,
                status=ToolExecutionStatus.VALIDATION_ERROR,
                result=None,
                errors=[{"error_code": "INPUT_VALIDATION_ERROR", "message": f"Input parameters failed validation for tool '{contract.tool_id}'."}]
            )

        # Execution Phase
        try:
            output = tool.execute(params)
        except Exception as e:
            err_msg = str(e)
            is_unconfigured = "not configured" in err_msg.lower() or "configuration" in err_msg.lower() or "unconfigured" in err_msg.lower()
            err_code = "PROVIDER_NOT_CONFIGURED" if is_unconfigured else "TOOL_EXECUTION_FAILURE"
            status = ToolExecutionStatus.UNAVAILABLE if is_unconfigured else ToolExecutionStatus.EXECUTION_ERROR
            return ToolExecutionResult(
                tool_id=contract.tool_id,
                status=status,
                result=None,
                errors=[{"error_code": err_code, "message": f"Runtime error executing tool '{contract.tool_id}': {err_msg}"}]
            )

        # Output Validation Check
        if not tool.validate_output(output):
            return ToolExecutionResult(
                tool_id=contract.tool_id,
                status=ToolExecutionStatus.VALIDATION_ERROR,
                result=output,
                errors=[{"error_code": "OUTPUT_VALIDATION_ERROR", "message": f"Output payload failed validation for tool '{contract.tool_id}'."}]
            )

        return ToolExecutionResult(
            tool_id=contract.tool_id,
            status=ToolExecutionStatus.SUCCESS,
            result=output,
            execution_metadata={"tool_version": contract.version, "capability": contract.capability}
        )
