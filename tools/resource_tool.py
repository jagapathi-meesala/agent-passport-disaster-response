"""
Dynamic Resource Location Tool implementation.

Extends AbstractTool to validate runtime geographic coordinates and resource types,
query external resource providers via ResourceProviderClient, and normalize raw payloads
into provider-neutral ResourceLocationResponse models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from contracts.tool_interface import AbstractTool, ToolContract
from tools.resource_schemas import (
    ResourceLocationRequest,
    ResourceLocationResponse,
    ResourceLocation,
)
from tools.resource_client import ResourceProviderClient, ResourceProviderError


class ResourceLocationTool(AbstractTool):
    """
    Configurable Resource and Location Information Tool providing provider-neutral
    resource retrieval and normalization.
    """

    def __init__(self, client: Optional[ResourceProviderClient] = None):
        self.client = client or ResourceProviderClient()
        self._contract = ToolContract(
            tool_id="resource_location_tool",
            name="resource_location_tool",
            version="1.0.0",
            description="A configurable resource and location information tool that retrieves provider-neutral resource information using runtime location and resource-type inputs.",
            capability="resource_location",
            input_schema={
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"}
                        },
                        "required": ["latitude", "longitude"]
                    },
                    "radius": {"type": "number"}
                },
                "required": ["resource_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "queried_location": {"type": "object"},
                    "requested_resource_type": {"type": "string"},
                    "resources": {"type": "array"},
                    "observed_at": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["queried_location", "requested_resource_type", "resources", "observed_at", "source"]
            },
            permissions=["resource_query"],
            enabled=True
        )

    @property
    def contract(self) -> ToolContract:
        """Return machine-readable ToolContract."""
        return self._contract

    def _extract_request_params(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract resource_type, location, radius, and filters from params or context."""
        if not isinstance(params, dict):
            return None

        # Check direct params
        res_type = params.get("resource_type")
        loc_data = params.get("location")
        radius = params.get("radius", 10.0)
        p_id = params.get("provider_neutral_id")
        filters = params.get("filters", {})

        # Fallback check inside context dictionary
        if (not res_type or not loc_data) and isinstance(params.get("context"), dict):
            ctx = params["context"]
            if not res_type:
                res_type = ctx.get("resource_type")
            if not loc_data:
                loc_data = ctx.get("location")
            if "radius" in ctx:
                radius = ctx["radius"]
            if "filters" in ctx:
                filters = ctx["filters"]

        if not res_type or not loc_data or not isinstance(loc_data, dict):
            return None

        return {
            "resource_type": res_type,
            "latitude": loc_data.get("latitude"),
            "longitude": loc_data.get("longitude"),
            "radius": radius,
            "provider_neutral_id": p_id,
            "filters": filters
        }

    def validate_input(self, params: Dict[str, Any]) -> bool:
        """
        Validate runtime input parameters against ResourceLocationRequest schema.
        Requires valid resource_type, latitude (-90 to 90), longitude (-180 to 180), and radius (> 0.0).
        """
        extracted = self._extract_request_params(params)
        if not extracted:
            return False

        try:
            ResourceLocationRequest(
                resource_type=str(extracted["resource_type"]),
                latitude=float(extracted["latitude"]),
                longitude=float(extracted["longitude"]),
                radius=float(extracted["radius"]),
                provider_neutral_id=extracted.get("provider_neutral_id"),
                filters=extracted.get("filters", {})
            )
            return True
        except Exception:
            return False

    def normalize_response(
        self,
        raw_data: Dict[str, Any],
        lat: float,
        lon: float,
        resource_type: str
    ) -> ResourceLocationResponse:
        """
        Normalization Layer: Converts raw provider JSON into standardized ResourceLocationResponse.
        Extracts resource records safely, keeping missing optional fields as None without fabricating data.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        records: List[ResourceLocation] = []

        raw_list = None
        if isinstance(raw_data, list):
            raw_list = raw_data
        elif isinstance(raw_data, dict):
            raw_list = (
                raw_data.get("resources")
                or raw_data.get("results")
                or raw_data.get("facilities")
                or raw_data.get("data")
            )

        if isinstance(raw_list, list):
            for item in raw_list:
                if isinstance(item, dict):
                    r_id = str(item.get("resource_id") or item.get("id") or f"rec-{len(records)+1}")
                    r_name = str(item.get("name") or item.get("title") or f"Resource Item {len(records)+1}")
                    r_type = str(item.get("resource_type") or item.get("type") or resource_type)

                    r_lat = item.get("latitude") or item.get("lat")
                    r_lon = item.get("longitude") or item.get("lon") or item.get("lng")

                    record = ResourceLocation(
                        resource_id=r_id,
                        name=r_name,
                        resource_type=r_type,
                        latitude=float(r_lat) if r_lat is not None else None,
                        longitude=float(r_lon) if r_lon is not None else None,
                        address=item.get("address"),
                        availability=item.get("availability") if isinstance(item.get("availability"), dict) else None,
                        capacity=item.get("capacity") if isinstance(item.get("capacity"), dict) else None,
                        metadata={k: v for k, v in item.items() if k not in ("id", "resource_id", "name", "type", "resource_type", "latitude", "longitude", "address")}
                    )
                    records.append(record)

        return ResourceLocationResponse(
            queried_location={"latitude": lat, "longitude": lon},
            requested_resource_type=resource_type,
            resources=records,
            observed_at=now_iso,
            source=self.client.service_url or "configured-resource-service",
            provider_metadata={"raw_record_count": len(records), "raw_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else []}
        )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute resource query for runtime location and resource-type inputs.
        Raises ValueError or ResourceProviderError on validation or connectivity failures.
        """
        if not self.validate_input(params):
            raise ValueError("Invalid or missing parameters in runtime input. Required: resource_type, location {latitude, longitude}.")

        extracted = self._extract_request_params(params)
        req = ResourceLocationRequest(
            resource_type=str(extracted["resource_type"]),
            latitude=float(extracted["latitude"]),
            longitude=float(extracted["longitude"]),
            radius=float(extracted["radius"]),
            provider_neutral_id=extracted.get("provider_neutral_id"),
            filters=extracted.get("filters", {})
        )

        raw_payload = self.client.fetch_resources(
            resource_type=req.resource_type,
            latitude=req.latitude,
            longitude=req.longitude,
            radius=req.radius,
            filters=req.filters
        )

        normalized = self.normalize_response(
            raw_data=raw_payload,
            lat=req.latitude,
            lon=req.longitude,
            resource_type=req.resource_type
        )

        return normalized.to_dict()
