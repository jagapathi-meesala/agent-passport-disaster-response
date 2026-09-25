"""
Framework-independent Agent State model and safe state machine.

Tracks session execution state, capability resolution, tool execution outputs,
and errors with explicit state transition validation.
"""

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from contracts.schemas import AgentRequest, AgentStatus, AgentError


class InvalidStateTransitionError(ValueError):
    """Exception raised when an illegal state transition is attempted."""
    def __init__(self, current_status: AgentStatus, target_status: AgentStatus):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Invalid state transition from '{current_status.value}' to '{target_status.value}'."
        )


class AgentState(BaseModel):
    """
    Framework-independent Agent State model.
    Tracks execution progress, state transitions, tool results, and errors.
    """
    request: AgentRequest = Field(..., description="Active user request.")
    status: AgentStatus = Field(default=AgentStatus.ACCEPTED, description="Current state status.")
    selected_capabilities: List[str] = Field(default_factory=list, description="Validated capabilities selected for execution.")
    selected_tools: List[str] = Field(default_factory=list, description="Registered tools selected for execution.")
    tool_results: Dict[str, Any] = Field(default_factory=dict, description="Captured tool execution outputs.")
    errors: List[AgentError] = Field(default_factory=list, description="Structured errors recorded during execution.")
    final_result: Optional[Dict[str, Any]] = Field(None, description="Final output payload.")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime execution metadata.")

    # Allowed state transition mapping
    _ALLOWED_TRANSITIONS = {
        AgentStatus.ACCEPTED: {AgentStatus.RUNNING, AgentStatus.FAILED},
        AgentStatus.RUNNING: {AgentStatus.AWAITING_TOOLS, AgentStatus.COMPLETED, AgentStatus.FAILED},
        AgentStatus.AWAITING_TOOLS: {AgentStatus.RUNNING, AgentStatus.FAILED},
        AgentStatus.COMPLETED: set(),  # Terminal state
        AgentStatus.FAILED: set(),     # Terminal state
    }

    def transition_to(self, target_status: AgentStatus) -> AgentStatus:
        """
        Safely transition the agent state to target_status.
        Raises InvalidStateTransitionError if the transition path is invalid.
        """
        allowed = self._ALLOWED_TRANSITIONS.get(self.status, set())
        if target_status not in allowed:
            error = AgentError(
                error_code="INVALID_STATE_TRANSITION",
                message=f"Cannot transition state from '{self.status.value}' to '{target_status.value}'.",
                details={"current_status": self.status.value, "target_status": target_status.value}
            )
            self.errors.append(error)
            raise InvalidStateTransitionError(self.status, target_status)

        self.status = target_status
        return self.status

    def record_error(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None) -> AgentError:
        """Record a structured error in state without raising exception."""
        err = AgentError(
            error_code=error_code,
            message=message,
            details=details or {}
        )
        self.errors.append(err)
        return err

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AgentState to dictionary."""
        return self.model_dump()

    def to_json(self) -> str:
        """Serialize AgentState to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Instantiate AgentState from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentState":
        """Instantiate AgentState from JSON string."""
        return cls(**json.loads(json_str))
