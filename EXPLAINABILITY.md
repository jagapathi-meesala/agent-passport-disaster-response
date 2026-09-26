# Explainability

## Agent Overview

This repository contains a portable disaster-response agent designed to provide structured assistance for disaster-response workflows.

The agent uses a framework-independent execution core and separates agent identity, behavior contracts, capabilities, tools, adapters, verification, and runtime configuration.

The agent is designed to be inspectable, reproducible, and portable across supported execution adapters.

---

## 1. Agent Identity

Agent name: DisasterResponseAgent

Agent manifest: `agent.yaml`

Agent identity and behavioral principles: `SOUL.md`

Passport definition: `config/passport.json`

The OpenGAP-compatible manifest provides the portable agent identity metadata.

The passport provides the declared capabilities, supported input/output types, authorized tools, and contract version.

---

## 2. Agent Purpose

The purpose of the agent is to support disaster-response workflows using structured, verifiable execution.

The agent supports the following declared capabilities:

- situational_assessment
- logistics_coordination
- resource_allocation
- weather_monitoring
- resource_location

The agent must operate only within the capabilities declared by its passport.

It must not claim successful execution of capabilities that are not declared or authorized.

---

## 3. Inputs

The framework-independent request contract accepts structured agent requests.

A request may contain:

- request identifier
- user input
- optional context
- requested capabilities

Input is validated before capability or tool execution begins.

Invalid requests are rejected instead of being executed.

---

## 4. Outputs

The agent produces a structured response.

The response can communicate:

- request identifier
- execution status
- result
- selected capabilities
- selected tools
- execution metadata
- structured errors

Possible execution outcomes include successful completion, failure, or waiting for required external tool configuration.

The response therefore allows a consumer to determine what was requested, what was authorized, what tools were involved, and whether execution completed.

---

## 5. Decision-Making Process

The agent does not authorize an operation solely because it was requested by the user.

Authorization is determined from the loaded passport and tool contracts.

The decision process is:

```text
Request
   |
   v
Validate request
   |
   v
Load passport
   |
   v
Validate requested capability
   |
   +---- unsupported ----> Reject request
   |
   v
Discover tool
   |
   v
Check tool availability
   |
   v
Check passport authorization
   |
   v
Validate tool input
   |
   v
Execute tool
   |
   v
Validate tool output
   |
   v
Generate structured response
