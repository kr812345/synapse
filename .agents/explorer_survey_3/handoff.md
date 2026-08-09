# Handoff Report — Departments Survey (Survey Explorer 3)

## 1. Observation

A full survey of the 6 departments across the Synapse codebase (`/root/synapse`) was conducted. Below are the exact file paths, line numbers, classes, methods, and hardcoded mock responses identified:

### 1.1 Engineering Department (`/root/synapse/departments/engineering/`)
- **Files & Classes**:
  - `departments/engineering/manager.py`:
    - Class `EngineeringManager(BaseAgent)` (lines 5-33)
    - Methods: `__init__`, `allowed_tools` (`["jira", "github"]`), `forbidden_actions` (`["delete_repo"]`), `memory_access_level` (`"admin"`), `can_handle` (`"engineering" in task or "code" in task`), `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 23)**: `return {"status": "success", "task": task, "result": "mocked engineering manager result"}`
  - `departments/engineering/backend_worker.py`:
    - Class `BackendWorker(BaseAgent)` (lines 4-31)
    - Methods: `__init__`, `allowed_tools` (`["terminal", "ide"]`), `forbidden_actions` (`["delete_database"]`), `memory_access_level` (`"high"`), `can_handle` (`"backend" in task or "api" in task`), `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 21)**: `return {"status": "success", "task": task, "result": "mocked backend result"}`
- **Missing Components**: Frontend Worker, QA Worker, DevOps Worker mentioned in TDD 01 §1.3.

### 1.2 Research Department (`/root/synapse/departments/research/`)
- **Files & Classes**:
  - `departments/research/manager.py`:
    - Class `ResearchManager(BaseAgent)` (lines 4-31)
    - Methods: `__init__`, `allowed_tools` (`["delegate", "summarize"]`), `forbidden_actions` (`["direct_execution"]`), `memory_access_level` (`"department_wide"`), `can_handle`, `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Stub (line 21)**: `return {"status": "delegated", "task": task}` (does not dispatch tasks or invoke Model Router/Kernel).
  - Workers in `departments/research/workers/`:
    - `github.py` -> `GithubWorker(BaseAgent)` (lines 4-31), `execute` **Stub (line 21)**: `return {"status": "success", "source": "github", "data": []}`
    - `hn.py` -> `HNWorker(BaseAgent)` (lines 4-31), `execute` **Stub (line 21)**: `return {"status": "success", "source": "hn", "data": []}`
    - `product_hunt.py` -> `ProductHuntWorker(BaseAgent)` (lines 4-31), `execute` **Stub (line 21)**: `return {"status": "success", "source": "product_hunt", "data": []}`
    - `reddit.py` -> `RedditWorker(BaseAgent)` (lines 4-31), `execute` **Stub (line 21)**: `return {"status": "success", "source": "reddit", "data": []}`
    - `twitter.py` -> `TwitterWorker(BaseAgent)` (lines 4-31), `execute` **Stub (line 21)**: `return {"status": "success", "source": "twitter", "data": []}`

### 1.3 Marketing Department (`/root/synapse/departments/marketing/`)
- **Files & Classes**:
  - `departments/marketing/manager.py`:
    - Class `MarketingManager(BaseAgent)` (lines 5-33)
    - Methods: `__init__`, `allowed_tools` (`["analytics", "campaign_manager"]`), `forbidden_actions` (`["spend_over_budget"]`), `memory_access_level` (`"admin"`), `can_handle`, `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 23)**: `return {"status": "success", "task": task, "result": "mocked marketing manager result"}`
  - `departments/marketing/social_worker.py`:
    - Class `SocialWorker(BaseAgent)` (lines 4-31)
    - Methods: `__init__`, `allowed_tools` (`["twitter", "linkedin"]`), `forbidden_actions` (`["post_without_approval"]`), `memory_access_level` (`"medium"`), `can_handle`, `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 21)**: `return {"status": "success", "task": task, "result": "mocked social media result"}`
- **Missing Components**: Content Agent, SEO Tool mentioned in TDD 01 §1.3.

### 1.4 Sales Department (`/root/synapse/departments/sales/`)
- **Files & Classes**:
  - `departments/sales/` directory exists as an **EMPTY DIRECTORY** (0 files, 0 lines of code).
  - No manager, no workers, no `__init__.py`.
- **Status**: Completely unwritten stub directory.

### 1.5 Personal Department (`/root/synapse/departments/personal/`)
- **Files & Classes**:
  - `departments/personal/manager.py`:
    - Class `PersonalManager(BaseAgent)` (lines 5-33)
    - Methods: `__init__`, `allowed_tools` (`["contacts", "finances"]`), `forbidden_actions` (`["authorize_payments"]`), `memory_access_level` (`"admin"`), `can_handle`, `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 23)**: `return {"status": "success", "task": task, "result": "mocked personal manager result"}`
  - `departments/personal/assistant_worker.py`:
    - Class `AssistantWorker(BaseAgent)` (lines 4-31)
    - Methods: `__init__`, `allowed_tools` (`["calendar", "email"]`), `forbidden_actions` (`["delete_emails"]`), `memory_access_level` (`"high"`), `can_handle`, `execute`, `validate`, `report`, `remember`.
    - **Hardcoded Mock (line 21)**: `return {"status": "success", "task": task, "result": "mocked assistant result"}`
