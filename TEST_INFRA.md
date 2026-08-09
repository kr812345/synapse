# Synapse AI OS — E2E Test Infrastructure

This document outlines the design, architecture, methodology, feature inventory, directory structure, and execution mechanisms of the End-to-End (E2E) Test Infrastructure for Synapse AI OS.

---

## 1. E2E Test Philosophy

The Synapse AI OS E2E test suite is constructed under three non-negotiable architectural principles:

1. **Opaque-Box Verification**:
   - Tests interact with Synapse AI OS strictly through external contracts, Kernel API methods (`send_event`, `register_module`), public module events, and asynchronous message flow.
   - The test harness (`OpaqueTestHarness` via `harness_client`) subscribes non-intrusively to the Event Bus to intercept and assert event propagation, payloads, and state transitions without inspecting internal module variables or private methods.

2. **Requirement-Driven Mapping**:
   - Every single test case traces directly back to formal feature requirements specified in `PROJECT.md` (e.g., `KERN-001` through `KERN-004`, `EVTB-001` through `EVTB-007`, `MR-01` through `MR-09`, and department specs `F-ENG`, `F-RES`, `F-MKT`, `F-SLS`, `F-PRS`, `F-ECH`).
   - Every OS domain has complete lifecycle test coverage covering registration, event processing, execution, cost tracking, tool invocation, and error handling.

3. **Zero Reliance on Mock Hacks**:
   - All modules operate using genuine, fully functional asynchronous code.
   - Event routing, memory persistence (SQLite), tool execution, model selection heuristics, cost tracking calculations, and multi-department agent workflows execute real domain logic without mocked facades or artificial test shortcuts.

---

## 2. 4-Tier Test Methodology

The E2E test suite follows a structured 4-tier hierarchical testing strategy to ensure reliability across unit-level feature contracts up to enterprise-level multi-agent workflows.

```
+-----------------------------------------------------------------------+
|                       TIER 4: Real-World Workflows                    |
|   (6 E2E Multi-Agent OS Lifecycles, Incident Response & Product Release)  |
+-----------------------------------------------------------------------+
|                 TIER 3: Pairwise Cross-Feature Interactions            |
|   (11 Cascades: EventBus <-> Router <-> CostTracker <-> Departments)   |
+-----------------------------------------------------------------------+
|               TIER 2: Boundary & Corner Cases (>=5 per Domain)         |
|   (45 Tests: Edge conditions, invalid schemas, failures, limits, DLQ) |
+-----------------------------------------------------------------------+
|               TIER 1: Base Feature Coverage (>=5 per Domain)          |
|   (45 Tests + 3 Sanity: 9 OS domains base functional requirement tests) |
+-----------------------------------------------------------------------+
```

### Tier Descriptions:

- **Tier 1 — Base Feature Coverage** (45 Core Feature Tests + 3 Harness Sanity Tests):
  Validates baseline functionality for all features across all 9 OS domains. Ensures each domain satisfies minimum requirement contracts with at least 5 dedicated test cases per domain.

- **Tier 2 — Boundary & Corner Cases** (45 Boundary & Edge Tests):
  Subject all 9 OS domains to stressful edge conditions, malformed input events, missing parameters, duplicate module registrations, rate/character limit truncations, API timeouts, invalid tool arguments, and unexpected worker failures. Minimum 5 test cases per domain.

- **Tier 3 — Pairwise Cross-Feature Interactions** (11 Integration Tests):
  Evaluates integration boundaries between multiple major OS subsystems. Validates event bus routing coupled with model router execution, real-time cost tracking, multi-department task cascades (e.g., Research -> Engineering -> QA), and broadcast event handlers.

- **Tier 4 — Real-World Application Workflows** (6 E2E Workflow Tests):
  Simulates full real-world multi-agent operating system life cycles from kernel boot, module initialization, multi-department task coordination, persistence recovery, stress loads, through graceful system teardown.

---

## 3. 9 OS Domain Feature Inventory

The test infrastructure provides complete coverage across all 9 core functional domains of Synapse AI OS:

