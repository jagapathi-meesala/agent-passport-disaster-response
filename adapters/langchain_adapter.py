"""
LangChain-Core Framework Adapter implementation.

Provides a clean translation boundary connecting LangChain messages, prompt strings,
or dictionary payloads to standard AgentRequest and AgentResponse schemas.

Delegates execution strictly to AgentCore without embedding LLM logic, tool execution,
passport authorization, or state machine transitions inside the adapter.
"""

import uuid
from typing import Any, Dict, Optional, Union
from pydantic import ValidationError

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from adapters.base import AbstractFrameworkAdapter
from core.agent import AgentCore
from contracts.schemas import AgentRequest, AgentResponse
from contracts.adapter import AdapterMetadata


class LangChainAdapter(AbstractFrameworkAdapter):
    """
    Framework adapter for integrating LangChain-core payloads with DisasterResponseAgent.
    Translates string prompts, dict payloads, or BaseMessage objects to AgentRequest,
    delegates processing to AgentCore, and formats output as structured dicts or AIMessage.
    """

    def __init__(self, core_agent: AgentCore, metadata: Optional[AdapterMetadata] = None):
        default_meta = metadata or AdapterMetadata(
            adapter_id="langchain_core_adapter",
            name="LangChainCoreAdapter",
            version="1.0.0",
            runtime_type="langchain_core",
            supported_input_format="human_message_dict_str",
            supported_output_format="json_dict_ai_message",
            description="LangChain-core framework adapter for DisasterResponseAgent."
        )
        super().__init__(core_agent=core_agent, metadata=default_meta)

    def adapt_request(self, framework_payload: Any) -> AgentRequest:
        """
        Convert LangChain-compatible payload (str, dict, or BaseMessage) into a validated AgentRequest.
        """
        if framework_payload is None:
            raise ValueError("Framework payload cannot be None.")

        req_id: Optional[str] = None
        user_input: Optional[str] = None
        context: Dict[str, Any] = {}
        requested_capabilities: list = []

        # Form A: Plain String
        if isinstance(framework_payload, str):
            user_input = framework_payload

        # Form B: LangChain Message object (HumanMessage / BaseMessage)
        elif isinstance(framework_payload, BaseMessage):
            user_input = str(framework_payload.content)
            req_id = getattr(framework_payload, "id", None)
            if hasattr(framework_payload, "additional_kwargs") and isinstance(framework_payload.additional_kwargs, dict):
                context = framework_payload.additional_kwargs.get("context", {})
                requested_capabilities = framework_payload.additional_kwargs.get("requested_capabilities", [])

        # Form C: Dictionary Payload
        elif isinstance(framework_payload, dict):
            req_id = framework_payload.get("request_id") or framework_payload.get("id")
            user_input = framework_payload.get("input") or framework_payload.get("user_input") or framework_payload.get("task")
            context = framework_payload.get("context") or framework_payload.get("payload") or {}
            requested_capabilities = framework_payload.get("requested_capabilities") or []

        else:
            raise ValueError(f"Unsupported LangChain payload type: '{type(framework_payload).__name__}'. Supported: str, dict, BaseMessage.")

        # Ensure user_input exists and is non-empty
        if not user_input or not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("Payload missing valid non-empty user input.")

        # Generate runtime-safe request_id if missing
        if not req_id or not isinstance(req_id, str) or not req_id.strip():
            req_id = f"lc-req-{uuid.uuid4().hex[:8]}"

        if not isinstance(context, dict):
            raise ValueError("Payload 'context' must be a dictionary.")

        try:
            return AgentRequest(
                request_id=req_id.strip(),
                user_input=user_input.strip(),
                context=context,
                requested_capabilities=requested_capabilities
            )
        except ValidationError as e:
            raise ValueError(f"Failed to adapt LangChain payload to AgentRequest: {str(e)}")

    def adapt_response(self, core_response: AgentResponse) -> Dict[str, Any]:
        """Convert AgentResponse instance into a clean JSON-compatible dictionary payload."""
        if not isinstance(core_response, AgentResponse):
            raise ValueError("core_response must be a valid AgentResponse instance.")

        return {
            "request_id": core_response.request_id,
            "status": core_response.status.value,
            "result": core_response.result,
            "used_capabilities": core_response.used_capabilities,
            "used_tools": core_response.used_tools,
            "execution_metadata": core_response.execution_metadata,
            "errors": [err.model_dump() for err in core_response.errors]
        }

    def adapt_to_message(self, core_response: AgentResponse) -> AIMessage:
        """Convert AgentResponse into a LangChain AIMessage object with response metadata."""
        dict_output = self.adapt_response(core_response)
        content_summary = (
            core_response.result.get("summary")
            if core_response.result and isinstance(core_response.result, dict)
            else f"Agent state: {core_response.status.value}"
        )
        return AIMessage(
            content=str(content_summary),
            id=core_response.request_id,
            additional_kwargs=dict_output
        )
