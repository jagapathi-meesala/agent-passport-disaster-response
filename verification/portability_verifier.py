"""
Portability Verification Engine implementation.

Verifies semantic behavioral equivalence of AgentCore across multiple runtime entry points
(Direct AgentCore, PortableAdapter, LangChainAdapter) without modifying AgentCore logic,
duplicating state machines, or adding framework dependencies to core code.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from contracts.schemas import AgentRequest, AgentResponse, AgentStatus
from core.agent import AgentCore
from adapters.portable_adapter import PortableAdapter
from adapters.langchain_adapter import LangChainAdapter
from passport.manager import PassportManager
from tools.base import ToolRegistry


class PortabilityResult:
    """Encapsulates outcome and comparison matrix of a portability verification audit."""

    def __init__(
        self,
        is_valid: bool,
        execution_paths_tested: List[str],
        status_match: bool = True,
        capabilities_match: bool = True,
        tools_match: bool = True,
        result_match: bool = True,
        errors_match: bool = True,
        framework_isolation_passed: bool = True,
        hardcoding_audit_passed: bool = True,
        matrix: Optional[Dict[str, Dict[str, bool]]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.is_valid = is_valid
        self.execution_paths_tested = execution_paths_tested
        self.status_match = status_match
        self.capabilities_match = capabilities_match
        self.tools_match = tools_match
        self.result_match = result_match
        self.errors_match = errors_match
        self.framework_isolation_passed = framework_isolation_passed
        self.hardcoding_audit_passed = hardcoding_audit_passed
        self.matrix = matrix or {}
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize verification result to JSON-compatible dictionary."""
        return {
            "is_valid": self.is_valid,
            "execution_paths_tested": self.execution_paths_tested,
            "status_match": self.status_match,
            "capabilities_match": self.capabilities_match,
            "tools_match": self.tools_match,
            "result_match": self.result_match,
            "errors_match": self.errors_match,
            "framework_isolation_passed": self.framework_isolation_passed,
            "hardcoding_audit_passed": self.hardcoding_audit_passed,
            "matrix": self.matrix,
            "details": self.details
        }

    def to_json(self) -> str:
        """Serialize verification result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def __repr__(self) -> str:
        return f"<PortabilityResult is_valid={self.is_valid} paths={self.execution_paths_tested}>"


class PortabilityVerifier:
    """
    Verification engine proving semantic equivalence across Direct Core,
    PortableAdapter, and LangChainAdapter execution entry points.
    """

    @staticmethod
    def normalize_response(raw_resp: Union[AgentResponse, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize raw response object (AgentResponse or Dict) into a clean semantic dictionary.
        Strips dynamic request IDs, execution metadata timestamps, durations, and wrapper classes.
        """
        if isinstance(raw_resp, AgentResponse):
            d = raw_resp.to_dict()
        elif isinstance(raw_resp, dict):
            d = raw_resp
        else:
            raise ValueError(f"Cannot normalize object of type: {type(raw_resp)}")

        # Normalize status
        status_val = d.get("status")
        if isinstance(status_val, AgentStatus):
            status_str = status_val.value
        else:
            status_str = str(status_val)

        # Normalize used_capabilities and used_tools (sorted lists for set equivalence)
        used_caps = sorted(d.get("used_capabilities") or [])
        used_tools = sorted(d.get("used_tools") or [])

        # Normalize errors to list of error_codes
        raw_errors = d.get("errors") or []
        err_codes = []
        for err in raw_errors:
            if isinstance(err, dict):
                err_codes.append(err.get("error_code", "UNKNOWN_ERROR"))
            elif hasattr(err, "error_code"):
                err_codes.append(err.error_code)

        # Normalize result dictionary
        result_dict = d.get("result")

        return {
            "status": status_str,
            "result": result_dict,
            "used_capabilities": used_caps,
            "used_tools": used_tools,
            "errors": sorted(err_codes)
        }

    def verify_equivalence(
        self,
        core_agent: AgentCore,
        payload: Dict[str, Any]
    ) -> PortabilityResult:
        """
        Execute payload across 3 paths (Direct Core, PortableAdapter, LangChainAdapter)
        and compare semantic equivalence.
        """
        paths = ["direct_core", "portable_adapter", "langchain_adapter"]
        portable_adapter = PortableAdapter(core_agent=core_agent)
        langchain_adapter = LangChainAdapter(core_agent=core_agent)

        # Path 1: Direct Core
        req_id = payload.get("request_id") or payload.get("id") or "verifier-req-01"
        user_input = payload.get("input") or payload.get("user_input") or "Perform task"
        context = payload.get("context") or payload.get("payload") or {}
        caps = payload.get("requested_capabilities") or []

        direct_req = AgentRequest(
            request_id=req_id,
            user_input=user_input,
            context=context,
            requested_capabilities=caps
        )
        resp_direct = core_agent.process_request(direct_req)

        # Path 2: Portable Adapter
        resp_portable = portable_adapter.run_framework_task(payload)

        # Path 3: LangChain Adapter
        resp_langchain = langchain_adapter.run_framework_task(payload)

        # Normalize responses
        norm_direct = self.normalize_response(resp_direct)
        norm_portable = self.normalize_response(resp_portable)
        norm_langchain = self.normalize_response(resp_langchain)

        # Property Comparisons
        status_match = (norm_direct["status"] == norm_portable["status"] == norm_langchain["status"])
        capabilities_match = (norm_direct["used_capabilities"] == norm_portable["used_capabilities"] == norm_langchain["used_capabilities"])
        tools_match = (norm_direct["used_tools"] == norm_portable["used_tools"] == norm_langchain["used_tools"])
        result_match = (norm_direct["result"] == norm_portable["result"] == norm_langchain["result"])
        errors_match = (norm_direct["errors"] == norm_portable["errors"] == norm_langchain["errors"])

        overall_valid = status_match and capabilities_match and tools_match and result_match and errors_match

        matrix = {
            "status": {"direct_core": True, "portable_adapter": norm_portable["status"] == norm_direct["status"], "langchain_adapter": norm_langchain["status"] == norm_direct["status"]},
            "capabilities": {"direct_core": True, "portable_adapter": norm_portable["used_capabilities"] == norm_direct["used_capabilities"], "langchain_adapter": norm_langchain["used_capabilities"] == norm_direct["used_capabilities"]},
            "tools": {"direct_core": True, "portable_adapter": norm_portable["used_tools"] == norm_direct["used_tools"], "langchain_adapter": norm_langchain["used_tools"] == norm_direct["used_tools"]},
            "result": {"direct_core": True, "portable_adapter": norm_portable["result"] == norm_direct["result"], "langchain_adapter": norm_langchain["result"] == norm_direct["result"]},
            "errors": {"direct_core": True, "portable_adapter": norm_portable["errors"] == norm_direct["errors"], "langchain_adapter": norm_langchain["errors"] == norm_direct["errors"]}
        }

        return PortabilityResult(
            is_valid=overall_valid,
            execution_paths_tested=paths,
            status_match=status_match,
            capabilities_match=capabilities_match,
            tools_match=tools_match,
            result_match=result_match,
            errors_match=errors_match,
            matrix=matrix,
            details={
                "direct_core": norm_direct,
                "portable_adapter": norm_portable,
                "langchain_adapter": norm_langchain
            }
        )

    def verify_unauthorized_capability(
        self,
        core_agent: AgentCore,
        unauthorized_capability: str = "unauthorized_cyber_override"
    ) -> PortabilityResult:
        """
        Verify that unauthorized capability requests fail consistently with identical error status across all entry points.
        """
        payload = {
            "request_id": "unauth-req-verifier",
            "input": "Attempt unauthorized action",
            "requested_capabilities": [unauthorized_capability]
        }
        res = self.verify_equivalence(core_agent, payload)
        # Extra assertion: verify all 3 produced status == 'failed'
        direct_status = res.details["direct_core"]["status"]
        if direct_status != "failed":
            res.is_valid = False

        return res

    def verify_framework_isolation(self, project_root: Optional[str] = None) -> bool:
        """Scan core/, contracts/, tools/, passport/ for forbidden framework/provider imports."""
        root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent
        forbidden_modules = ("langchain", "langchain_core", "fastapi", "openai", "anthropic", "crewai", "autogen", "lyzr")
        target_dirs = ("core", "contracts", "tools", "passport")

        for t_dir in target_dirs:
            dir_path = root / t_dir
            if not dir_path.is_dir():
                continue
            for py_file in dir_path.glob("**/*.py"):
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for forbidden in forbidden_modules:
                    if forbidden in content:
                        return False
        return True

    def verify_hardcoding_audit(self, project_root: Optional[str] = None) -> bool:
        """Scan core/, contracts/, tools/, passport/, config/, adapters/ for hardcoded secrets or runtime defaults."""
        import re
        root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent
        secret_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
        target_dirs = ("core", "contracts", "tools", "passport", "config", "adapters")

        for t_dir in target_dirs:
            dir_path = root / t_dir
            if not dir_path.is_dir():
                continue
            for py_file in dir_path.glob("**/*.py"):
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if secret_pattern.search(content):
                    return False
                if "secret_key = \"" in content.lower():
                    return False
        return True

    def run_full_verification(
        self,
        core_agent: Optional[AgentCore] = None,
        passport_path: str = "config/passport.json"
    ) -> PortabilityResult:
        """Execute complete portability verification suite and generate consolidated PortabilityResult."""
        if core_agent is None:
            pm = PassportManager()
            pm.load_from_file(passport_path)
            tr = ToolRegistry()
            core_agent = AgentCore(passport_manager=pm, tool_registry=tr)

        valid_payload = {
            "request_id": "full-verifier-01",
            "input": "Evaluate disaster situational awareness",
            "context": {"location_bounds": {"lat": 10.0, "lon": 20.0}},
            "requested_capabilities": ["situational_assessment"]
        }

        res_equivalence = self.verify_equivalence(core_agent, valid_payload)
        res_unauth = self.verify_unauthorized_capability(core_agent)
        isolation_ok = self.verify_framework_isolation()
        hardcoding_ok = self.verify_hardcoding_audit()

        overall_valid = (
            res_equivalence.is_valid and
            res_unauth.is_valid and
            isolation_ok and
            hardcoding_ok
        )

        return PortabilityResult(
            is_valid=overall_valid,
            execution_paths_tested=res_equivalence.execution_paths_tested,
            status_match=res_equivalence.status_match,
            capabilities_match=res_equivalence.capabilities_match,
            tools_match=res_equivalence.tools_match,
            result_match=res_equivalence.result_match,
            errors_match=res_equivalence.errors_match,
            framework_isolation_passed=isolation_ok,
            hardcoding_audit_passed=hardcoding_ok,
            matrix=res_equivalence.matrix,
            details={
                "equivalence_details": res_equivalence.details,
                "unauthorized_capability_test": res_unauth.details,
                "framework_isolation_passed": isolation_ok,
                "hardcoding_audit_passed": hardcoding_ok
            }
        )
