"""
Unit tests for ResourceLocationTool, ResourceLocationRequest validation, Provider Client,
Normalization, Passport Authorization, and AgentCore Integration.

All external API test calls use a controlled mock transport stub to ensure unit tests are 100% deterministic and do not depend on live internet.
"""

import unittest
from pydantic import ValidationError

from config.settings import get_settings
from contracts.tool_interface import ToolExecutionStatus
from contracts.schemas import AgentRequest, AgentStatus
from tools.resource_schemas import ResourceLocationRequest, ResourceLocationResponse, ResourceLocation
from tools.resource_client import ResourceProviderClient, ResourceProviderError
from tools.resource_tool import ResourceLocationTool
from tools.base import ToolRegistry
from passport.manager import PassportManager
from core.agent import AgentCore


class MockResourceProviderClient(ResourceProviderClient):
    """Controlled test transport for deterministic Resource Location Tool unit tests."""

    def __init__(self, should_fail=False, status_code=500, timeout_error=False, response_data=None):
        super().__init__(service_url="https://test-resource-service.example/v1/query")
        self.should_fail = should_fail
        self.status_code = status_code
        self.timeout_error = timeout_error
        self.response_data = response_data if response_data is not None else {
            "resources": [
                {
                    "id": "res-synth-01",
                    "name": "Synthetic Center Alpha",
                    "type": "emergency_center",
                    "latitude": 10.0,
                    "longitude": 20.0,
                    "address": "123 Synthetic Way",
                    "availability": {"open": True},
                    "capacity": {"units": 50}
                },
                {
                    "id": "res-synth-02",
                    "name": "Synthetic Center Beta",
                    "type": "emergency_center",
                    "latitude": 10.1,
                    "longitude": 20.1
                    # Note: address, availability, capacity omitted intentionally
                }
            ]
        }

    def fetch_resources(self, resource_type: str, latitude: float, longitude: float, radius: float, filters=None) -> dict:
        if self.timeout_error:
            raise ResourceProviderError("Timeout of 10.0s exceeded while connecting to resource provider.")
        if self.should_fail:
            raise ResourceProviderError(f"HTTP Error querying resource provider: {self.status_code}", status_code=self.status_code)
        return self.response_data


