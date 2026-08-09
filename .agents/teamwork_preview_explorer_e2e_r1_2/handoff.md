# Handoff Report — E2E Testing Orchestrator Department Analysis & Testable Contracts

## 1. Observation

### Codebase Infrastructure & Department State
1. **Kernel & Event Bus Interface**:
   - `shared/interfaces.py:4-14`: `Module(ABC)` requires `name` (property) and `async handle_event(event: Event) -> None`.
   - `shared/models.py:6-12`: `Event` envelope schema (`id`, `source`, `destination`, `event_type`, `payload`, `timestamp`).
   - `kernel/kernel.py:8-28`: `Kernel` implements `KernelInterface`. Manages `self.modules`, handles dynamic module registration (`register_module`), injects kernel reference (`set_kernel`), and routes events via `EventBus`.
   - `events/event_bus.py:24-43`: Unicast routing (`destination == module.name`) and Broadcast routing (`destination == "*"`).

2. **Core Subsystems**:
   - `models/model_router.py:28-52`: Handles `model.request_execution` events, chooses model tier (`Gemini Flash`, `OpenRouter`, `Antigravity CLI`), and returns `model.execution_complete`.
   - `agents/registry.py:8-65`: `AgentRegistry(Module)` stores `AgentContract` instances, handles `registry.register_agent` and `registry.find_agent` events.
   - `memory/memory_engine.py:11-194`: `MemoryEngine(Module)` backed by SQLite database. Stores tables `events`, `tasks`, `artifacts`, `knowledge_graph`, `agents`, `metrics`. Handles `memory.store_knowledge` and `memory.query_knowledge`.
   - `scheduler/scheduler.py:9-136`: `Scheduler(Module)` processes `task.create` and `dag.create` events, orchestrates execution flow (`Scheduler` -> `AgentRegistry` -> `ModelRouter` -> requester), updates task status (`pending` -> `scheduling` -> `agent_assigned` -> `completed`), and fires `task.complete` / `dag.complete`.

3. **Tool Registry**:
   - `tools/tool_registry.py:17-35`: `ToolRegistry` registers `ToolInterface` objects and executes tools via `execute_tool(agent, name, **kwargs)`. Enforces permission check: `if name not in agent.allowed_tools(): raise PermissionDenied(...)`.
   - `tools/library/browser.py:4-20`: `BrowserTool(ToolInterface)` with `name = "browser"`, required_permissions = `["web_read"]`.

4. **Department Implementations**:
   - **Echo Department** (`departments/echo/echo_manager.py:7-30`): Implements `Module`. Listens for `event_type == "ping"`, emits `event_type == "pong"` with `payload={"original_payload": event.payload}`.
   - **Engineering Department** (`departments/engineering/`):
     - `manager.py:5-23`: `EngineeringManager(BaseAgent)` returns `"mocked engineering manager result"`. Tools: `["jira", "github"]`.
     - `backend_worker.py:4-21`: `BackendWorker(BaseAgent)` returns `"mocked backend result"`. Tools: `["terminal", "ide"]`.
     - Missing workers per `PROJECT.md` (F-ENG-3): `QAWorker`, `DevOpsWorker`.
   - **Research Department** (`departments/research/`):
     - `manager.py:4-22`: `ResearchManager(BaseAgent)` returns `{"status": "delegated", "task": task}`. Tools: `["delegate", "summarize"]`.
     - Workers in `departments/research/workers/`: `github.py` (`GithubWorker`), `hn.py` (`HNWorker`), `product_hunt.py` (`ProductHuntWorker`), `reddit.py` (`RedditWorker`), `twitter.py` (`TwitterWorker`). All currently return static stub dicts (`{"status": "success", "source": "...", "data": []}`).
   - **Marketing Department** (`departments/marketing/`):
     - `manager.py:5-23`: `MarketingManager(BaseAgent)` returns `"mocked marketing manager result"`. Tools: `["analytics", "campaign_manager"]`.
     - `social_worker.py:4-21`: `SocialWorker(BaseAgent)` returns `"mocked social media result"`. Tools: `["twitter", "linkedin"]`.
     - Missing worker per `PROJECT.md` (F-MKT-3): `ContentWorker`.
   - **Sales Department** (`departments/sales/`):
     - Directory exists but is completely empty.
     - Required components per `PROJECT.md` (F-SLS-1..3): `SalesManager(BaseAgent)` (tools: `["crm", "lead_gen"]`) and `OutreachWorker(BaseAgent)` / `SalesWorker` (tools: `["email_draft", "pitch_gen"]`).
   - **Personal Department** (`departments/personal/`):
     - `manager.py:5-23`: `PersonalManager(BaseAgent)` returns `"mocked personal manager result"`. Tools: `["contacts", "finances"]`.
     - `assistant_worker.py:4-21`: `AssistantWorker(BaseAgent)` returns `"mocked assistant result"`. Tools: `["calendar", "email"]`.

