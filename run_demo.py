#!/usr/bin/env python3
"""
Standalone Competition Demonstration Runner for DisasterResponseAgent.

Demonstrates the complete portable AI agent lifecycle:
1. Dynamic Passport loading & validation
2. Behavior contract compliance & stage execution
3. Dynamic tool registration and discovery (WeatherTool, ResourceLocationTool)
4. Multi-adapter execution (Direct Core, PortableAdapter, LangChainAdapter)
5. Authorization boundary enforcement & unauthorized capability rejection
6. Framework portability verification
7. Passport trust & identity evidence JSON generation
"""

import sys
import json
from typing import Dict, Any

from passport.manager import PassportManager
from core.agent import AgentCore
from tools.base import ToolRegistry
from tools.weather_tool import WeatherTool
from tools.resource_tool import ResourceLocationTool
from tools.weather_client import WeatherProviderClient
from tools.resource_client import ResourceProviderClient
from adapters.portable_adapter import PortableAdapter
from adapters.langchain_adapter import LangChainAdapter
from verification.passport_trust_verifier import PassportTrustVerifier
from verification.portability_verifier import PortabilityVerifier


class MockWeatherClient(WeatherProviderClient):
    """Local offline mock client for deterministic weather tool demo."""
    def __init__(self):
        super().__init__(service_url="https://test-weather.example/v1")

    def fetch_weather(self, latitude: float, longitude: float) -> dict:
        return {
            "current_weather": {
                "temperature": 27.5,
                "windspeed": 14.0,
                "winddirection": 180.0,
                "time": "2026-09-25T12:00:00Z"
            },
            "hourly": {
                "relative_humidity_2m": [60.0],
                "precipitation": [0.0]
            }
        }


class MockResourceClient(ResourceProviderClient):
    """Local offline mock client for deterministic resource tool demo."""
    def __init__(self):
        super().__init__(service_url="https://test-resource.example/v1")

    def fetch_resources(self, resource_type: str, latitude: float, longitude: float, radius: float, filters=None) -> dict:
        return {
            "resources": [
                {
                    "id": "res-demo-01",
                    "name": "Emergency Medical Station Alpha",
                    "type": resource_type,
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": "Zone 1 Medical Sector",
                    "availability": {"open": True},
                    "capacity": {"units": 45}
                }
            ]
        }


