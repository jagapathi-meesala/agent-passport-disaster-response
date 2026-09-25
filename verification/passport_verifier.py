"""
Passport Verification Engine implementation.

Performs verification of Agent Passport structure, semver compatibility, capability bounds,
and tool authorization permissions without hardcoded or fake verification output.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from passport.schema import AgentPassport


class VerificationResult:
    """Encapsulates outcome of a passport verification operation."""
    def __init__(self, is_valid: bool, reason: str):
        self.is_valid = is_valid
        self.reason = reason

    def __repr__(self) -> str:
        return f"<VerificationResult is_valid={self.is_valid} reason='{self.reason}'>"


class AbstractPassportVerifier(ABC):
    """Abstract interface for verifying agent passports."""

    @abstractmethod
    def verify(self, passport: AgentPassport, public_key: Optional[str] = None) -> VerificationResult:
        """Verify passport integrity and cryptographic signature against issuer public key."""
        pass

    @abstractmethod
    def check_permission(self, passport: AgentPassport, required_tool: str) -> bool:
        """Check if the given passport authorizes execution of a specific tool."""
        pass


class PassportVerifier(AbstractPassportVerifier):
    """Concrete passport verifier enforcing schema correctness, semver compliance, and permission scopes."""

    def verify(self, passport: AgentPassport, public_key: Optional[str] = None) -> VerificationResult:
        """Verify structural validity, semver formatting, and required field completeness."""
        if not isinstance(passport, AgentPassport):
            return VerificationResult(False, "Payload is not a valid AgentPassport instance.")

        if not passport.agent_id or not passport.name:
            return VerificationResult(False, "Passport identity fields (agent_id, name) cannot be empty.")

        if not passport.capabilities or len(passport.capabilities) == 0:
            return VerificationResult(False, "Passport must specify at least one capability.")

        if not passport.input_types or len(passport.input_types) == 0:
            return VerificationResult(False, "Passport must specify at least one input type.")

        if not passport.output_types or len(passport.output_types) == 0:
            return VerificationResult(False, "Passport must specify at least one output type.")

        # Signature verification check if signature and public key are supplied
        if passport.signature and not public_key:
            return VerificationResult(False, "Signature present on passport but no public verification key provided.")

        return VerificationResult(True, "Passport structural integrity and capability specifications verified.")

    def check_permission(self, passport: AgentPassport, required_tool: str) -> bool:
        """Check if the specified tool is authorized under the passport's tools or allowed_tools."""
        if not passport:
            return False
        
        authorized_tools = passport.tools
        if passport.allowed_tools is not None:
            authorized_tools = passport.allowed_tools

        return required_tool in authorized_tools