5. **Test Suite Baseline Execution**:
   - Command: `PYTHONPATH=. ./.venv/bin/pytest`
   - Result: 9 tests passed, 44 deprecation/warning messages.
   - Warning sources: `PytestCollectionWarning` on `TestClient` in `tests/test_kernel.py:8`, and `datetime.utcnow()` deprecations across `shared/models.py`, `memory/memory_engine.py`.

---

## 2. Logic Chain

1. **Kernel-Module Interface Requirement**:
   - `Kernel.register_module(module)` requires `module` to be an instance of `Module` (implementing `name` property and `async handle_event(event)`).
   - Currently, only `EchoDepartment` implements `Module` directly. Department managers (`EngineeringManager`, `ResearchManager`, `MarketingManager`, `PersonalManager`, and future `SalesManager`) inherit `BaseAgent`, which is an agent contract abstraction, not a `Module`.
   - **Inference**: To connect `BaseAgent` departments to the Kernel, a `BaseDepartmentModule` adapter (or direct module wrapper) is required (e.g. `EngineeringDepartment(Module)` wrapping `EngineeringManager`). This adapter receives `Event` objects, invokes agent tasks, and emits completed task events back into the `Kernel`.

2. **Mock Replacement & Execution Routing**:
   - Requirements R1 and features F-ENG-1, F-ENG-2, F-RES-1, F-RES-2, F-MKT-1, F-MKT-2, F-PRS-1, F-PRS-2 mandate removing all hardcoded string returns (`"mocked..."`) and static stubs.
   - **Inference**: Department managers must process task descriptions dynamically, delegate subtasks to specialized worker agents, call registered tools via `ToolRegistry`, query/store state in `MemoryEngine`, or request LLM execution via `ModelRouter`.

3. **Tool Permission Enforcement**:
   - `ToolRegistry.execute_tool(agent, name, **kwargs)` checks if `name in agent.allowed_tools()`.
   - **Inference**: Each worker agent must declare all required tools in `allowed_tools()`. Attempts by unauthorized workers to call restricted tools must raise `PermissionDenied`.

---

## 3. Caveats

- **Read-Only Scope**: This analysis was conducted strictly without modifying codebase files outside `.agents/teamwork_preview_explorer_e2e_r1_2/`.
- **Mock LLM Adapters for E2E Tests**: To keep automated E2E tests deterministic, fast, and offline-compatible, LLM generation in `ModelRouter` and API tool calls (GitHub, Twitter, Reddit, HN, ProductHunt) during tests should use structured test adapters or mock responses rather than un-mocked external network requests.

---

## 4. Conclusion & Testable Contracts for the 6 Departments

### A. Summary of Department Inventory

| Department | Module Name | Manager Class | Worker Agents | Required Tools | Event Handlers / Topics |
|------------|-------------|---------------|---------------|----------------|------------------------|
| **Echo** | `echo_department` | N/A (`EchoDepartment`) | None | None | In: `ping`<br>Out: `pong` |
| **Engineering** | `engineering_department` | `EngineeringManager` | `BackendWorker`, `QAWorker`, `DevOpsWorker` | `jira`, `github`, `terminal`, `ide` | In: `department.execute_task`, `engineering.task`<br>Out: `department.task_completed` |
| **Research** | `research_department` | `ResearchManager` | `GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker` | `delegate`, `summarize`, `github_api_search`, `hn_api_search`, `ph_api_search`, `reddit_api_search`, `twitter_api_search` | In: `department.execute_task`, `research.query`<br>Out: `department.task_completed`, `memory.store_knowledge` |
| **Marketing** | `marketing_department` | `MarketingManager` | `SocialWorker`, `ContentWorker` | `analytics`, `campaign_manager`, `twitter`, `linkedin`, `content_generator` | In: `department.execute_task`, `marketing.campaign`<br>Out: `department.task_completed` |
| **Sales** | `sales_department` | `SalesManager` | `OutreachWorker` (SalesWorker) | `crm`, `lead_gen`, `email_draft`, `pitch_gen` | In: `department.execute_task`, `sales.lead`<br>Out: `department.task_completed` |
| **Personal** | `personal_department` | `PersonalManager` | `AssistantWorker` | `contacts`, `finances`, `calendar`, `email` | In: `department.execute_task`, `personal.schedule`<br>Out: `department.task_completed` |

---

### B. Detailed Testable Contracts by Department

#### 1. Echo Department Contract
- **Input Event**:
  ```python
  Event(source="test_runner", destination="echo_department", event_type="ping", payload={"message": "hello"})
  ```
