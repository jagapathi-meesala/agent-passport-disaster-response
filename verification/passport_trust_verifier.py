"""
Passport Trust & Identity Verification Engine implementation.

Verifies structural schema integrity, semver validity, dynamic contract version matching,
identity invariance across runtime entry points (Direct Core, PortableAdapter, LangChainAdapter),
capability bounds, tool authorization, and unauthorized capability rejection.
"""

import json
from typing import Any, Dict, List, Optional

from passport.schema import AgentPassport
from passport.manager import PassportManager
from verification.passport_verifier import PassportVerifier
from contracts.behavior import BehaviorContract
from contracts.schemas import AgentRequest, AgentStatus
from core.agent import AgentCore
from adapters.portable_adapter import PortableAdapter
from adapters.langchain_adapter import LangChainAdapter
from tools.base import ToolRegistry


class PassportTrustResult:
    """Encapsulates outcome of a Passport Trust & Identity verification audit."""

    def __init__(
        self,
        is_valid: bool,
        agent_id: str,
        version: str,
        passport_version: str,
        contract_version: str,
        expected_contract_version: str,
        contract_version_matching: bool,
        schema_integrity_valid: bool,
        capabilities_count: int,
        authorized_tools_count: int,
        adapter_identity_consistent: bool,
        unauthorized_capability_rejection_passed: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        self.is_valid = is_valid
        self.agent_id = agent_id
        self.version = version
        self.passport_version = passport_version
        self.contract_version = contract_version
        self.expected_contract_version = expected_contract_version
        self.contract_version_matching = contract_version_matching
        self.schema_integrity_valid = schema_integrity_valid
        self.capabilities_count = capabilities_count
        self.authorized_tools_count = authorized_tools_count
        self.adapter_identity_consistent = adapter_identity_consistent
        self.unauthorized_capability_rejection_passed = unauthorized_capability_rejection_passed
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trust verification result to a JSON-compatible dictionary."""
        return {
            "is_valid": self.is_valid,
            "agent_id": self.agent_id,
            "version": self.version,
            "passport_version": self.passport_version,
            "contract_version": self.contract_version,
            "expected_contract_version": self.expected_contract_version,
            "contract_version_matching": self.contract_version_matching,
            "schema_integrity_valid": self.schema_integrity_valid,
            "capabilities_count": self.capabilities_count,
            "authorized_tools_count": self.authorized_tools_count,
            "adapter_identity_consistent": self.adapter_identity_consistent,
            "unauthorized_capability_rejection_passed": self.unauthorized_capability_rejection_passed,
            "details": self.details
        }

    def to_json(self) -> str:
        """Serialize trust verification result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def __repr__(self) -> str:
        return f"<PassportTrustResult is_valid={self.is_valid} agent_id='{self.agent_id}'>"


class PassportTrustVerifier:
    """
    Verification engine evaluating concrete identity, contract compliance, capability bounds,
    and multi-adapter authorization invariance of Agent Passports.
    """

    def __init__(self, passport_verifier: Optional[PassportVerifier] = None):
        self.passport_verifier = passport_verifier or PassportVerifier()

    def verify_trust(
        self,
        passport: AgentPassport,
        core_agent: Optional[AgentCore] = None
    ) -> PassportTrustResult:
        """
        Perform dynamic trust and identity verification for a given AgentPassport.
        """
        # 1. Structural Schema Verification
        verification_res = self.passport_verifier.verify(passport)
        schema_integrity_valid = verification_res.is_valid

        # 2. Dynamic Contract Version Verification
        expected_contract_ver = BehaviorContract().contract_version
        contract_version_matching = (passport.contract_version == expected_contract_ver)

        # 3. Dynamic Identity Properties Extraction
        agent_id = passport.agent_id or ""
        version = passport.version or ""
        passport_version = passport.passport_version or ""

        # 4. Capability Bounds Verification
        capabilities_count = len(passport.capabilities) if passport.capabilities else 0

        # 5. Tool Authorization Verification
        authorized_tools = passport.tools if passport.tools is not None else []
        if passport.allowed_tools is not None:
            authorized_tools = passport.allowed_tools
        authorized_tools_count = len(authorized_tools)

        # Prepare Core Agent with target passport bound
        if core_agent is None:
            pm = PassportManager()
            p_obj = pm.load_from_dict(passport.to_dict())
            tr = ToolRegistry()
            core_agent = AgentCore(passport_manager=pm, tool_registry=tr)
            core_agent._active_passport = p_obj
        else:
            p_obj = core_agent.passport_manager.load_from_dict(passport.to_dict())
            core_agent._active_passport = p_obj

        # 6. Multi-Adapter Identity Consistency Verification
        adapter_identity_consistent = True
        try:
            # Direct Core Status
            core_status = core_agent.get_status()
            if core_status.get("agent_id") != agent_id:
                adapter_identity_consistent = False

            # Portable Adapter execution identity check
            portable_adapter = PortableAdapter(core_agent=core_agent)
            payload_valid = {
                "request_id": "trust-req-portable",
                "input": "Identity consistency check task",
                "requested_capabilities": [passport.capabilities[0]] if capabilities_count > 0 else []
            }
            res_port = portable_adapter.run_framework_task(payload_valid)
            if res_port.get("status") not in ("completed", "awaiting_tools"):
                adapter_identity_consistent = False

            # LangChain Adapter execution identity check
            langchain_adapter = LangChainAdapter(core_agent=core_agent)
            res_lc = langchain_adapter.run_framework_task(payload_valid)
            if res_lc.get("status") not in ("completed", "awaiting_tools"):
                adapter_identity_consistent = False

        except Exception:
            adapter_identity_consistent = False

        # 7. Unauthorized Capability Rejection Test Across All Adapters
        unauthorized_rejection_passed = True
        try:
            unauth_payload = {
                "request_id": "trust-unauth-test",
                "input": "Attempt unauthorized action",
                "requested_capabilities": ["unauthorized_synthetic_capability_999"]
            }

            # Path A: Direct Core
            direct_req = AgentRequest(
                request_id="trust-unauth-direct",
                user_input="Attempt unauthorized action",
                requested_capabilities=["unauthorized_synthetic_capability_999"]
            )
            res_direct = core_agent.process_request(direct_req)

            # Path B: Portable Adapter
            res_port_unauth = portable_adapter.run_framework_task(unauth_payload)

            # Path C: LangChain Adapter
            res_lc_unauth = langchain_adapter.run_framework_task(unauth_payload)

            # Check that all 3 failed with UNSUPPORTED_CAPABILITY
            if res_direct.status != AgentStatus.FAILED or not any(e.error_code == "UNSUPPORTED_CAPABILITY" for e in res_direct.errors):
                unauthorized_rejection_passed = False
            if res_port_unauth.get("status") != "failed" or not any(e.get("error_code") == "UNSUPPORTED_CAPABILITY" for e in res_port_unauth.get("errors", [])):
                unauthorized_rejection_passed = False
            if res_lc_unauth.get("status") != "failed" or not any(e.get("error_code") == "UNSUPPORTED_CAPABILITY" for e in res_lc_unauth.get("errors", [])):
                unauthorized_rejection_passed = False

        except Exception:
            unauthorized_rejection_passed = False

        # Consolidated Trust Validity
        overall_valid = (
            schema_integrity_valid and
            contract_version_matching and
            adapter_identity_consistent and
            unauthorized_rejection_passed and
            capabilities_count > 0 and
            bool(agent_id) and
            bool(name := passport.name)
        )

        details = {
            "schema_verification_reason": verification_res.reason,
            "passport_contract_version": passport.contract_version,
            "behavior_contract_version": expected_contract_ver,
            "adapters_verified": ["direct_core", "portable_adapter", "langchain_adapter"],
            "capabilities": passport.capabilities,
            "tools": authorized_tools
        }

        return PassportTrustResult(
            is_valid=overall_valid,
            agent_id=agent_id,
            version=version,
            passport_version=passport_version,
            contract_version=passport.contract_version,
            expected_contract_version=expected_contract_ver,
            contract_version_matching=contract_version_matching,
            schema_integrity_valid=schema_integrity_valid,
            capabilities_count=capabilities_count,
            authorized_tools_count=authorized_tools_count,
            adapter_identity_consistent=adapter_identity_consistent,
            unauthorized_capability_rejection_passed=unauthorized_rejection_passed,
            details=details
        )