def print_banner(title: str):
    """Format section header banner."""
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def main():
    """Execute complete portable agent demonstration flow."""
    print_banner("AGENT PASSPORT – PORTABLE DISASTER RESPONSE AGENT DEMO")

    # 1. Initialize Passport & Core Engine
    print("\n[1/7] Loading Agent Passport specification from 'config/passport.json'...")
    passport_manager = PassportManager()
    passport = passport_manager.load_from_file("config/passport.json")
    print(f"   ► Passport ID: {passport.agent_id}")
    print(f"   ► Agent Name: {passport.name} (v{passport.version})")
    print(f"   ► Contract Version: {passport.contract_version}")
    print(f"   ► Declared Capabilities: {passport.capabilities}")
    print(f"   ► Authorized Tools: {passport.tools}")

    # 2. Register Operational Tools
    print("\n[2/7] Initializing Dynamic ToolRegistry...")
    tool_registry = ToolRegistry()
    weather_tool = WeatherTool(client=MockWeatherClient())
    resource_tool = ResourceLocationTool(client=MockResourceClient())
    tool_registry.register_tool(weather_tool)
    tool_registry.register_tool(resource_tool)

    registered_tools = [t.tool_id for t in tool_registry.list_tools()]
    print(f"   ► Registered Tools ({len(registered_tools)}): {registered_tools}")

    # Initialize Core Agent Engine
    agent_core = AgentCore(passport_manager=passport_manager, tool_registry=tool_registry)

    # 3. Direct Core Execution
    print("\n[3/7] Path A: Executing Task via Direct AgentCore...")
    from contracts.schemas import AgentRequest
    req_direct = AgentRequest(
        request_id="demo-req-direct-01",
        user_input="Assess weather metrics for target location",
        context={"location": {"latitude": 15.5, "longitude": 75.5}},
        requested_capabilities=["weather_monitoring"]
    )
    resp_direct = agent_core.process_request(req_direct)
    print(f"   ► Status: {resp_direct.status.value}")
    print(f"   ► Used Capabilities: {resp_direct.used_capabilities}")
    print(f"   ► Used Tools: {resp_direct.used_tools}")

    # 4. Portable Reference Adapter Execution
    print("\n[4/7] Path B: Executing Task via PortableAdapter (Generic Dictionary Payload)...")
    portable_adapter = PortableAdapter(core_agent=agent_core)
    payload_portable = {
        "request_id": "demo-req-portable-02",
        "input": "Locate medical emergency facilities",
        "context": {
            "resource_type": "medical_facility",
            "location": {"latitude": 15.5, "longitude": 75.5},
            "radius": 10.0
        },
        "requested_capabilities": ["resource_location"]
    }
    resp_portable = portable_adapter.run_framework_task(payload_portable)
    print(f"   ► Status: {resp_portable['status']}")
    print(f"   ► Used Capabilities: {resp_portable['used_capabilities']}")
    print(f"   ► Used Tools: {resp_portable['used_tools']}")

    # 5. LangChain Framework Adapter Execution
    print("\n[5/7] Path C: Executing Task via LangChainAdapter (LangChain HumanMessage / Payload)...")
    langchain_adapter = LangChainAdapter(core_agent=agent_core)
    payload_langchain = {
        "request_id": "demo-req-langchain-03",
        "input": "Evaluate weather conditions and risks",
        "context": {"location": {"latitude": 15.5, "longitude": 75.5}},
        "requested_capabilities": ["weather_monitoring"]
    }
    resp_langchain = langchain_adapter.run_framework_task(payload_langchain)
    print(f"   ► Status: {resp_langchain['status']}")
    print(f"   ► Used Capabilities: {resp_langchain['used_capabilities']}")
    print(f"   ► Used Tools: {resp_langchain['used_tools']}")

    # 6. Passport Authorization & Unauthorized Capability Rejection Test
    print("\n[6/7] Testing Passport Authorization Boundaries (Unauthorized Capability Rejection)...")
    unauth_payload = {
        "request_id": "demo-req-unauth-04",
        "input": "Attempt unauthorized cyber override action",
        "requested_capabilities": ["unauthorized_cyber_attack"]
    }
    res_unauth = portable_adapter.run_framework_task(unauth_payload)
    print(f"   ► Rejection Status: {res_unauth['status']} (Expected: 'failed')")
    print(f"   ► Recorded Errors: {[e['error_code'] for e in res_unauth['errors']]}")

    # 7. Automated Verifications & Evidence Export
    print("\n[7/7] Running Portability & Passport Trust Verification Engines...")
    trust_verifier = PassportTrustVerifier()
    trust_result = trust_verifier.verify_trust(passport, agent_core)

    portability_verifier = PortabilityVerifier()
    portability_result = portability_verifier.run_full_verification(agent_core)

    print("\n" + "-" * 75)
    print("  MACHINE-READABLE EVIDENCE SUMMARY")
    print("-" * 75)
    print(f"  Passport Trust Verification: {'PASSED' if trust_result.is_valid else 'FAILED'}")
    print(f"   └─ Agent ID: {trust_result.agent_id}")
    print(f"   └─ Semver Compliance: {trust_result.schema_integrity_valid}")
    print(f"   └─ Contract Version Match ({trust_result.contract_version}): {trust_result.contract_version_matching}")
    print(f"   └─ Cross-Adapter Identity Invariance: {trust_result.adapter_identity_consistent}")
    print(f"   └─ Unauthorized Rejection Passed: {trust_result.unauthorized_capability_rejection_passed}")

    print(f"\n  Framework Portability Verification: {'PASSED' if portability_result.is_valid else 'FAILED'}")
    print(f"   └─ Paths Tested: {portability_result.execution_paths_tested}")
    print(f"   └─ Semantic Status Match: {portability_result.status_match}")
    print(f"   └─ Capability Match: {portability_result.capabilities_match}")
    print(f"   └─ Tool Match: {portability_result.tools_match}")
    print(f"   └─ Framework Isolation Audit: {portability_result.framework_isolation_passed}")
    print(f"   └─ Zero-Hardcoding Audit: {portability_result.hardcoding_audit_passed}")

    overall_success = trust_result.is_valid and portability_result.is_valid

    print("\n" + "=" * 75)
    print(f"  OVERALL DEMO RESULT: {'SUCCESS (ALL 7 LIFECYCLE STAGES VERIFIED)' if overall_success else 'FAILURE'}")
    print("=" * 75 + "\n")

    if not overall_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
