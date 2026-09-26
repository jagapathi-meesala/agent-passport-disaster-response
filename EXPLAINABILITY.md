# Explainability

## 1. Agent Identity

- Agent name: DisasterResponseAgent
- Agent type: Portable Disaster Response Agent
- Agent version: 1.0.0
- Passport specification: `config/passport.json`
- OpenGAP manifest: `agent.yaml`
- Agent identity definition: `SOUL.md`

The agent identity is defined independently from the runtime framework.

---

## 2. Mission

The agent is designed to support disaster-response workflows through a portable, framework-independent architecture.

Its declared capabilities are:

- situational_assessment
- logistics_coordination
- resource_allocation
- weather_monitoring
- resource_location

The agent does not claim capabilities that are absent from its passport.

---

## 3. Input

The agent accepts structured requests containing:

- request identifier
- user input
- optional context
- requested capabilities

Input is represented through the framework-independent `AgentRequest` contract.

Before execution, the request is validated.

---

## 4. Decision and Execution Lifecycle

Every request follows the agent lifecycle:

1. INPUT
2. REQUEST_VALIDATION
3. PASSPORT_LOADING
4. CAPABILITY_VALIDATION
5. TOOL_DISCOVERY
6. TOOL_EXECUTION
7. RESULT_VALIDATION
8. RESPONSE_GENERATION

Each stage has a defined responsibility.

### INPUT

Receives the request through the framework-independent request contract.

### REQUEST_VALIDATION

Checks that the request satisfies the required request schema.

### PASSPORT_LOADING

Loads the configured agent passport dynamically.

### CAPABILITY_VALIDATION

Checks requested capabilities against capabilities declared by the passport.

Unsupported capabilities are rejected.

### TOOL_DISCOVERY

Discovers registered tools dynamically through `ToolRegistry`.

### TOOL_EXECUTION

A tool can execute only after:

1. The tool exists.
2. The tool is enabled.
3. The tool is authorized by the passport.
4. The input satisfies the tool contract.
5. Required provider configuration is available.

### RESULT_VALIDATION

Tool outputs are checked against their declared output contracts.

### RESPONSE_GENERATION

The agent produces a structured `AgentResponse` containing status, result, capabilities, tools, metadata, and errors where applicable.

---

## 5. Capability Decision Logic

The agent does not infer authorization from the user's request alone.

Authorization is determined from the loaded passport.

Conceptually:

    requested capability
            |
            v
    passport capability set
            |
       +----+----+
       |         |
     found    not found
       |         |
       v         v
    continue   reject
                |
                v
    UNSUPPORTED_CAPABILITY

This prevents unsupported capabilities from being executed.

---

## 6. Tool Selection Logic

Tools are selected dynamically through the tool registry.

For each requested capability, the system identifies registered tools associated with that capability.

Tool execution follows:

    tool lookup
        |
        v
    enabled?
        |
        v
    passport authorized?
        |
        v
    input valid?
        |
        v
    execute
        |
        v
    output valid?
        |
        v
    return result

A failure at an authorization or validation stage prevents unsafe or invalid execution.

---

## 7. External Provider Explainability

External provider configuration is not embedded in the source code.

Provider configuration is supplied through the runtime environment.

When a required provider is not configured, the agent does not invent a successful external result.

Instead:

    provider unavailable
          |
          v
    tool execution unavailable
          |
          v
    PROVIDER_NOT_CONFIGURED
          |
          v
    AWAITING_TOOLS

This makes the reason for incomplete execution visible to the caller.

---

## 8. Failure and Rejection Behavior

The agent exposes structured failure information.

Examples include:

### Unsupported capability

Status:

`failed`

Error:

`UNSUPPORTED_CAPABILITY`

Meaning:

The requested capability is not authorized by the agent passport.

### Missing provider configuration

Status:

`awaiting_tools`

Error:

`PROVIDER_NOT_CONFIGURED`

Meaning:

The requested operation requires an external provider that has not been configured.

### Disabled or unavailable tool

The ToolRegistry prevents execution and records the corresponding tool execution status.

---

## 9. Explainability of Outputs

The agent response exposes:

