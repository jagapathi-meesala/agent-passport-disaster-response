# Explainability

## Agent Overview

This repository contains a portable disaster-response agent designed to provide structured assistance for disaster-response workflows.

The agent uses a framework-independent execution core and separates agent identity, behavior contracts, capabilities, tools, adapters, verification, and runtime configuration.

The design allows the agent to be inspected, tested, verified, and executed through supported adapters without making the core dependent on a single AI framework.

---

## Decision

The agent decides whether a requested operation can be executed by validating the request, loading the passport, checking the requested capability, discovering the required tool, and validating authorization.

The decision is based on the loaded passport, declared capabilities, tool contracts, authorization rules, and runtime tool availability.

A requested capability is accepted only when it is declared by the loaded passport.

A tool is selected only when it exists, is enabled, is authorized by the passport, and satisfies its input contract.

Unsupported capabilities are rejected rather than executed.

The agent therefore separates user intent from executable authorization.

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
