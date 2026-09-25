# Agent Passport – Portable Disaster Response Agent

A portable, framework-agnostic AI agent architecture designed for disaster response operations. The agent uses verifiable "Agent Passports" to certify identity, capabilities, and trust boundaries across heterogeneous deployment environments.

## Architectural Principles

1. **Framework Agnostic**: Core runtime logic is completely decoupled from underlying LLM frameworks (LangChain, AutoGen, LlamaIndex, etc.).
2. **Passport-Based Identity & Trust**: Agent identity, versioning, capabilities, allowed tools, and input/output contracts are declared via external machine-readable Agent Passports (`config/passport.json`).
3. **Dynamic Environment Configuration**: Zero hardcoded business logic, credentials, locations, or operational data. All inputs are injected at runtime via environment variables and dynamic tools.
4. **Modular Capability Isolation**: Tools, verification engines, adapters, schemas, and API endpoints live in distinct modules with single responsibilities.
5. **Verifiable Passport Identity & Trust**: Machine-readable Passport Trust & Identity Verification Engine (`PassportTrustVerifier`) proving schema integrity, dynamic contract compliance, capability authorization bounds, and identity invariance across runtime adapters.
6. **End-to-End Competition Integration**: Complete REST API, interactive vanilla dashboard, automated end-to-end integration test suite, and machine-readable evidence export (`run_demo.py`).

---

## Step 11: End-to-End Integration & Competition Demo

The project includes a complete competition-ready demonstration stack:

- **`run_demo.py`**: Standalone competition demonstration runner showing the 7-stage portable agent lifecycle with machine-readable evidence output.
- **REST API (`api/main.py`)**: FastAPI server providing endpoints for passport metadata, tool discovery, multi-adapter execution, passport trust, and portability verification.
- **Vanilla Demo Dashboard (`frontend/index.html`)**: Lightweight, framework-free dashboard allowing judges to inspect passport status, discover registered tools, execute tasks across adapters, and verify trust & portability.
- **E2E Integration Test Suite (`tests/test_e2e_integration.py`)**: Automated test suite verifying all endpoints, adapter selection, unauthorized capability rejection, and evidence serialization.

---

## REST API Endpoints

- `GET /passport`: Dynamically loads and returns active `AgentPassport` credential metadata.
- `GET /tools`: Dynamically lists all registered tools in `ToolRegistry` with their input/output contracts.
- `POST /execute`: Executes disaster response tasks via target adapter (`direct_core`, `portable`, `langchain`).
- `POST /verify/trust`: Triggers `PassportTrustVerifier` engine and returns `PassportTrustResult` JSON report.
- `POST /verify/portability`: Triggers `PortabilityVerifier` engine across execution adapters and returns `PortabilityResult` JSON report.

---

## Directory Overview

- `core/`: Framework-independent core execution engine (`agent.py`), state model (`state.py`), and context (`execution.py`).
- `contracts/`: Data schemas (`schemas.py`), behavior contracts (`behavior.py`), tool contracts (`tool_interface.py`), and adapter contracts (`adapter.py`).
- `passport/`: Agent passport schema, identity metadata, loader, and manager.
- `tools/`: Operational tool implementations (`weather_tool.py`, `resource_tool.py`, clients, schemas) and dynamic tool registry (`base.py`).
- `adapters/`: Framework translation wrappers (`base.py`, `portable_adapter.py`, `langchain_adapter.py`, `registry.py`).
- `verification/`: Passport verifier (`passport_verifier.py`), portability verification engine (`portability_verifier.py`), and passport trust verifier (`passport_trust_verifier.py`).
- `config/`: Dynamic configuration management and external passport JSON specifications (`config/passport.json`).
- `api/`: REST server (`api/main.py`) exposing agent endpoints.
- `frontend/`: Lightweight vanilla HTML/CSS/JS demo dashboard (`frontend/index.html`).
- `docs/`: System architecture ([docs/architecture.md](file:///home/jagapathi/Videos/agent-passport-disaster-response/docs/architecture.md)) and standards.
- `tests/`: Test suite (175 tests) covering unit and E2E integration tests.
- `run_demo.py`: Executable standalone competition demonstration runner.

---

## Getting Started & Usage

### Prerequisites
- Python 3.10+
- `.venv` virtual environment

### 1. Running the Standalone Competition Demo (`run_demo.py`)
Run the CLI demonstration runner:
```bash
.venv/bin/python3 run_demo.py
```
*Outputs structured JSON evidence for all 7 lifecycle stages with exit code 0.*

### 2. Running All Automated Unit & E2E Tests
Run the complete test suite (175 tests):
```bash
.venv/bin/python3 -m unittest discover -s tests -p "test_*.py"
```

### 3. Running the REST API & Demo Dashboard
Start the API server:
```bash
.venv/bin/uvicorn api.main:app --reload --port 8001
```
Open `frontend/index.html` in any web browser to interact with the Live Demo Dashboard.
