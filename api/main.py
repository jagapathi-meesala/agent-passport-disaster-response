"""
FastAPI Server Entrypoint for DisasterResponseAgent.

Exposes REST endpoints for status, health, dynamic Agent Passport metadata,
registered tools, multi-adapter execution, and automated verification suites.
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.settings import get_settings
from passport.manager import PassportManager
from passport.schema import AgentPassport
from core.agent import AgentCore
from tools.base import ToolRegistry
from tools.weather_tool import WeatherTool
from tools.resource_tool import ResourceLocationTool
from adapters.portable_adapter import PortableAdapter
from adapters.langchain_adapter import LangChainAdapter
from verification.passport_trust_verifier import PassportTrustVerifier
from verification.portability_verifier import PortabilityVerifier


app = FastAPI(
    title="Agent Passport – Disaster Response Agent API",
    description="REST API for portable disaster response agent lifecycle, tool registry, multi-adapter execution, and verification.",
    version="1.0.0",
)

# Configure CORS middleware for local development origins (including file:// and dev servers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "null",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize application components
settings = get_settings()
passport_manager = PassportManager()
passport_file = settings.passport_file_path or "config/passport.json"
active_passport = passport_manager.load_from_file(passport_file)

tool_registry = ToolRegistry()
tool_registry.register_tool(WeatherTool())
tool_registry.register_tool(ResourceLocationTool())

agent_core = AgentCore(passport_manager=passport_manager, tool_registry=tool_registry)


class ExecuteTaskRequest(BaseModel):
    """Payload schema for task execution API."""
    request_id: Optional[str] = Field(None, description="Optional request identifier.")
    user_input: str = Field(..., description="User instruction or command string.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Runtime execution context.")
    requested_capabilities: List[str] = Field(default_factory=list, description="List of requested capability identifiers.")
    adapter_type: str = Field("direct_core", description="Target execution path: 'direct_core', 'portable', or 'langchain'.")


@app.get("/")
def read_root():
    """Root endpoint returning basic runtime information."""
    return {
        "service": "DisasterResponseAgent API",
        "environment": settings.environment or "runtime",
        "status": "ready"
    }


@app.get("/health")
def health_check():
    """Health status check endpoint."""
    return {"status": "ok"}


@app.get("/passport")
def get_passport():
    """Read-only endpoint dynamically loading and returning active Agent Passport metadata."""
    try:
        passport = passport_manager.load_from_file(settings.passport_file_path or "config/passport.json")
        return passport.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load agent passport: {str(e)}")


@app.get("/tools")
def list_tools():
    """Dynamically list all registered tools in the ToolRegistry and their contracts."""
    tools_data = []
    for contract in tool_registry.list_tools():
        tools_data.append({
            "tool_id": contract.tool_id,
            "name": contract.name,
            "capability": contract.capability,
            "description": contract.description,
            "enabled": contract.enabled,
            "input_schema": contract.input_schema,
            "output_schema": contract.output_schema,
            "inputs_schema": contract.input_schema,
            "outputs_schema": contract.output_schema
        })
    return {"tools": tools_data, "count": len(tools_data)}


@app.post("/execute")
def execute_task(payload: ExecuteTaskRequest):
    """
    Execute a disaster response task via Direct Core, PortableAdapter, or LangChainAdapter.
    """
    adapter_choice = payload.adapter_type.lower().strip()
    exec_payload = {
        "user_input": payload.user_input,
        "context": payload.context,
        "requested_capabilities": payload.requested_capabilities
    }
    if payload.request_id:
        exec_payload["request_id"] = payload.request_id

    try:
        if adapter_choice in ("direct_core", "core"):
            from contracts.schemas import AgentRequest
            req = AgentRequest(
                request_id=payload.request_id or f"api-req-{id(payload)}",
                user_input=payload.user_input,
                context=payload.context,
                requested_capabilities=payload.requested_capabilities
            )
            response = agent_core.process_request(req)
            return response.to_dict()

        elif adapter_choice in ("portable", "portable_adapter"):
            adapter = PortableAdapter(core_agent=agent_core)
            return adapter.run_framework_task(exec_payload)

        elif adapter_choice in ("langchain", "langchain_adapter"):
            adapter = LangChainAdapter(core_agent=agent_core)
            return adapter.run_framework_task(exec_payload)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid adapter_type '{payload.adapter_type}'. Supported: 'direct_core', 'portable', 'langchain'."
            )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")


@app.post("/verify/trust")
def verify_passport_trust():
    """Run Passport Trust & Identity Verification engine and return JSON result."""
    try:
        current_passport = passport_manager.get_active_passport() or passport_manager.load_from_file(settings.passport_file_path or "config/passport.json")
        verifier = PassportTrustVerifier()
        trust_result = verifier.verify_trust(current_passport, agent_core)
        return trust_result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport trust verification failed: {str(e)}")


@app.post("/verify/portability")
def verify_portability():
    """Run Portability Verification engine across all execution entry points."""
    try:
        verifier = PortabilityVerifier()
        portability_result = verifier.run_full_verification(agent_core)
        return portability_result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portability verification failed: {str(e)}")