- **Missing Components**: Life Planner, Email Agent, Calendar Agent mentioned in TDD 01 §1.3.

### 1.6 Echo Department (`/root/synapse/departments/echo/`)
- **Files & Classes**:
  - `departments/echo/echo_manager.py`:
    - Class `EchoDepartment(Module)` (lines 7-30)
    - Methods: `__init__`, `name` (`"echo_department"`), `set_kernel`, `handle_event`.
    - Behavior: Directly responds to `event_type == "ping"` with an Event of `event_type == "pong"`.
- **Status**: Utility/loopback module for event routing verification.

### 1.7 Existing Pytest Test Suite (`/root/synapse/tests/`)
Command executed: `PYTHONPATH=. ./.venv/bin/pytest`
Result: 9 passing tests across 7 files (`test_base_agent.py`, `test_kernel.py`, `test_memory.py`, `test_model_router.py`, `test_registry.py`, `test_scheduler.py`, `test_tool_registry.py`).
**Critical Gap**: Zero tests exist for any of the 6 departments (`tests/test_engineering.py`, `tests/test_research.py`, `tests/test_marketing.py`, `tests/test_sales.py`, `tests/test_personal.py`, `tests/test_echo.py` are all missing).

---

## 2. Logic Chain

1. **Requirement Mapping**: Requirement R1 (`ORIGINAL_REQUEST.md`) explicitly demands removing all hardcoded mock responses (e.g. `"mocked engineering manager result"`) in all 6 Departments and implementing real task execution logic.
2. **Architecture Compliance**: According to `docs/architecture.md` and TDDs (`docs/tdd/01_overall_architecture.md`, `02_module_responsibilities.md`, `04_agent_lifecycle.md`, `06_event_system.md`), agents in departments must:
   - Accept tasks assigned via Event Bus / Kernel / Agent Registry.
   - Use `ModelRouter` via `model.request_execution` events (or direct model router interaction) to execute LLM inferences instead of returning hardcoded strings.
   - Use `ToolRegistry` to run allowed tools.
   - Generate artifacts (`report()`) and store atomic knowledge into `MemoryEngine` (`remember()`).
3. **Department Gaps**:
   - `EngineeringManager` & `BackendWorker`: hardcoded strings -> need real execution & event handling.
   - `ResearchManager` & 5 workers (GitHub, HN, ProductHunt, Reddit, Twitter): return empty `data: []` or `delegated` stubs -> need real data processing and delegation logic.
   - `MarketingManager` & `SocialWorker`: hardcoded strings -> need real campaign content generation & artifact output.
   - `Sales`: empty directory -> needs full implementation of `SalesManager` and worker(s).
   - `PersonalManager` & `AssistantWorker`: hardcoded strings -> need real schedule/assistant handling & memory persistence.
   - `EchoDepartment`: works for basic ping/pong, needs dedicated test file `tests/test_echo.py`.
