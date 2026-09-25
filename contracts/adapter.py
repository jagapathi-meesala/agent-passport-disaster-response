"""
Adapter contract and metadata specifications.

Provides framework-neutral Pydantic models describing framework adapter metadata and boundaries.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AdapterMetadata(BaseModel):
    """Metadata specification describing a framework/runtime adapter."""
    adapter_id: str = Field(..., description="Unique machine-readable identifier for the adapter.")
    name: str = Field(..., description="Human-readable name of the adapter.")
    version: str = Field(..., description="Semantic version string of the adapter.")
    runtime_type: str = Field(..., description="Type of runtime/framework target (e.g. 'reference', 'rest', 'event').")
    supported_input_format: str = Field(..., description="Format of incoming payload accepted by adapter (e.g. 'json_dict').")
    supported_output_format: str = Field(..., description="Format of outgoing payload produced by adapter (e.g. 'json_dict').")
    description: Optional[str] = Field(None, description="Optional explanation of adapter capability and scope.")

    @field_validator("adapter_id", "name", "version", "runtime_type")
    @classmethod
    def validate_non_empty(cls, v: str, info) -> str:
        """Enforce non-empty string fields."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must be a non-empty string.")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata instance to dictionary."""
        return self.model_dump()
