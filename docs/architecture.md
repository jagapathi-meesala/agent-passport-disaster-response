# DisasterResponseAgent Architecture

## System Architecture

```
+------------------------------------------------------------------+
|                    Vanilla HTML/CSS/JS Dashboard                 |
|                        (frontend/index.html)                     |
+------------------------------------------------------------------+
|                     FastAPI REST Service Layer                   |
|                            (api/main.py)                         |
+------------------------------------------------------------------+
|            Passport Trust & Identity Verification Engine         |
|             (PassportTrustVerifier, PassportTrustResult)         |
+------------------------------------------------------------------+
|                  Portability Verification Engine                 |
|             (PortabilityVerifier, PortabilityResult)             |
+------------------------------------------------------------------+
|               Portable Framework Adapter Layer                   |
|   (AbstractFrameworkAdapter, PortableAdapter, LangChainAdapter)  |
+------------------------------------------------------------------+
|                  Passport Verification Engine                    |
+------------------------------------------------------------------+
|                   Framework-Independent Core                     |
|         (AgentCore, AgentState, BehaviorContract, Context)        |
+------------------------------------------------------------------+
|     Data Contracts (AgentRequest, AgentResponse, AgentError)     |
+------------------------------------------------------------------+
|                   Dynamic Tool Registry System                   |
|        (ToolContract, AbstractTool, ToolExecutionResult)         |
+------------------------------------------------------------------+
| Operational Tools (WeatherTool, ResourceLocationTool, Clients)   |
+------------------------------------------------------------------+
|               External Configuration & Passport Schema           |
+------------------------------------------------------------------+
```

## Step 11: End-to-End Integration & Competition Demo

Step 11 integrates all project components into a unified, competition-ready demonstration suite exposing:
1. **REST API Service** ([api/main.py](file:///home/jagapathi/Videos/agent-passport-disaster-response/api/main.py)): FastAPI server exposing endpoints for agent passport metadata, tool discovery, multi-adapter execution, and verification engines.
2. **Competition Demo Runner** ([run_demo.py](file:///home/jagapathi/Videos/agent-passport-disaster-response/run_demo.py)): Executable standalone runner showcasing the full 7-stage portable agent lifecycle with machine-readable evidence export.
3. **Vanilla Web Dashboard** ([frontend/index.html](file:///home/jagapathi/Videos/agent-passport-disaster-response/frontend/index.html)): Framework-free frontend allowing live inspection of passport metadata, tool registry, multi-adapter execution, trust, and portability verification.
4. **End-to-End Test Suite** ([tests/test_e2e_integration.py](file:///home/jagapathi/Videos/agent-passport-disaster-response/tests/test_e2e_integration.py)): Complete automated integration coverage.

---

## REST API Endpoints

The API layer ([api/main.py](file:///home/jagapathi/Videos/agent-passport-disaster-response/api/main.py)) exposes the following REST endpoints:

- `GET /passport`: Dynamically loads and returns active `AgentPassport` credential metadata.
- `GET /tools`: Dynamically retrieves registered operational tools and `ToolContract` schemas from `ToolRegistry`.
- `POST /execute`: Executes tasks via selected target adapter (`direct_core`, `portable`, `langchain`) using `AgentRequest` and `AgentResponse` contracts.
- `POST /verify/trust`: Triggers `PassportTrustVerifier` engine and returns `PassportTrustResult` JSON report.
- `POST /verify/portability`: Triggers `PortabilityVerifier` engine and returns `PortabilityResult` JSON report.

---

## Standalone Competition Demonstration Runner

The `run_demo.py` script executes the complete 7-stage agent lifecycle:

1. **Passport Trust & Identity Verification**: Validates `config/passport.json` against `BehaviorContract`.
2. **Dynamic Tool Registry Initialization**: Discovers and registers operational tools (`WeatherTool`, `ResourceLocationTool`).
3. **Direct AgentCore Execution**: Executes task directly on framework-independent `AgentCore`.
4. **PortableAdapter Execution**: Executes generic task payload through `PortableAdapter`.
5. **LangChainAdapter Execution**: Translates and executes `LangChain` message payloads via `LangChainAdapter`.
6. **Authorization Boundary Enforcement**: Verifies rejection of unauthorized capability requests.
7. **Machine-Readable Evidence Serialization**: Exports structured JSON evidence proving identity invariance and zero-hardcoding compliance.

### Execution Command:
```bash
.venv/bin/python3 run_demo.py
```

---

## Agent Passport Trust & Identity Verification Subsystem

The **Passport Trust Subsystem** ([verification/passport_trust_verifier.py](file:///home/jagapathi/Videos/agent-passport-disaster-response/verification/passport_trust_verifier.py)) provides dynamic, machine-readable trust and identity verification for `AgentPassport` credentials across runtime adapters without modifying `AgentCore` logic.

```text
                        AgentPassport (config/passport.json)
                                         │
                                         ▼
                             PassportTrustVerifier
                                         │
           ┌─────────────────────────────┼─────────────────────────────┐
           ▼                             ▼                             ▼
1. Schema & Semver          2. Contract Compliance        3. Multi-Adapter Identity
   Integrity Check             (passport.contract_version    & Authorization Check
                                == BehaviorContract.version)
           │                             │                             │
           └─────────────────────────────┼─────────────────────────────┘
                                         │
                                         ▼
                                PassportTrustResult
                        (to_dict() / to_json() Export)
```

### Key Verification Properties

1. **Schema & Semver Integrity**: Validates structural completeness (`agent_id`, `name`, `version`, `description`, `capabilities`, `input_types`, `output_types`) and semver format compliance (`X.Y.Z`).
2. **Dynamic Contract Version Verification**: Dynamically compares `passport.contract_version` against `BehaviorContract().contract_version` (`"1.0.0"`), detecting contract version mismatches cleanly.
3. **Multi-Adapter Identity Consistency**: Verifies that bound passport identity metadata (`agent_id`, `version`, `capabilities`) remains 100% consistent across Direct `AgentCore`, `PortableAdapter`, and `LangChainAdapter`.
4. **Unauthorized Capability Rejection**: Confirms that requests containing unauthorized capabilities fail with identical error classification (`status = "failed"`, `error_code = "UNSUPPORTED_CAPABILITY"`) across all execution entry points.
5. **Competition Evidence Generation**: `PassportTrustResult` exports structured JSON reports (`to_dict()`, `to_json()`) suitable for competition credential verification.

---

## Dependency Direction Rules

The dependency flow strictly enforced across the project is top-down:

```text
api / demo ──► verification ──► adapters ──► core ──► contracts / tools / passport
```

`AgentCore` contains zero imports of verifiers, adapters, or external AI frameworks (`LangChain`, `AutoGen`, `CrewAI`, `Lyzr`, `FastAPI`).

---

## Testing & Audit Verification

### Running All Unit & E2E Tests
Execute the complete test suite (175 tests):
```bash
.venv/bin/python3 -m unittest discover -s tests -p "test_*.py"
```

### Static Audit Checks
1. **Zero Hardcoded Secrets/Domain Data**: All coordinates, resource counts, weather values, and credentials loaded strictly from environment or configuration.
2. **Framework Isolation**: External frameworks (e.g. `langchain_core`) imported ONLY inside `adapters/langchain_adapter.py`.
3. **Core Immutability**: `core/*`, `passport/*`, `contracts/*`, `tools/*`, `verification/*`, and `adapters/*` remained unmodified during Step 11.
