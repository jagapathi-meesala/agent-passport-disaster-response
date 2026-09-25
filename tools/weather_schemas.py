"""
Pydantic data contracts for Weather Tool input request and output response models.

Enforces strict runtime coordinate validation without hardcoding default coordinates,
city names, or fake weather metrics.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class WeatherLocation(BaseModel):
    """Geographic location coordinates schema."""
    latitude: float = Field(..., description="Latitude coordinate in degrees (-90.0 to 90.0).")
    longitude: float = Field(..., description="Longitude coordinate in degrees (-180.0 to 180.0).")

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


class WeatherRequest(BaseModel):
    """Validated input contract for weather queries."""
    location: WeatherLocation = Field(..., description="Runtime target coordinates.")
    provider_neutral_id: Optional[str] = Field(None, description="Optional provider-neutral location reference.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize WeatherRequest to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherRequest":
        """Instantiate WeatherRequest from dictionary with validation."""
        return cls(**data)


class WeatherResponse(BaseModel):
    """Normalized output contract returned by WeatherTool."""
    location: Dict[str, float] = Field(..., description="Target query coordinates {'latitude': lat, 'longitude': lon}.")
    observed_at: str = Field(..., description="ISO 8601 timestamp of observation or forecast data.")
    temperature: Optional[float] = Field(None, description="Air temperature (Celsius).")
    humidity: Optional[float] = Field(None, description="Relative humidity percentage (0-100%).")
    precipitation: Optional[float] = Field(None, description="Precipitation amount (mm).")
    wind: Optional[Dict[str, Any]] = Field(None, description="Wind metrics {'speed': float, 'direction': float/str}.")
    weather_condition: Optional[str] = Field(None, description="Normalized condition summary (e.g. Clear, Rain, Storm).")
    source: str = Field(default="configured-weather-service", description="Identifier of the external weather data provider.")
    provider_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw or provider-specific metadata.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize WeatherResponse to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherResponse":
        """Instantiate WeatherResponse from dictionary."""
        return cls(**data)