| Domain # | Domain Name | Core Component Files | Key Covered Functionality |
|---|---|---|---|
| **1** | **Kernel** | `kernel/kernel.py`, `shared/interfaces.py` | Dynamic module registration (`register_module`), `Module` interface enforcement, health checking (`check_health`), module tracking (`get_module`), system shutdown event broadcasting (`system.shutdown`). |
| **2** | **Event Bus** | `events/event_bus.py`, `shared/models.py` | Unicast event routing, pub/sub broadcast (`destination="*"`), wildcard topic subscription (`*`, `#`), decoupled async queues (`asyncio.Queue`), Dead-Letter Queue (DLQ) routing, payload validation, handler exception boundaries. |
| **3** | **Model Router** | `models/model_router.py`, `models/cost_tracker.py`, `models/adapters/` | Abstract `ModelAdapter`, `GeminiFlashAdapter` (Tier 1), `OpenRouterAdapter` (Tier 2), `AntigravityAdapter` (Tier 3), heuristic routing in `decide_model`, adapter fallback cascade, financial & token `CostTracker`, `model.request_execution` / `model.execution_complete` contract. |
| **4** | **Engineering** | `departments/engineering/` | `EngineeringManager`, `BackendWorker` (code synth), `QAWorker` (test validation), `DevOpsWorker` (container & CI/CD deployment), `ToolRegistry` tool execution. |
| **5** | **Research** | `departments/research/` | `ResearchManager`, `GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker`, functional search aggregation & trend analytics. |
| **6** | **Marketing** | `departments/marketing/` | `MarketingManager`, `SocialWorker` (post generation), `ContentWorker` (blog/article synthesis), campaign analytics tool execution. |
| **7** | **Sales** | `departments/sales/` | `SalesManager`, `OutreachWorker` (pitch drafting), CRM tool execution (`crm_manage_lead`), lead tracking and outreach workflow. |
| **8** | **Personal** | `departments/personal/` | `PersonalManager`, `AssistantWorker` (schedule execution, calendar/reminder handling, task prioritization & permissions). |
| **9** | **Echo** | `departments/echo/` | `EchoDepartment` ping/pong message processing, payload preservation, source-directed response routing. |

---

## 4. Test Directory Layout

```
/root/synapse/
├── run_e2e_tests.py                 # E2E Test Suite Runner CLI Harness Script
├── TEST_INFRA.md                    # Infrastructure & Architecture Documentation
├── TEST_READY.md                    # Verification Status & Feature Checklist
├── pytest.ini                       # Pytest configuration (asyncio mode, markers)
└── tests/                           # Test suite directory
    ├── conftest.py                  # Standard pytest fixtures
    ├── test_base_agent.py           # Unit tests for BaseAgent
    ├── test_kernel.py               # Unit tests for Kernel
    ├── test_memory.py               # Unit tests for MemoryEngine
    ├── test_model_router.py         # Unit tests for ModelRouter
    ├── test_model_router_stress.py  # Stress unit tests for ModelRouter
    ├── test_registry.py             # Unit tests for AgentRegistry
    ├── test_scheduler.py            # Unit tests for TaskScheduler
    ├── test_tool_registry.py        # Unit tests for ToolRegistry
    └── e2e/                         # End-to-End Test Suite
        ├── conftest.py              # E2E fixtures (fresh_kernel, full_os_kernel, harness_client)
        ├── helpers.py               # Assertions & test object factory functions
        ├── test_harness_sanity.py   # Harness sanity & helper validation (3 tests)
        ├── tier1/                   # Tier 1 Feature Coverage (45 tests)
        │   ├── test_tier1_echo.py
        │   ├── test_tier1_engineering.py
        │   ├── test_tier1_event_bus.py
        │   ├── test_tier1_kernel.py
        │   ├── test_tier1_marketing.py
        │   ├── test_tier1_model_router.py
        │   ├── test_tier1_personal.py
        │   ├── test_tier1_research.py
        │   └── test_tier1_sales.py
        ├── tier2/                   # Tier 2 Boundary & Corner Cases (45 tests)
        │   ├── test_tier2_echo.py
        │   ├── test_tier2_engineering.py
        │   ├── test_tier2_event_bus.py
        │   ├── test_tier2_kernel.py
        │   ├── test_tier2_marketing.py
        │   ├── test_tier2_model_router.py
        │   ├── test_tier2_personal.py
        │   ├── test_tier2_research.py
        │   └── test_tier2_sales.py
        ├── tier3/                   # Tier 3 Pairwise Cross-Feature Interactions (11 tests)
        │   ├── test_tier3_eventbus_costtracker.py
        │   ├── test_tier3_multi_department_cascades.py
        │   └── test_tier3_router_departments.py
        └── tier4/                   # Tier 4 Real-World Application Workflows (6 tests)
            ├── test_tier4_full_agent_os_lifecycle.py
            └── test_tier4_product_release_workflow.py
```

---

## 5. Test Runner Commands

### Running via E2E Harness CLI (`run_e2e_tests.py`)

- **Full E2E Suite Execution**:
  ```bash
  PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier all
  ```

- **Individual Tier Execution**:
  ```bash
  # Run Tier 1 Feature Tests only
  PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier 1

  # Run Tier 2 Boundary & Corner Cases only
  PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier 2

  # Run Tier 3 Multi-Component Integration Cascades only
  PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier 3

  # Run Tier 4 Real-World Application Workflows only
  PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier 4
  ```

### Running via Pytest Directly

- **Run all E2E Tests**:
  ```bash
  PYTHONPATH=. ./.venv/bin/pytest tests/e2e/
  ```

- **Run Full Repository Suite (Unit + E2E, 145 Tests)**:
  ```bash
  PYTHONPATH=. ./.venv/bin/pytest
  ```

- **Run Specific Tier Directory**:
  ```bash
  PYTHONPATH=. ./.venv/bin/pytest tests/e2e/tier1/
  PYTHONPATH=. ./.venv/bin/pytest tests/e2e/tier2/
  PYTHONPATH=. ./.venv/bin/pytest tests/e2e/tier3/
  PYTHONPATH=. ./.venv/bin/pytest tests/e2e/tier4/
  ```
