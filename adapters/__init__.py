"""
Adapters module for DisasterResponseAgent.

Contains framework translation layers connecting the framework-agnostic Core Agent
to third-party AI frameworks or generic runtime environments.
"""

from adapters.base import AbstractFrameworkAdapter
from adapters.portable_adapter import PortableAdapter
from adapters.langchain_adapter import LangChainAdapter
from adapters.registry import AdapterRegistry

__all__ = [
    "AbstractFrameworkAdapter",
    "PortableAdapter",
    "LangChainAdapter",
    "AdapterRegistry",
]
