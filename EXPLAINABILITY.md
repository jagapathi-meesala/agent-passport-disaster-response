# Explainability

## Agent Purpose

DisasterResponseAgent is a portable disaster-response AI agent designed to support structured disaster-response workflows through a framework-independent core and dynamically integrated tools.

## Decision and Execution Flow

The agent follows a defined lifecycle:

1. INPUT
2. REQUEST_VALIDATION
3. PASSPORT_LOADING
4. CAPABILITY_VALIDATION
5. TOOL_DISCOVERY
6. TOOL_EXECUTION
7. RESULT_VALIDATION
8. RESPONSE_GENERATION

Each request is validated against the agent passport before execution.

## Capability Selection

The agent only executes capabilities declared in its passport.

Declared capabilities include:

- situational assessment
- logistics coordination
- resource allocation
- weather monitoring
- resource location

An unsupported capability is rejected rather than executed.

## Tool Selection

Tools are discovered dynamically through the ToolRegistry.

Before execution, the system checks:

1. Whether the tool exists.
2. Whether the tool is enabled.
3. Whether the tool is authorized by the passport.
4. Whether the input matches the tool contract.
5. Whether the tool execution succeeds.
6. Whether the output matches the expected contract.

## External Provider Handling

External provider configuration is supplied through the runtime environment.

The agent does not fabricate external results when a provider is unavailable or unconfigured.

Instead, the execution state reports that external tool configuration is required.

## Portability

The same AgentCore behavior can be accessed through:

- Direct AgentCore execution
- PortableAdapter
- LangChainAdapter

The portability verifier compares the semantic behavior of these execution paths.

## Verification

The project includes automated verification for:

- Passport identity
- Semantic version compliance
- Behavior contract compatibility
- Cross-adapter identity consistency
- Unauthorized capability rejection
- Framework isolation
- Zero-hardcoding requirements
- Tool and capability consistency

## Evidence

The repository contains automated tests and competition evidence demonstrating the verification results.

The complete test suite currently contains 175 tests.

The final demo verifies all seven lifecycle stages and reports successful passport trust and framework portability verification.

## Transparency

The agent reports execution status, selected capabilities, selected tools, execution metadata, and errors in structured responses.

This allows consumers of the agent to understand which capabilities and tools were involved in a request without relying on hidden framework-specific behavior.
