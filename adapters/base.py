"""
Abstract Framework Adapter interface.

Defines the generic wrapper specification for adapting external agent frameworks or runtimes
to standard Core Agent contracts without embedding business logic or framework-specific dependencies in AgentCore.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from core.agent import AgentCore
from contracts.schemas import AgentRequest, AgentResponse
from contracts.adapter import AdapterMetadata


class AbstractFrameworkAdapter(ABC):
    """Abstract interface for framework and runtime wrappers."""

    def __init__(self, core_agent: AgentCore, metadata: Optional[AdapterMetadata] = None):
        if core_agent is None:
            raise ValueError("core_agent must be a valid AgentCore instance.")
        self.core_agent = core_agent
        self.metadata = metadata

    @abstractmethod
    def adapt_request(self, framework_payload: Any) -> AgentRequest:
        """Convert framework-specific or generic runtime input format into standard AgentRequest schema."""
        pass

    @abstractmethod
    def adapt_response(self, core_response: AgentResponse) -> Any:
        """Convert standard AgentResponse core output format into framework/runtime payload."""
        pass

    def run_framework_task(self, framework_payload: Any) -> Any:
        """
        Execute framework task by translating input to AgentRequest,
        delegating execution strictly to AgentCore, and translating AgentResponse back.
        """
        request = self.adapt_request(framework_payload)
        response = self.core_agent.process_request(request)
        return self.adapt_response(response)
