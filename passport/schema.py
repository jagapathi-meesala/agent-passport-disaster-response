"""
Agent Passport Schema definition and validation rules.

Defines the structure of the machine-readable Agent Passport, specifying identity,
capabilities, versioning contracts, input/output types, authorized tools, and cryptographic metadata.
"""

import re
import json
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")


class AgentPassport(BaseModel):
    """Verifiable credential specification and identity definition for DisasterResponseAgent."""
    passport_version: str = Field(..., description="Passport specification semver version (e.g. '1.0.0').")
    agent_id: str = Field(..., description="Unique non-empty agent identifier.")
    name: str = Field(..., description="Human-readable agent instance name.")
    version: str = Field(..., description="Agent implementation semver version (e.g. '1.0.0').")
    description: str = Field(..., description="Non-empty description of agent role and operational scope.")
    capabilities: List[str] = Field(..., description="List of unique capability identifiers.")
    input_types: List[str] = Field(..., description="List of accepted input data types.")
    output_types: List[str] = Field(..., description="List of produced output data types.")
    tools: List[str] = Field(default_factory=list, description="List of unique authorized tool names.")
    contract_version: str = Field(..., description="Target contract specification semver version.")

    # Optional metadata & cryptographic signature fields
    issuer_id: Optional[str] = Field(None, description="Identifier of issuing authority.")
    issue_timestamp: Optional[str] = Field(None, description="ISO timestamp of issuance.")
    expiration_timestamp: Optional[str] = Field(None, description="Optional expiration timestamp.")
    allowed_tools: Optional[List[str]] = Field(None, description="Permitted tool identifiers.")
    allowed_scopes: Optional[List[str]] = Field(None, description="Operational scope boundaries.")
    signature: Optional[str] = Field(None, description="Cryptographic signature verifying authenticity.")

    @field_validator("passport_version", "version", "contract_version")
    @classmethod
    def validate_semver(cls, v: str, info) -> str:
        """Enforce semantic versioning format X.Y.Z."""
        if not isinstance(v, str) or not SEMVER_REGEX.match(v.strip()):
            raise ValueError(f"Field '{info.field_name}' must be a valid semantic version (e.g. '1.0.0'). Got: '{v}'")
        return v.strip()

    @field_validator("agent_id", "name", "description")
    @classmethod
    def validate_non_empty_string(cls, v: str, info) -> str:
        """Enforce non-empty string fields."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

    @field_validator("capabilities", "input_types", "output_types")
    @classmethod
    def validate_non_empty_unique_list(cls, v: List[str], info) -> List[str]:
        """Enforce non-empty lists with unique string items."""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError(f"Field '{info.field_name}' must be a non-empty list.")
        seen = set()
        cleaned = []
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Items in '{info.field_name}' must be non-empty strings.")
            s_item = item.strip()
            if s_item in seen:
                raise ValueError(f"Field '{info.field_name}' contains duplicate item: '{s_item}'.")
            seen.add(s_item)
            cleaned.append(s_item)
        return cleaned

    @field_validator("tools")
    @classmethod
    def validate_unique_tools_list(cls, v: List[str], info) -> List[str]:
        """Enforce list with unique tool names."""
        if not isinstance(v, list):
            raise ValueError(f"Field '{info.field_name}' must be a list.")
        seen = set()
        cleaned = []
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Items in '{info.field_name}' must be non-empty strings.")
            s_item = item.strip()
            if s_item in seen:
                raise ValueError(f"Field '{info.field_name}' contains duplicate tool name: '{s_item}'.")
            seen.add(s_item)
            cleaned.append(s_item)
        return cleaned

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AgentPassport instance to dictionary."""
        return self.model_dump()

    def to_json(self) -> str:
        """Serialize AgentPassport instance to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPassport":
        """Instantiate AgentPassport from dictionary with validation."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentPassport":
        """Instantiate AgentPassport from JSON string with validation."""
        data = json.loads(json_str)
        return cls(**data)
