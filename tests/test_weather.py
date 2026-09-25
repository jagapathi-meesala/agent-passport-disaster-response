"""
Unit tests for Weather Tool, WeatherLocation validation, Provider Client, Normalization, Passport Authorization, and ToolRegistry Integration.

All API test calls use a controlled mock transport / client stub to ensure unit tests are 100% deterministic and do not depend on live internet.
"""

import unittest
from pydantic import ValidationError

from config.settings import get_settings
from contracts.tool_interface import ToolExecutionStatus
from contracts.schemas import AgentRequest, AgentStatus
from tools.weather_schemas import WeatherLocation, WeatherRequest, WeatherResponse
from tools.weather_client import WeatherProviderClient, WeatherProviderError
from tools.weather_tool import WeatherTool
from tools.base import ToolRegistry
from passport.manager import PassportManager
from core.agent import AgentCore


class MockWeatherProviderClient(WeatherProviderClient):
    """Controlled test transport for deterministic Weather Tool unit tests."""

    def __init__(self, should_fail=False, status_code=500, timeout_error=False, response_data=None):
        super().__init__(service_url="https://test-weather-service.example/v1/forecast")
        self.should_fail = should_fail
        self.status_code = status_code
        self.timeout_error = timeout_error
        self.response_data = response_data if response_data is not None else {
            "current_weather": {
                "temperature": 28.5,
                "windspeed": 12.0,
                "winddirection": 180.0,
                "time": "2026-09-25T12:00:00Z"
            },
            "hourly": {
                "relative_humidity_2m": [65.0],
                "precipitation": [0.0]
            }
        }

    def fetch_weather(self, latitude: float, longitude: float) -> dict:
        if self.timeout_error:
            raise WeatherProviderError("Timeout of 10.0s exceeded while connecting to weather provider.")
        if self.should_fail:
            raise WeatherProviderError(f"HTTP Error querying weather provider: {self.status_code}", status_code=self.status_code)
        return self.response_data