4. **Testing Obligation**: Acceptance Criteria requires `pytest` test files for every department that programmatically verify component data processing and event routing without hardcoded strings.

---

## 3. Caveats

- **Sales Department**: Since `departments/sales/` is completely empty, the implementer must create `__init__.py`, `manager.py`, and worker modules from scratch.
- **Model Router Integration**: Department worker `execute()` calls currently accept a raw `task`. For unit test predictability, tests should mock or inject the Model Router / Kernel so tests do not make external HTTP calls, while ensuring the agents themselves invoke the execution workflow dynamically.
- **Unimplemented Worker Roles**: TDD 01 mentions additional worker roles (Frontend, QA, DevOps, Content, SEO, LifePlanner). These can be added as specialized worker classes under their respective department folders to complete the workforce hierarchy.

---

## 4. Conclusion

All 6 departments require backend logic replacement or creation:
1. **Engineering**: Replace mocks in `EngineeringManager` and `BackendWorker`.
2. **Research**: Implement actual task delegation in `ResearchManager` and output synthesis across `GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker`.
3. **Marketing**: Replace mocks in `MarketingManager` and `SocialWorker`.
4. **Sales**: Scaffold and implement `SalesManager` and `SalesWorker` in `departments/sales/`.
5. **Personal**: Replace mocks in `PersonalManager` and `AssistantWorker`.
6. **Echo**: Validate and preserve `EchoDepartment` ping/pong module.
7. **Test Suite**: Write 6 dedicated test files in `tests/` (`test_engineering.py`, `test_research.py`, `test_marketing.py`, `test_sales.py`, `test_personal.py`, `test_echo.py`).

---

## 5. Verification Method

To verify the departments survey findings and future implementations:
1. Run `PYTHONPATH=. ./.venv/bin/pytest` in `/root/synapse` to verify existing tests pass.
2. Check file paths and lines:
   - `view_file` on `departments/engineering/manager.py` (line 23)
   - `view_file` on `departments/engineering/backend_worker.py` (line 21)
   - `view_file` on `departments/marketing/manager.py` (line 23)
   - `view_file` on `departments/marketing/social_worker.py` (line 21)
   - `view_file` on `departments/personal/manager.py` (line 23)
   - `view_file` on `departments/personal/assistant_worker.py` (line 21)
   - `view_file` on `departments/research/manager.py` (line 21)
   - Check empty directory `departments/sales/`

---

## 6. Feature Inventory Additions

Below is the detailed list of enumerated features and requirements for each of the 6 departments:

### 6.1 Feature Inventory: Engineering Department
- **F-ENG-1**: Real task execution in `EngineeringManager` (`departments/engineering/manager.py`).
  - *Requirement*: Remove `"mocked engineering manager result"`. Accept coding/architecture tasks, break down or delegate to workers, route requests to Model Router / Tool Registry, validate output, and return structured result.
- **F-ENG-2**: Real task execution in `BackendWorker` (`departments/engineering/backend_worker.py`).
  - *Requirement*: Remove `"mocked backend result"`. Process API/backend coding tasks using allowed tools (`terminal`, `ide`), emit artifacts/code patches, store knowledge in `MemoryEngine`.
- **F-ENG-3**: Expanded workforce (Optional/Enhancement).
  - *Requirement*: Implement `FrontendWorker`, `QAWorker`, `DevOpsWorker` under `departments/engineering/` as defined in TDD 01 §1.3.
- **F-ENG-4**: Unit & Integration Test (`tests/test_engineering.py`).
  - *Requirement*: Test `EngineeringManager` and `BackendWorker` task handling, capability verification (`can_handle`), tool permission checks (`allowed_tools`), and event bus integration.