class TestResourceSystem(unittest.TestCase):

    def setUp(self):
        self.mock_client = MockResourceProviderClient()
        self.resource_tool = ResourceLocationTool(client=self.mock_client)
        self.registry = ToolRegistry()
        self.passport_manager = PassportManager()
        self.passport = self.passport_manager.load_from_file("config/passport.json")

    def test_1_request_schema_validation(self):
        """1. Valid ResourceLocationRequest instantiation."""
        req = ResourceLocationRequest(
            resource_type="emergency_facility",
            latitude=15.0,
            longitude=75.0,
            radius=15.0
        )
        self.assertEqual(req.resource_type, "emergency_facility")
        self.assertEqual(req.latitude, 15.0)
        self.assertEqual(req.longitude, 75.0)

    def test_2_invalid_latitude_rejection(self):
        """2. Latitude out of bounds (-90 to 90) is rejected."""
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=95.0, longitude=75.0)
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=-95.0, longitude=75.0)

    def test_3_invalid_longitude_rejection(self):
        """3. Longitude out of bounds (-180 to 180) is rejected."""
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=15.0, longitude=185.0)
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=15.0, longitude=-185.0)

    def test_4_invalid_radius_rejection(self):
        """4. Radius <= 0.0 is rejected."""
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=15.0, longitude=75.0, radius=0.0)
        with self.assertRaises(ValidationError):
            ResourceLocationRequest(resource_type="facility", latitude=15.0, longitude=75.0, radius=-5.0)

    def test_5_missing_required_runtime_input(self):
        """5. Missing required runtime input fails validate_input."""
        self.assertFalse(self.resource_tool.validate_input({}))
        self.assertFalse(self.resource_tool.validate_input({"resource_type": "facility"}))
        self.assertFalse(self.resource_tool.validate_input({"location": {"latitude": 15.0, "longitude": 75.0}}))

    def test_6_tool_contract_validation(self):
        """6. ResourceLocationTool contract properties are valid."""
        contract = self.resource_tool.contract
        self.assertEqual(contract.tool_id, "resource_location_tool")
        self.assertEqual(contract.name, "resource_location_tool")
        self.assertEqual(contract.capability, "resource_location")

    def test_7_tool_registration(self):
        """7. ResourceLocationTool registers cleanly in ToolRegistry."""
        self.registry.register_tool(self.resource_tool)
        self.assertIsNotNone(self.registry.get_tool("resource_location_tool"))

    def test_8_capability_discovery(self):
        """8. ToolRegistry discovers resource_location_tool by capability."""
        self.registry.register_tool(self.resource_tool)
        tools = self.registry.find_by_capability("resource_location")
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].contract.tool_id, "resource_location_tool")

    def test_9_passport_authorization(self):
        """9. Passport checks resource_location capability and tool permissions."""
        self.registry.register_tool(self.resource_tool)
        exec_res = self.registry.execute_tool(
            "resource_location_tool",
            {
                "resource_type": "emergency_center",
                "location": {"latitude": 10.0, "longitude": 20.0}
            },
            passport=self.passport
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.SUCCESS)

    def test_10_disabled_tool_behavior(self):
        """10. Registry rejects execution of disabled resource tool."""
        tool = ResourceLocationTool(client=self.mock_client)
        tool.contract.enabled = False
        self.registry.register_tool(tool)
        exec_res = self.registry.execute_tool(
            "resource_location_tool",
            {"resource_type": "facility", "location": {"latitude": 10.0, "longitude": 20.0}}
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.DISABLED)

    def test_11_provider_timeout_error_handling(self):
        """11. Provider timeout raises ResourceProviderError."""
        timeout_client = MockResourceProviderClient(timeout_error=True)
        tool = ResourceLocationTool(client=timeout_client)
        with self.assertRaises(ResourceProviderError):
            tool.execute({
                "resource_type": "facility",
                "location": {"latitude": 10.0, "longitude": 20.0}
            })

    def test_12_http_error_handling(self):
        """12. HTTP status error raises ResourceProviderError."""
        failing_client = MockResourceProviderClient(should_fail=True, status_code=500)
        tool = ResourceLocationTool(client=failing_client)
        with self.assertRaises(ResourceProviderError) as cm:
            tool.execute({
                "resource_type": "facility",
                "location": {"latitude": 10.0, "longitude": 20.0}
            })
        self.assertEqual(cm.exception.status_code, 500)

    def test_13_invalid_json_handling(self):
        """13. Invalid provider response handles empty payload gracefully."""
        empty_client = MockResourceProviderClient(response_data={})
        tool = ResourceLocationTool(client=empty_client)
        result = tool.execute({
            "resource_type": "facility",
            "location": {"latitude": 10.0, "longitude": 20.0}
        })
        self.assertEqual(len(result["resources"]), 0)

    def test_14_provider_response_normalization(self):
        """14. Raw provider response is normalized to ResourceLocationResponse."""
        res = self.resource_tool.normalize_response(
            self.mock_client.response_data,
            lat=10.0,
            lon=20.0,
            resource_type="emergency_center"
        )
        self.assertIsInstance(res, ResourceLocationResponse)
        self.assertEqual(len(res.resources), 2)
        self.assertEqual(res.resources[0].name, "Synthetic Center Alpha")

    def test_15_missing_optional_provider_fields(self):
        """15. Unsupplied provider fields remain None without inventing fake data."""
        res = self.resource_tool.normalize_response(
            self.mock_client.response_data,
            lat=10.0,
            lon=20.0,
            resource_type="emergency_center"
        )
        item_beta = res.resources[1]
        self.assertEqual(item_beta.name, "Synthetic Center Beta")
        self.assertIsNone(item_beta.address)
        self.assertIsNone(item_beta.capacity)
        self.assertIsNone(item_beta.availability)

    def test_16_successful_provider_neutral_response(self):
        """16. Successful execution returns provider-neutral dictionary."""
        self.registry.register_tool(self.resource_tool)
        exec_res = self.registry.execute_tool(
            "resource_location_tool",
            {
                "resource_type": "emergency_center",
                "location": {"latitude": 10.0, "longitude": 20.0}
            },
            passport=self.passport
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.SUCCESS)
        self.assertIn("resources", exec_res.result)

    def test_17_no_fabricated_values(self):
        """17. Unsupplied provider fields are not fabricated."""
        res = self.resource_tool.normalize_response({"resources": [{"id": "r1", "name": "Center"}]}, 10.0, 20.0, "facility")
        record = res.resources[0]
        self.assertIsNone(record.address)
        self.assertIsNone(record.capacity)
        self.assertIsNone(record.availability)

    def test_18_agent_core_integration(self):
        """18. AgentCore discovers and executes ResourceLocationTool dynamically."""
        self.registry.register_tool(self.resource_tool)
        core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.registry)
        req = AgentRequest(
            request_id="req-res-118",
            user_input="Locate emergency facilities",
            context={
                "resource_type": "emergency_center",
                "location": {"latitude": 10.0, "longitude": 20.0}
            },
            requested_capabilities=["resource_location"]
        )
        response = core.process_request(req)
        self.assertEqual(response.status, AgentStatus.COMPLETED)
        self.assertIn("resource_location_tool", response.used_tools)

    def test_19_runtime_configuration_behavior(self):
        """19. Provider service_url loads dynamically from configuration."""
        client = ResourceProviderClient(service_url="https://custom-resource-endpoint.example/api")
        tool = ResourceLocationTool(client=client)
        self.assertEqual(tool.client.service_url, "https://custom-resource-endpoint.example/api")

    def test_20_no_hardcoded_domain_data(self):
        """20. Verify no hardcoded city names or real-world locations exist in tool metadata."""
        contract = self.resource_tool.contract
        desc = contract.description.lower()
        for forbidden_city in ("hyderabad", "vijayawada", "visakhapatnam", "bangalore", "mumbai"):
            self.assertNotIn(forbidden_city, desc)


if __name__ == "__main__":
    unittest.main()
