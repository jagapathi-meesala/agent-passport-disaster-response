"""
Framework-neutral Adapter Registry implementation.

Manages dynamic registration, lookup, listing, and lifecycle of framework and runtime adapters
without embedding framework-specific logic in AgentCore.
"""

from typing import Dict, List, Optional
from adapters.base import AbstractFrameworkAdapter


class AdapterRegistry:
    """Registry for managing active framework adapters."""

    def __init__(self):
        self._adapters: Dict[str, AbstractFrameworkAdapter] = {}

    def register_adapter(self, adapter_id: str, adapter: AbstractFrameworkAdapter) -> None:
        """Register a framework adapter instance under a unique adapter_id string."""
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            raise ValueError("adapter_id must be a non-empty string.")
        if not isinstance(adapter, AbstractFrameworkAdapter):
            raise TypeError("adapter must be an instance of AbstractFrameworkAdapter.")

        s_id = adapter_id.strip()
        if s_id in self._adapters:
            raise ValueError(f"Adapter with ID '{s_id}' is already registered.")

        self._adapters[s_id] = adapter

    def unregister_adapter(self, adapter_id: str) -> bool:
        """Unregister an adapter by adapter_id. Returns True if removed, False if not found."""
        if not isinstance(adapter_id, str):
            return False
        s_id = adapter_id.strip()
        if s_id in self._adapters:
            del self._adapters[s_id]
            return True
        return False

    def get_adapter(self, adapter_id: str) -> Optional[AbstractFrameworkAdapter]:
        """Retrieve registered adapter instance by adapter_id string."""
        if not isinstance(adapter_id, str):
            return None
        return self._adapters.get(adapter_id.strip())

    def list_adapters(self) -> List[str]:
        """Return list of registered adapter IDs."""
        return list(self._adapters.keys())

    def clear(self) -> None:
        """Unregister all adapters."""
        self._adapters.clear()