- request identifier
- execution status
- final result
- used capabilities
- used tools
- execution metadata
- structured errors

This allows a consumer to determine:

1. What request was processed.
2. What capabilities were used.
3. What tools were used.
4. Whether execution completed.
5. Whether external configuration was missing.
6. Whether the request was rejected.

The implementation does not require exposure of private internal reasoning or hidden model chain-of-thought.

---

## 10. Portability Explainability

The same framework-independent `AgentCore` can be accessed through:

- Direct AgentCore execution
- PortableAdapter
- LangChainAdapter

The adapters translate framework-specific request/response representations into the common contracts.

The core execution logic remains outside the framework adapters.

Therefore:

    Direct request
          |
          v
      AgentCore

    Generic adapter
          |
          v
      AgentCore

    LangChain adapter
          |
          v
      AgentCore

This keeps agent behavior independent from a single framework.

---

## 11. Cross-Adapter Verification

The portability verifier compares semantic execution results across:

- `direct_core`
- `portable_adapter`
- `langchain_adapter`

The verification checks:

- status
- capabilities
- tools
- result
- errors

Generated request identifiers, timestamps, durations, and wrapper-specific representations are not treated as semantic differences.

---

## 12. Passport Trust Verification

The PassportTrustVerifier verifies the actual loaded passport.

Verification includes:

- agent identity
- semantic version validity
- passport schema integrity
- behavior contract compatibility
- capability declarations
- authorized tool declarations
- cross-adapter identity consistency
- unauthorized capability rejection

The expected behavior-contract version is obtained dynamically from the contract definition rather than being hardcoded into the verifier.

---

## 13. Security and Authorization Boundary

The agent follows an allow-list model.

Only capabilities declared in the passport can be selected.

Only tools registered and authorized for execution can be used.

Unsupported capabilities are rejected before tool execution.

The verification suite explicitly tests unauthorized capability rejection.

---

## 14. No-Fake-Result Policy

The system does not report successful external tool results when the required provider is unavailable.

Provider failures remain visible through structured execution status and error information.

This distinction allows consumers to differentiate:

- completed execution
- unavailable tools
- failed requests
- unauthorized requests

---

## 15. Zero-Hardcoding Design

Runtime configuration and domain-specific external data are not embedded in the implementation.

The project does not hardcode:

- API keys
- provider URLs
- runtime service configuration
- geographic coordinates
- disaster locations
- hospital locations
- shelter locations
- weather values
- resource counts

Runtime provider configuration is supplied externally.

Protocol and contract definitions remain explicit because they are part of the implementation interface.

---

## 16. Verification Evidence

The project includes automated verification and evidence artifacts.

Current verification results include:

- 175 automated tests passed
- Passport Trust Verification: PASSED
- Framework Portability Verification: PASSED
- Framework Isolation Audit: PASSED
- Zero-Hardcoding Audit: PASSED
- Unauthorized Capability Rejection: PASSED
- All seven demo lifecycle stages verified successfully

Evidence screenshots are stored in the repository `evidence/` directory.

---

## 17. Reproducibility

The repository provides:

- `requirements.txt`
- `.env.example`
- `run_demo.py`
- automated tests
- verification modules
- documentation
- evidence artifacts

The project can therefore be inspected and verified from the repository rather than relying only on a presentation or screenshot.

---

## 18. Known External Dependency Boundary

Weather and resource-location operations depend on externally supplied provider configuration.

The project intentionally does not substitute fabricated provider results when those services are unavailable.

This means a provider-dependent request may legitimately return `awaiting_tools` until the required runtime configuration is supplied.

---

## 19. Summary

DisasterResponseAgent is explainable at the architectural and execution-contract level.

A request can be traced through:

    Input
      ↓
    Validation
      ↓
    Passport
      ↓
    Capability authorization
      ↓
    Tool discovery
      ↓
    Tool authorization
      ↓
    Tool execution
      ↓
    Result validation
      ↓
    Structured response
      ↓
    Verification

The system exposes the relevant execution decisions, selected capabilities, selected tools, execution status, and errors while keeping the core agent behavior independent of a single framework.
