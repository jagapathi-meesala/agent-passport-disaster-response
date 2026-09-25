"""
Contract interface definitions for tools registered with DisasterResponseAgent.

Ensures all tools expose uniform machine-readable contracts, capability declarations,
input/output schemas, and execution interfaces without framework dependencies.
"""

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")


class ToolExecutionStatus(str, Enum):
    """Explicit status enumeration for tool execution results."""
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    UNAUTHORIZED = "unauthorized"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    EXECUTION_ERROR = "execution_error"


class ToolContract(BaseModel):
    """Machine-readable contract specifying a tool's identity, capabilities, and schemas."""
    tool_id: str = Field(..., description="Unique machine-readable tool identifier.")
    name: str = Field(..., description="Human-readable tool name.")
    version: str = Field(default="1.0.0", description="Tool semver version (e.g. '1.0.0').")
    description: str = Field(..., description="Non-empty explanation of tool capabilities.")
    capability: str = Field(..., description="Primary capability identifier provided by tool.")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for input parameter validation.")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for output payload validation.")
    permissions: List[str] = Field(default_factory=list, description="Required passport permission scopes.")
    required_permissions: List[str] = Field(default_factory=list, description="Legacy field alias for permissions.")
    enabled: bool = Field(default=True, description="Whether tool is enabled for execution.")

    @field_validator("tool_id", "name", "description", "capability")
    @classmethod
    def validate_non_empty_str(cls, v: str, info) -> str:
        """Enforce non-empty string fields."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str, info) -> str:
        """Enforce semantic versioning format X.Y.Z."""
        if not isinstance(v, str) or not SEMVER_REGEX.match(v.strip()):
            raise ValueError(f"Field '{info.field_name}' must be a valid semantic version (e.g. '1.0.0'). Got: '{v}'")
        return v.strip()


# Backward compatibility alias
ToolSpecification = ToolContract


class ToolExecutionResult(BaseModel):
    """Structured execution output produced by tool invocations."""
    tool_id: str = Field(..., description="Target tool identifier.")
    status: ToolExecutionStatus = Field(..., description="Execution outcome status.")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution payload output.")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Runtime execution metadata.")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Structured error records.")


class AbstractTool(ABC):
    """Abstract interface for all disaster response operational tools."""

    @property
    @abstractmethod
    def contract(self) -> ToolContract:
        """Return machine-readable ToolContract metadata."""
        pass

    @property
    def specification(self) -> ToolContract:
        """Backward compatibility accessor for tool contract."""
        return self.contract

    def validate_input(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters against the tool's input schema.
        Default implementation checks required keys specified in input_schema.
        """
        if not isinstance(params, dict):
            return False
        required_keys = self.contract.input_schema.get("required", [])
        for key in required_keys:
            if key not in params:
                return False
        return True

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool logic with validated runtime parameters."""
        pass

    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        Validate execution output payload against the tool's output schema.
        Default implementation checks required keys specified in output_schema.
        """
        if not isinstance(result, dict):
            return False
        required_keys = self.contract.output_schema.get("required", [])
        for key in required_keys:
            if key not in result:
                return False
        return True
