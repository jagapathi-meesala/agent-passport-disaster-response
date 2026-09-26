# Explainability

## Agent Overview

This repository contains a portable disaster-response agent designed to provide structured assistance for disaster-response workflows.

The agent uses a framework-independent execution core and separates agent identity, behavior contracts, capabilities, tools, adapters, verification, and runtime configuration.

The design allows the agent to be inspected, tested, verified, and executed through supported adapters without making the core dependent on a single AI framework.

---

## 1. Agent Identity

The agent is identified as `DisasterResponseAgent` through the repository's passport and agent manifest configuration.

The agent manifest is defined in `agent.yaml`, while the passport definition is stored in `config/passport.json`.

The agent's identity and behavioral principles are also documented in `SOUL.md`.

The passport declares the agent's capabilities, supported input and output types, authorized tools, and behavior contract version.

---

## 2. Agent Purpose

The purpose of the agent is to support disaster-response workflows using structured and verifiable execution.

The agent is designed to assist with situational assessment, logistics coordination, resource allocation, weather monitoring, and resource location.

The agent does not assume that every requested operation is authorized.

Only capabilities and tools declared and authorized by the loaded passport can be executed.

---

## Inputs

The framework-independent request contract accepts structured agent requests.

An input request can contain a request identifier, user input, optional context, and requested capabilities.

The input data is validated before capability selection or tool execution begins.

Invalid or incomplete requests are rejected rather than being executed as valid operations.

The agent does not require a fixed disaster location, fixed dataset, fixed city, fixed resource count, or fixed external provider in the core execution logic.

Runtime provider configuration is supplied through the environment and external configuration rather than being embedded in the agent behavior.

---

## 4. Outputs

The agent produces a structured response describing the result of the requested execution.

The response can contain the request identifier, execution status, result data, selected capabilities, selected tools, execution metadata, and structured errors.

The execution status communicates whether the request completed successfully, failed, or is waiting for required external tool configuration.

This allows a consumer to determine what was requested, what was authorized, which tools were selected, and whether execution completed.

---

## Decision

The agent does not authorize an operation solely because that operation was requested by the user.

The decision process uses the loaded passport, declared capabilities, tool contracts, authorization rules, and runtime availability.

The decision-making sequence is:

```text
Request
   |
   v
Validate Request
   |
   v
Load Passport
   |
   v
Validate Requested Capability
   |
   +---- Unsupported Capability ----> Reject Request
   |
   v
Discover Tool
   |
   v
Check Tool Availability
   |
   v
Check Passport Authorization
   |
   v
Validate Tool Input
   |
   v
Execute Tool
   |
   v
Validate Tool Output
   |
   v
Generate Structured Response

---

## Limitations and Constraints

The agent has limitations and external dependencies that can affect execution.

External provider operations depend on the required provider configuration being available at runtime.

The agent cannot return real external provider data when the required provider is unavailable or not configured.

Provider-dependent capabilities can therefore enter an awaiting-tools or failure state instead of producing fabricated results.

The agent does not fabricate successful weather, resource, location, or disaster data when an external provider is unavailable.

The agent also depends on the validity of its passport, behavior contract, tool contracts, runtime configuration, and supported adapter implementations.
