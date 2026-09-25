"""
Behavior Contract specification for DisasterResponseAgent.

Defines the machine-readable, framework-independent execution lifecycle stages
and transition constraints for core processing.
"""

from enum import Enum
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class LifecycleStage(str, Enum):
    """Execution lifecycle stages for the agent core."""
    INPUT = "INPUT"
    REQUEST_VALIDATION = "REQUEST_VALIDATION"
    PASSPORT_LOADING = "PASSPORT_LOADING"
    CAPABILITY_VALIDATION = "CAPABILITY_VALIDATION"
    TOOL_DISCOVERY = "TOOL_DISCOVERY"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    RESULT_VALIDATION = "RESULT_VALIDATION"
    RESPONSE_GENERATION = "RESPONSE_GENERATION"


class StageSpecification(BaseModel):
    """Specification of an individual lifecycle stage."""
    stage: LifecycleStage
    description: str
    required_inputs: List[str]
    output_artifacts: List[str]


class BehaviorContract(BaseModel):
    """
    Machine-readable Behavior Contract defining the agent execution pipeline.
    Independent of web frameworks or third-party AI libraries.
    """
    contract_version: str = "1.0.0"
    stages: List[StageSpecification] = Field(
        default_factory=lambda: [
            StageSpecification(
                stage=LifecycleStage.INPUT,
                description="Receive structured AgentRequest payload.",
                required_inputs=["request_id", "user_input"],
                output_artifacts=["raw_request"]
            ),
            StageSpecification(
                stage=LifecycleStage.REQUEST_VALIDATION,
                description="Validate request fields and parameter constraints.",
                required_inputs=["raw_request"],
                output_artifacts=["validated_request"]
            ),
            StageSpecification(
                stage=LifecycleStage.PASSPORT_LOADING,
                description="Dynamically load active AgentPassport specification.",
                required_inputs=["passport_file_path"],
                output_artifacts=["active_passport"]
            ),
            StageSpecification(
                stage=LifecycleStage.CAPABILITY_VALIDATION,
                description="Verify requested capabilities against passport authorization bounds.",
                required_inputs=["requested_capabilities", "active_passport"],
                output_artifacts=["authorized_capabilities"]
            ),
            StageSpecification(
                stage=LifecycleStage.TOOL_DISCOVERY,
                description="Match authorized capabilities to registered operational tools in ToolRegistry.",
                required_inputs=["authorized_capabilities", "tool_registry"],
                output_artifacts=["matched_tools", "missing_tools"]
            ),
            StageSpecification(
                stage=LifecycleStage.TOOL_EXECUTION,
                description="Execute registered tools with validated parameters.",
                required_inputs=["matched_tools"],
                output_artifacts=["tool_results"]
            ),
            StageSpecification(
                stage=LifecycleStage.RESULT_VALIDATION,
                description="Validate tool output payloads against contract schemas.",
                required_inputs=["tool_results"],
                output_artifacts=["validated_results"]
            ),
            StageSpecification(
                stage=LifecycleStage.RESPONSE_GENERATION,
                description="Produce final AgentResponse with explicit status and execution metadata.",
                required_inputs=["validated_results", "execution_metadata"],
                output_artifacts=["final_response"]
            ),
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize BehaviorContract to dictionary."""
        return self.model_dump()
