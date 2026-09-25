"""
Standard data schemas for agent request, response, and error contracts.

Uses Pydantic models for strict data validation without hardcoded business values.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AgentStatus(str, Enum):
    """Explicit status enumeration for agent execution lifecycle."""
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    AWAITING_TOOLS = "awaiting_tools"
    FAILED = "failed"


class AgentError(BaseModel):
    """Structured error payload schema."""
    error_code: str = Field(..., description="Machine-readable error category or code.")
    message: str = Field(..., description="Human-readable explanation of error condition.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context or parameter details.")


class AgentRequest(BaseModel):
    """Validated user request contract submitted to the agent core."""
    request_id: str = Field(..., description="Unique non-empty request identifier.")
    user_input: str = Field(..., description="Non-empty user instruction or command text.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional runtime context metadata.")
    requested_capabilities: List[str] = Field(default_factory=list, description="Optional requested capabilities.")

    @field_validator("request_id", "user_input")
    @classmethod
    def validate_non_empty_str(cls, v: str, info) -> str:
        """Enforce non-empty string fields."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

    @field_validator("requested_capabilities")
    @classmethod
    def validate_capabilities_list(cls, v: List[str], info) -> List[str]:
        """Enforce unique string items in requested capabilities."""
        if not isinstance(v, list):
            raise ValueError("requested_capabilities must be a list.")
        seen = set()
        cleaned = []
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Capability items must be non-empty strings.")
            s_item = item.strip()
            if s_item in seen:
                raise ValueError(f"Duplicate capability requested: '{s_item}'.")
            seen.add(s_item)
            cleaned.append(s_item)
        return cleaned

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AgentRequest instance to dictionary."""
        return self.model_dump()

    def to_json(self) -> str:
        """Serialize AgentRequest instance to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRequest":
        """Instantiate AgentRequest from dictionary with validation."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentRequest":
        """Instantiate AgentRequest from JSON string with validation."""
        return cls(**json.loads(json_str))


class AgentResponse(BaseModel):
    """Validated response contract produced by the agent core."""
    request_id: str = Field(..., description="Matching identifier of original request.")
    status: AgentStatus = Field(..., description="Current operational status enum value.")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution output dictionary when available.")
    used_capabilities: List[str] = Field(default_factory=list, description="List of capabilities exercised.")
    used_tools: List[str] = Field(default_factory=list, description="List of tool names invoked.")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Dynamic execution context metadata.")
    errors: List[AgentError] = Field(default_factory=list, description="Structured error records.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AgentResponse instance to dictionary."""
        return self.model_dump()

    def to_json(self) -> str:
        """Serialize AgentResponse instance to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """Instantiate AgentResponse from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentResponse":
        """Instantiate AgentResponse from JSON string."""
        return cls(**json.loads(json_str))


# Backward compatibility schemas
class AgentTaskRequest(BaseModel):
    """Legacy task request contract."""
    task_id: str = Field(..., description="Unique identifier for the disaster response task.")
    task_type: str = Field(..., description="Category or scope of task (e.g. logistics, assessment).")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dynamic runtime task parameters.")


class AgentTaskResponse(BaseModel):
    """Legacy task response contract."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