- **Output Event**:
  ```python
  Event(source="echo_department", destination="test_runner", event_type="pong", payload={"original_payload": {"message": "hello"}})
  ```
- **Assertions**:
  - `event.source == "echo_department"`
  - `event.event_type == "pong"`
  - `event.payload["original_payload"] == {"message": "hello"}`

#### 2. Engineering Department Contract
- **Input Event**:
  ```python
  Event(
      source="scheduler",
      destination="engineering_department",
      event_type="department.execute_task",
      payload={"task_id": "eng-101", "task_description": "Implement REST endpoint for user profiles and run unit tests"}
  )
  ```
- **Output Event**:
  ```python
  Event(
      source="engineering_department",
      destination="scheduler",
      event_type="department.task_completed",
      payload={
          "task_id": "eng-101",
          "status": "success",
          "department": "engineering",
          "executed_by": ["EngineeringManager", "BackendWorker", "QAWorker"],
          "result": {
              "code_summary": "Created GET /api/v1/users/{id} endpoint",
              "tests_passed": True,
              "artifacts": ["/path/to/user_controller.py"]
          }
      }
  )
  ```
- **Assertions**:
  - `payload["status"] == "success"`
  - `payload["result"]` does **NOT** contain `"mocked engineering manager result"` or `"mocked backend result"`.
  - Contains subtask outputs from `BackendWorker` and `QAWorker`.

#### 3. Research Department Contract
- **Input Event**:
  ```python
  Event(
      source="scheduler",
      destination="research_department",
      event_type="department.execute_task",
      payload={"task_id": "res-201", "task_description": "Research AI OS projects on GitHub and Hacker News"}
  )
  ```
- **Output Event**:
  ```python
  Event(
      source="research_department",
      destination="scheduler",
      event_type="department.task_completed",
      payload={
          "task_id": "res-201",
          "status": "success",
          "department": "research",
          "findings": [
              {"source": "github", "data": [{"repo": "synapse-ai", "stars": 1500}]},
              {"source": "hn", "data": [{"title": "Show HN: Synapse AI OS", "points": 320}]}
          ],
          "summary": "Synthesized 2 sources on AI OS projects.",
          "knowledge_id": "know-res-201"
      }
  )
  ```
- **Assertions**:
  - `ResearchManager` delegates query to `GithubWorker` and `HNWorker`.
  - Emits `memory.store_knowledge` to `MemoryEngine`.
  - `payload["status"] == "success"` and findings are aggregated (not static `{"status": "delegated"}`).

#### 4. Marketing Department Contract
- **Input Event**:
  ```python
  Event(
      source="scheduler",
      destination="marketing_department",
      event_type="department.execute_task",
      payload={"task_id": "mkt-301", "task_description": "Launch social media campaign for Synapse v1.0 release"}
  )
  ```
- **Output Event**:
  ```python
  Event(
      source="marketing_department",
      destination="scheduler",
      event_type="department.task_completed",
      payload={
          "task_id": "mkt-301",
          "status": "success",
          "department": "marketing",
          "campaign": {
              "social_posts": [{"platform": "twitter", "content": "Excited to launch Synapse v1.0! #AI #OS"}],
              "blog_draft": "Synapse v1.0 is here...",
              "target_audience": "Developers & AI Engineers"
          }
      }
  )
  ```
- **Assertions**:
  - `MarketingManager` routes post creation to `SocialWorker` and copy drafting to `ContentWorker`.
  - `payload["result"]` does **NOT** contain `"mocked marketing manager result"` or `"mocked social media result"`.

#### 5. Sales Department Contract
- **Input Event**:
  ```python
  Event(
      source="scheduler",
      destination="sales_department",
      event_type="department.execute_task",
      payload={"task_id": "sls-401", "task_description": "Qualify inbound lead Acme Corp and draft outreach pitch"}
  )
  ```
- **Output Event**:
  ```python
  Event(
      source="sales_department",
      destination="scheduler",
      event_type="department.task_completed",
      payload={
          "task_id": "sls-401",
          "status": "success",
          "department": "sales",
          "lead_info": {"company": "Acme Corp", "qualification_score": 0.85},
          "email_draft": "Hi Acme team, Synapse AI OS can automate your workflows...",
          "crm_status": "contacted"
      }
  )
  ```
- **Assertions**:
  - `SalesManager` invokes `crm` / `lead_gen` tool and delegates email generation to `OutreachWorker`.
  - `payload["status"] == "success"`.

#### 6. Personal Department Contract
- **Input Event**:
  ```python
  Event(
      source="scheduler",
      destination="personal_department",
      event_type="department.execute_task",
      payload={"task_id": "prs-501", "task_description": "Schedule executive sync meeting for tomorrow at 2 PM"}
  )
  ```