class TestWeatherSystem(unittest.TestCase):

    def setUp(self):
        self.mock_client = MockWeatherProviderClient()
        self.weather_tool = WeatherTool(client=self.mock_client)
        self.registry = ToolRegistry()
        self.passport_manager = PassportManager()
        self.passport = self.passport_manager.load_from_file("config/passport.json")

    def test_1_valid_weather_request(self):
        """1. Valid WeatherLocation and WeatherRequest instantiation."""
        loc = WeatherLocation(latitude=17.385, longitude=78.486)
        self.assertEqual(loc.latitude, 17.385)
        self.assertEqual(loc.longitude, 78.486)

        req = WeatherRequest(location=loc)
        self.assertEqual(req.location.latitude, 17.385)

    def test_2_invalid_latitude_rejection(self):
        """2. Latitude out of bounds (-90 to 90) is rejected."""
        with self.assertRaises(ValidationError):
            WeatherLocation(latitude=95.0, longitude=78.0)
        with self.assertRaises(ValidationError):
            WeatherLocation(latitude=-91.0, longitude=78.0)

    def test_3_invalid_longitude_rejection(self):
        """3. Longitude out of bounds (-180 to 180) is rejected."""
        with self.assertRaises(ValidationError):
            WeatherLocation(latitude=17.0, longitude=185.0)
        with self.assertRaises(ValidationError):
            WeatherLocation(latitude=17.0, longitude=-185.0)

    def test_4_missing_coordinates_rejection(self):
        """4. Missing coordinates fail tool input validation."""
        self.assertFalse(self.weather_tool.validate_input({}))
        self.assertFalse(self.weather_tool.validate_input({"location": {}}))
        self.assertFalse(self.weather_tool.validate_input({"location": {"latitude": 17.0}}))

    def test_5_provider_configuration_loading(self):
        """5. Provider configuration loads dynamically from settings."""
        settings = get_settings()
        client = WeatherProviderClient()
        self.assertEqual(client.service_url, settings.weather_service_url)

    def test_6_provider_timeout_error_handling(self):
        """6. Provider timeout raises WeatherProviderError."""
        timeout_client = MockWeatherProviderClient(timeout_error=True)
        tool = WeatherTool(client=timeout_client)
        with self.assertRaises(WeatherProviderError):
            tool.execute({"location": {"latitude": 15.0, "longitude": 75.0}})

    def test_7_http_error_handling(self):
        """7. HTTP status error raises WeatherProviderError with status code."""
        failing_client = MockWeatherProviderClient(should_fail=True, status_code=503)
        tool = WeatherTool(client=failing_client)
        with self.assertRaises(WeatherProviderError) as cm:
            tool.execute({"location": {"latitude": 15.0, "longitude": 75.0}})
        self.assertEqual(cm.exception.status_code, 503)

    def test_8_invalid_provider_response_handling(self):
        """8. Invalid/empty provider response handles metrics gracefully."""
        empty_client = MockWeatherProviderClient(response_data={})
        tool = WeatherTool(client=empty_client)
        result = tool.execute({"location": {"latitude": 15.0, "longitude": 75.0}})
        self.assertEqual(result["location"]["latitude"], 15.0)
        self.assertIsNone(result["temperature"])

    def test_9_weather_response_normalization(self):
        """9. Raw provider JSON is normalized to WeatherResponse contract."""
        res = self.weather_tool.normalize_response(self.mock_client.response_data, 17.385, 78.486)
        self.assertIsInstance(res, WeatherResponse)
        self.assertEqual(res.temperature, 28.5)
        self.assertEqual(res.humidity, 65.0)
        self.assertEqual(res.wind["speed"], 12.0)

    def test_10_weather_tool_contract_validation(self):
        """10. WeatherTool contract properties are valid."""
        contract = self.weather_tool.contract
        self.assertEqual(contract.tool_id, "weather_tool")
        self.assertEqual(contract.name, "weather_tool")
        self.assertEqual(contract.capability, "weather_monitoring")

    def test_11_weather_tool_registration(self):
        """11. WeatherTool registers cleanly in ToolRegistry."""
        self.registry.register_tool(self.weather_tool)
        self.assertIsNotNone(self.registry.get_tool("weather_tool"))

    def test_12_weather_tool_execution_through_registry(self):
        """12. WeatherTool executes successfully through ToolRegistry."""
        self.registry.register_tool(self.weather_tool)
        exec_res = self.registry.execute_tool(
            "weather_tool",
            {"location": {"latitude": 17.385, "longitude": 78.486}},
            passport=self.passport
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.SUCCESS)
        self.assertIsNotNone(exec_res.result)
        self.assertEqual(exec_res.result["location"]["latitude"], 17.385)

    def test_13_passport_authorization(self):
        """13. Passport checks weather capability and tool permissions."""
        self.registry.register_tool(self.weather_tool)
        exec_res = self.registry.execute_tool(
            "weather_tool",
            {"location": {"latitude": 17.385, "longitude": 78.486}},
            passport=self.passport
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.SUCCESS)

    def test_14_no_fake_weather_result_on_provider_failure(self):
        """14. Execution failure returns structured error, not fake weather metrics."""
        failing_client = MockWeatherProviderClient(should_fail=True)
        tool = WeatherTool(client=failing_client)
        self.registry.register_tool(tool)
        exec_res = self.registry.execute_tool(
            "weather_tool",
            {"location": {"latitude": 17.385, "longitude": 78.486}},
            passport=self.passport
        )
        self.assertEqual(exec_res.status, ToolExecutionStatus.EXECUTION_ERROR)
        self.assertIsNone(exec_res.result)

    def test_15_runtime_coordinates_preserved(self):
        """15. Runtime input coordinates are preserved in the response."""
        self.registry.register_tool(self.weather_tool)
        exec_res = self.registry.execute_tool(
            "weather_tool",
            {"location": {"latitude": 12.34, "longitude": 56.78}},
            passport=self.passport
        )
        self.assertEqual(exec_res.result["location"]["latitude"], 12.34)
        self.assertEqual(exec_res.result["location"]["longitude"], 56.78)

    def test_16_provider_url_configurable(self):
        """16. WeatherTool provider URL comes from client configuration."""
        client = WeatherProviderClient(service_url="https://custom-weather.service/api")
        tool = WeatherTool(client=client)
        self.assertEqual(tool.client.service_url, "https://custom-weather.service/api")

    def test_17_agent_core_weather_tool_integration(self):
        """17. AgentCore processes weather requests dynamically via WeatherTool and ToolRegistry."""
        self.registry.register_tool(self.weather_tool)
        core = AgentCore(passport_manager=self.passport_manager, tool_registry=self.registry)
        req = AgentRequest(
            request_id="req-weather-117",
            user_input="Monitor weather conditions",
            context={"location": {"latitude": 17.385, "longitude": 78.486}},
            requested_capabilities=["weather_monitoring"]
        )
        response = core.process_request(req)
        self.assertEqual(response.status, AgentStatus.COMPLETED)
        self.assertIn("weather_tool", response.used_tools)


if __name__ == "__main__":
    unittest.main()
