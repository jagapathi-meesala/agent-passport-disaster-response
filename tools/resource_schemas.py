"""
Pydantic data schemas for Resource Location Tool input requests and provider-neutral responses.

Enforces strict runtime validation for coordinates, radius, and resource types
without hardcoding domain data or specific resource categories.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ResourceLocationRequest(BaseModel):
    """Validated request model for resource location queries."""
    resource_type: str = Field(..., description="Runtime resource type identifier (e.g. facility, center).")
    latitude: float = Field(..., description="Latitude coordinate in degrees (-90.0 to 90.0).")
    longitude: float = Field(..., description="Longitude coordinate in degrees (-180.0 to 180.0).")
    radius: float = Field(default=10.0, description="Query radius in kilometers or meters (must be > 0.0).")
    provider_neutral_id: Optional[str] = Field(None, description="Optional provider-neutral reference ID.")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Optional runtime filter criteria.")

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        """Enforce non-empty resource type string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field 'resource_type' must be a non-empty string.")
        return v.strip()

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Enforce valid latitude boundaries."""
        if not isinstance(v, (int, float)) or v < -90.0 or v > 90.0:
            raise ValueError(f"Latitude must be a valid number between -90.0 and 90.0 degrees. Got: {v}")
        return float(v)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Enforce valid longitude boundaries."""
        if not isinstance(v, (int, float)) or v < -180.0 or v > 180.0:
            raise ValueError(f"Longitude must be a valid number between -180.0 and 180.0 degrees. Got: {v}")
        return float(v)

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, v: float) -> float:
        """Enforce positive query radius."""
        if not isinstance(v, (int, float)) or v <= 0.0:
            raise ValueError(f"Radius must be a positive numeric value greater than 0.0. Got: {v}")
        return float(v)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ResourceLocationRequest to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceLocationRequest":
        """Instantiate ResourceLocationRequest from dictionary."""
        return cls(**data)


class ResourceLocation(BaseModel):
    """Provider-neutral representation of an individual resource location record."""
    resource_id: str = Field(..., description="Unique record or provider resource identifier.")
    name: str = Field(..., description="Name or designation of resource facility.")
    resource_type: str = Field(..., description="Category or resource type of this record.")
    latitude: Optional[float] = Field(None, description="Optional record latitude coordinate.")
    longitude: Optional[float] = Field(None, description="Optional record longitude coordinate.")
    address: Optional[str] = Field(None, description="Optional physical address or location string.")
    availability: Optional[Dict[str, Any]] = Field(None, description="Optional operational availability details.")
    capacity: Optional[Dict[str, Any]] = Field(None, description="Optional capacity or count metrics.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provider-neutral metadata.")


class ResourceLocationResponse(BaseModel):
    """Provider-neutral response container returned by ResourceLocationTool."""
    queried_location: Dict[str, float] = Field(..., description="Target query coordinates {'latitude': lat, 'longitude': lon}.")
    requested_resource_type: str = Field(..., description="Category of resource queried.")
    resources: List[ResourceLocation] = Field(default_factory=list, description="List of provider-neutral resource records.")
    observed_at: str = Field(..., description="ISO 8601 timestamp of data query.")
    source: str = Field(default="configured-resource-service", description="Identifier of external resource provider.")
    provider_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw or provider-specific response metadata.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ResourceLocationResponse to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceLocationResponse":
        """Instantiate ResourceLocationResponse from dictionary."""
        return cls(**data)