- **Output Event**:
  ```python
  Event(
      source="personal_department",
      destination="scheduler",
      event_type="department.task_completed",
      payload={
          "task_id": "prs-501",
          "status": "success",
          "department": "personal",
          "schedule_result": {"event_title": "Executive Sync", "time": "14:00", "status": "scheduled"}
      }
  )
  ```
- **Assertions**:
  - `PersonalManager` delegates scheduling task to `AssistantWorker`.
  - `payload["result"]` does **NOT** contain `"mocked personal manager result"` or `"mocked assistant result"`.

---

### C. E2E Test Suite Recommendations (Tier 1 to Tier 4)

#### **Tier 1: Unit & Agent Contract Tests** (`tests/unit/` or individual department test files)
- **Target Files**: `tests/test_engineering.py`, `tests/test_research.py`, `tests/test_marketing.py`, `tests/test_sales.py`, `tests/test_personal.py`, `tests/test_echo.py`.
- **Scope**:
  - Test individual agent instantiation, `can_handle`, `allowed_tools`, `forbidden_actions`, and `memory_access_level`.
  - Verify worker `execute()` calls return functional dictionary structures instead of mock strings.
  - Verify `ToolRegistry.execute_tool` raises `PermissionDenied` when an agent invokes a tool not listed in `allowed_tools()`.

#### **Tier 2: Direct Event Bus & Kernel Module Integration Tests** (`tests/integration/`)
- **Scope**:
  - Register department module adapters (`BaseDepartmentModule`) with `Kernel`.
  - Send direct unicast events to each department (`destination="engineering_department"`, `event_type="department.execute_task"`).
  - Verify event routing via `EventBus`, event payload schemas, and response events emitted back to the Kernel.
  - Verify broadcast event (`destination="*"`, `event_type="system.shutdown"`) handling across all department modules.

#### **Tier 3: Multi-Agent Delegation & Knowledge Integration Workflows** (`tests/workflows/`)
- **Scope**:
  - Test `EngineeringManager` delegating to `BackendWorker`, `QAWorker`, and `DevOpsWorker`.
  - Test `ResearchManager` delegating across all 5 research workers (`GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker`), aggregating search data, calling `summarize`, and storing knowledge entries into `MemoryEngine` (`memory.store_knowledge`).
  - Verify `MemoryEngine.query_knowledge` returns stored research findings.
  - Test `MarketingManager` delegating to `SocialWorker` and `ContentWorker`.
  - Test `SalesManager` delegating to `OutreachWorker`.
  - Test `PersonalManager` delegating to `AssistantWorker`.

#### **Tier 4: End-to-End Task Scheduler, Model Router & Multi-Department Cascades** (`tests/e2e/`)
- **Scope**:
  - Submit `Task` or multi-task `DAG` to `Scheduler` via `task.create` / `dag.create` events.
  - Trace full async event cascade:
    1. `Scheduler` sends `registry.find_agent` to `AgentRegistry`.
    2. `AgentRegistry` finds matching department agent contract and returns `registry.agent_found`.
    3. `Scheduler` assigns task and sends `model.request_execution` to `ModelRouter`.
    4. `ModelRouter` selects model tier (`Gemini Flash`, `OpenRouter`, `Antigravity CLI`) or dispatches to Department Module Adapter.
    5. Department executes workers, runs tools via `ToolRegistry`, stores artifacts/knowledge in `MemoryEngine`.
    6. `ModelRouter` / Department emits `model.execution_complete` / `department.task_completed` to `Scheduler`.
    7. `Scheduler` updates `Task` status to `"completed"` and sends `task.complete` (and `dag.complete`) to requester.
  - Test cross-department DAG workflows (e.g. Task 1: Research AI trends -> Task 2: Engineering prototype based on research -> Task 3: Marketing post for prototype).

---

## 5. Verification Method

1. **Running the Full Pytest Suite**:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest -v
   ```
2. **Component File Inspection**:
   - Inspect `/root/synapse/departments/` to verify presence of `echo/`, `engineering/`, `research/`, `marketing/`, `sales/`, and `personal/`.
   - Inspect `/root/synapse/tools/tool_registry.py` and `/root/synapse/tools/library/`.
   - Inspect `/root/synapse/tests/` to verify tests exist for all 6 departments (`test_engineering.py`, `test_research.py`, `test_marketing.py`, `test_sales.py`, `test_personal.py`, `test_echo.py`).
3. **Invalidation Conditions**:
   - Any test returning hardcoded mock strings (e.g., `"mocked engineering manager result"`).
   - Any department failing to register as a `Module` with `Kernel`.
   - Any worker agent executing a tool outside its `allowed_tools()` without raising `PermissionDenied`.
   - Test suite pass rate below 100%.
