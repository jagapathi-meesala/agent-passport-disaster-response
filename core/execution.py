"""
Task execution pipeline abstractions and runtime ExecutionContext for DisasterResponseAgent.

Defines the framework-independent ExecutionContext tracking execution IDs, dynamic ISO timestamps,
and execution duration without hardcoding operational values or secrets.
"""

import uuid
import time
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, PrivateAttr


class ExecutionContext(BaseModel):
    """
    Runtime execution context metadata wrapper.
    Generates dynamic execution_id and timestamps at runtime.
    """
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    environment: str = "development"

    _start_timestamp: float = PrivateAttr(default_factory=time.time)

    def finish(self) -> Dict[str, Any]:
        """Record completion timestamp and calculate execution duration."""
        now = datetime.now(timezone.utc)
        self.end_time = now.isoformat()
        self.duration_seconds = round(time.time() - self._start_timestamp, 4)
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ExecutionContext to dictionary."""
        return self.model_dump()


class AbstractExecutionEngine(ABC):
    """Abstract interface for task processing and tool orchestration engines."""

    @abstractmethod
    def run_step(self, step_input: Dict[str, Any], allowed_tools: List[str]) -> Dict[str, Any]:
        """Process a single step in a disaster response execution plan."""
        pass
