"""
Dynamic Weather Tool implementation.

Extends AbstractTool to validate runtime geographic coordinates, query configurable external
weather providers via WeatherProviderClient, and normalize raw payloads into WeatherResponse contracts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from contracts.tool_interface import AbstractTool, ToolContract
from tools.weather_schemas import WeatherRequest, WeatherResponse, WeatherLocation
from tools.weather_client import WeatherProviderClient, WeatherProviderError


class WeatherTool(AbstractTool):
    """
    Production-style Weather Tool providing dynamic weather retrieval and normalization.
    Decoupled from AI frameworks, hardcoded coordinates, or fake production data.
    """

    def __init__(self, client: Optional[WeatherProviderClient] = None):
        self.client = client or WeatherProviderClient()
        self._contract = ToolContract(
            tool_id="weather_tool",
            name="weather_tool",
            version="1.0.0",
            description="Queries operational weather metrics (temperature, humidity, precipitation, wind) for runtime geographic coordinates.",
            capability="weather_monitoring",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"}
                        },
                        "required": ["latitude", "longitude"]
                    }
                },
                "required": ["location"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "location": {"type": "object"},
                    "observed_at": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["location", "observed_at", "source"]
            },
            permissions=["weather_query"],
            enabled=True
        )

    @property
    def contract(self) -> ToolContract:
        """Return machine-readable ToolContract."""
        return self._contract

    def validate_input(self, params: Dict[str, Any]) -> bool:
        """
        Validate that runtime input contains a valid 'location' dictionary
        with latitude (-90 to 90) and longitude (-180 to 180).
        """
        if not isinstance(params, dict):
            return False

        # Support params containing 'location' directly or inside 'context'
        loc_data = params.get("location")
        if not loc_data and isinstance(params.get("context"), dict):
            loc_data = params["context"].get("location")

        if not loc_data or not isinstance(loc_data, dict):
            return False

        try:
            WeatherLocation(**loc_data)
            return True
        except Exception:
            return False

    def normalize_response(self, raw_data: Dict[str, Any], lat: float, lon: float) -> WeatherResponse:
        """
        Normalization Layer: Converts raw provider-specific JSON into standardized WeatherResponse.
        Extracts metrics when present, leaving missing provider fields as None without inventing fake data.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        temp = None
        hum = None
        precip = None
        wind_info = None
        condition = None
        observed_time = now_iso

        if isinstance(raw_data, dict):
            # 1. Parse Open-Meteo or generic current_weather block
            current = raw_data.get("current_weather") or raw_data.get("current") or {}
            if isinstance(current, dict):
                temp = current.get("temperature") or current.get("temp")
                if "windspeed" in current or "wind_speed" in current:
                    wind_speed = current.get("windspeed") or current.get("wind_speed")
                    wind_dir = current.get("winddirection") or current.get("wind_direction")
                    wind_info = {"speed": wind_speed, "direction": wind_dir}
                if "time" in current and isinstance(current["time"], str):
                    observed_time = current["time"]

            # 2. Parse hourly or secondary metrics if present
            hourly = raw_data.get("hourly")
            if isinstance(hourly, dict):
                temps = hourly.get("temperature_2m")
                if isinstance(temps, list) and len(temps) > 0 and temp is None:
                    temp = temps[0]
                hums = hourly.get("relative_humidity_2m")
                if isinstance(hums, list) and len(hums) > 0:
                    hum = hums[0]
                precips = hourly.get("precipitation")
                if isinstance(precips, list) and len(precips) > 0:
                    precip = precips[0]

        return WeatherResponse(
            location={"latitude": lat, "longitude": lon},
            observed_at=observed_time,
            temperature=float(temp) if temp is not None else None,
            humidity=float(hum) if hum is not None else None,
            precipitation=float(precip) if precip is not None else None,
            wind=wind_info,
            weather_condition=condition,
            source=self.client.service_url or "configured-weather-service",
            provider_metadata={"raw_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else []}
        )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute weather retrieval for runtime location input.
        Raises ValueError or WeatherProviderError on validation or connectivity failures.
        """
        if not self.validate_input(params):
            raise ValueError("Invalid or missing location coordinates in runtime input. Required: location {latitude, longitude}.")

        loc_data = params.get("location")
        if not loc_data and isinstance(params.get("context"), dict):
            loc_data = params["context"].get("location")

        location = WeatherLocation(**loc_data)
        raw_payload = self.client.fetch_weather(location.latitude, location.longitude)
        normalized = self.normalize_response(raw_payload, location.latitude, location.longitude)

        return normalized.to_dict()
