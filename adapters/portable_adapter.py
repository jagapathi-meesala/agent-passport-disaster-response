"""
Reference Portable Runtime Adapter implementation.

Demonstrates wrapping AgentCore with a framework-neutral dictionary/JSON runtime interface
without modifying AgentCore business logic, state machines, or tool registration.
"""

from typing import Any, Dict, Optional
from pydantic import ValidationError

from adapters.base import AbstractFrameworkAdapter
from core.agent import AgentCore
from contracts.schemas import AgentRequest, AgentResponse
from contracts.adapter import AdapterMetadata


class PortableAdapter(AbstractFrameworkAdapter):
    """
    Reference portable adapter for generic runtime execution environments.
    Converts generic input dictionary payloads to AgentRequest and AgentResponse to output dictionaries.
    """

    def __init__(self, core_agent: AgentCore, metadata: Optional[AdapterMetadata] = None):
        default_meta = metadata or AdapterMetadata(
            adapter_id="portable_reference_adapter",
            name="PortableReferenceAdapter",
            version="1.0.0",
            runtime_type="reference",
            supported_input_format="json_dict",
            supported_output_format="json_dict",
            description="Framework-neutral reference runtime adapter for DisasterResponseAgent."
        )
        super().__init__(core_agent=core_agent, metadata=default_meta)

    def adapt_request(self, framework_payload: Any) -> AgentRequest:
        """
        Convert generic runtime payload dictionary into a validated AgentRequest schema.
        Supports input field mappings: 'request_id'/'task_id', 'input'/'user_input'/'task'.
        """
        if not isinstance(framework_payload, dict):
            raise ValueError("Runtime payload must be a non-empty dictionary.")

        req_id = framework_payload.get("request_id") or framework_payload.get("task_id")
        user_input = framework_payload.get("input") or framework_payload.get("user_input") or framework_payload.get("task")
        context = framework_payload.get("context") or framework_payload.get("payload") or {}
        requested_capabilities = framework_payload.get("requested_capabilities") or []

        if not req_id or not isinstance(req_id, str) or not req_id.strip():
            import uuid
            req_id = f"port-req-{uuid.uuid4().hex[:8]}"

        if not user_input or not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("Runtime payload missing valid 'input' or 'user_input'.")

        if not isinstance(context, dict):
            raise ValueError("Runtime payload 'context' must be a dictionary.")

        try:
            return AgentRequest(
                request_id=req_id.strip(),
                user_input=user_input.strip(),
                context=context,
                requested_capabilities=requested_capabilities
            )
        except ValidationError as e:
            raise ValueError(f"Failed to adapt runtime payload to AgentRequest: {str(e)}")

    def adapt_response(self, core_response: AgentResponse) -> Dict[str, Any]:
        """Convert AgentResponse instance into a clean JSON-compatible dictionary representation."""
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