### 6.2 Feature Inventory: Research Department
- **F-RES-1**: Task Delegation & Aggregation in `ResearchManager` (`departments/research/manager.py`).
  - *Requirement*: Replace static `{"status": "delegated"}`. Parse research requests, delegate to platform workers (GitHub, HN, ProductHunt, Reddit, Twitter), synthesize worker findings into a comprehensive research artifact (`.md`), store knowledge to `MemoryEngine`.
- **F-RES-2**: Platform Worker Data Processing (`departments/research/workers/`).
  - *Requirement*: Replace empty `data: []` in `GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker`. Execute query searches via tool registry/APIs, return parsed findings, and handle errors.
- **F-RES-3**: Unit & Integration Test (`tests/test_research.py`).
  - *Requirement*: Test `ResearchManager` delegation and multi-source worker result aggregation.

### 6.3 Feature Inventory: Marketing Department
- **F-MKT-1**: Real Campaign Management in `MarketingManager` (`departments/marketing/manager.py`).
  - *Requirement*: Remove `"mocked marketing manager result"`. Process marketing campaign tasks, coordinate with social/content workers, output campaign artifacts.
- **F-MKT-2**: Content & Social Media Generation in `SocialWorker` (`departments/marketing/social_worker.py`).
  - *Requirement*: Remove `"mocked social media result"`. Generate platform-specific social posts (Twitter, LinkedIn), validate against forbidden actions (`post_without_approval`), emit content artifacts.
- **F-MKT-3**: Expanded workforce (Optional/Enhancement).
  - *Requirement*: Implement `ContentWorker` and `SEOWorker` in `departments/marketing/`.
- **F-MKT-4**: Unit & Integration Test (`tests/test_marketing.py`).
  - *Requirement*: Test campaign execution, tool validation, and artifact creation.

### 6.4 Feature Inventory: Sales Department
- **F-SLS-1**: Sales Department Scaffold (`departments/sales/`).
  - *Requirement*: Create `departments/sales/__init__.py`, `departments/sales/manager.py` (`SalesManager`), and `departments/sales/outreach_worker.py` (`SalesWorker`).
- **F-SLS-2**: `SalesManager` Implementation.
  - *Requirement*: Inherit `BaseAgent`, role `"manager"`, department `"sales"`, allowed tools (`["crm", "email_outreach"]`), forbidden actions (`["sign_contracts"]`), handle lead generation & strategy tasks via Model Router.
- **F-SLS-3**: `SalesWorker` Implementation.
  - *Requirement*: Inherit `BaseAgent`, handle outreach/email draft generation, emit sales pitch artifacts.
- **F-SLS-4**: Unit & Integration Test (`tests/test_sales.py`).
  - *Requirement*: Test sales task handling, permissions, and contract compliance.

### 6.5 Feature Inventory: Personal Department
- **F-PRS-1**: Assistant & Life Management in `PersonalManager` (`departments/personal/manager.py`).
  - *Requirement*: Remove `"mocked personal manager result"`. Manage personal schedules, task planning, and financial/contact tool oversight.
- **F-PRS-2**: Scheduling & Email in `AssistantWorker` (`departments/personal/assistant_worker.py`).
  - *Requirement*: Remove `"mocked assistant result"`. Process schedule/calendar/email tasks using allowed tools (`calendar`, `email`), enforce forbidden actions (`delete_emails`), persist preferences to `MemoryEngine`.
- **F-PRS-3**: Unit & Integration Test (`tests/test_personal.py`).
  - *Requirement*: Test personal assistant task execution and memory recall.

### 6.6 Feature Inventory: Echo Department
- **F-ECH-1**: Kernel Event Loopback in `EchoDepartment` (`departments/echo/echo_manager.py`).
  - *Requirement*: Maintain `EchoDepartment` event handling for `ping` -> `pong` system diagnostics.
- **F-ECH-2**: Unit & Integration Test (`tests/test_echo.py`).
  - *Requirement*: Dedicated test verifying `EchoDepartment` module registration and kernel event ping/pong routing.
