# Agent Passport Specification

## Overview

An **Agent Passport** is a standardized, machine-readable identity document and capability manifest for AI agents. It serves as a verifiable credential that declares an agent's identity, software version, operational role, permitted capabilities, supported input/output formats, and authorized tools.

## Why Our Agent Uses a Passport

In disaster response operations, AI agents operate across heterogeneous environments (on-premise emergency nodes, cloud hubs, edge devices) managed by diverse response organizations. The Agent Passport guarantees:

1. **Framework-Agnostic Portability**: The agent core logic relies on passport declarations rather than hardcoded configuration or vendor-specific frameworks.
2. **Zero-Code Metadata Updates**: Capabilities, permitted tools, input/output types, and version contracts can be updated by editing external JSON files (`config/passport.json`) without modifying Python source code.
3. **Strict Validation & Boundary Enforcement**: Ensures unauthorized tools or invalid capabilities cannot be invoked at runtime.

## Passport Schema Fields

| Field Name | Type | Description | Required | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `passport_version` | String | Version of the passport specification | Yes | Valid semver (`X.Y.Z`) |
| `agent_id` | String | Unique non-empty agent instance ID | Yes | Non-empty, whitespace stripped |
| `name` | String | Human-readable agent instance name | Yes | Non-empty, whitespace stripped |
| `version` | String | Agent implementation semver version | Yes | Valid semver (`X.Y.Z`) |
| `description` | String | Detailed description of role and scope | Yes | Non-empty, whitespace stripped |
| `capabilities` | List[String] | Declared functional capabilities | Yes | Non-empty list, items unique |
| `input_types` | List[String] | Accepted input data formats | Yes | Non-empty list, items unique |
| `output_types` | List[String] | Produced output data formats | Yes | Non-empty list, items unique |
| `tools` | List[String] | List of authorized tool names | Yes | Unique items |
| `contract_version` | String | Target contract semver version | Yes | Valid semver (`X.Y.Z`) |

Optional metadata fields:
- `issuer_id`: Identity of the issuing authority.
- `issue_timestamp`: ISO 8601 issuance timestamp.
- `expiration_timestamp`: Optional validity boundary.
- `signature`: Cryptographic signature for authenticity verification.

## Validation Rules

1. **Required Fields**: All required fields must be present in the configuration payload.
2. **Non-Empty Strings**: `agent_id`, `name`, and `description` must contain non-whitespace characters.
3. **Semantic Versioning**: `passport_version`, `version`, and `contract_version` must match `X.Y.Z` format.
4. **List Uniqueness**: `capabilities`, `tools`, `input_types`, and `output_types` must contain unique elements without duplicates.
5. **Non-Empty Lists**: `capabilities`, `input_types`, and `output_types` must contain at least one valid entry.

## Dynamic Passport Loading

The passport is loaded dynamically at runtime via `PassportManager.load_from_file()` or `PassportManager.load_from_dict()`. 

- The active configuration path is controlled dynamically by the `PASSPORT_FILE_PATH` environment variable (defaulting to `config/passport.json`).
- Changes to `config/passport.json` take effect instantly on re-load without restarting or recompiling Python core code.

## Running Tests

Execute the unit test suite:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
