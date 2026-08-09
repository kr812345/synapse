# Synapse AI OS — Technical Departments Integration & System Architecture Analysis

## 1. Executive Summary

This report provides a comprehensive, evidence-based architectural analysis of the **Synapse AI OS** core infrastructure and its integration requirements for the **Technical Departments** (Engineering and Research) under **Milestone 2**.

The analysis evaluates the dynamic interactions between core infrastructure modules—`Kernel` (`kernel/kernel.py`), `EventBus` (`events/event_bus.py`), `ModelRouter` (`models/model_router.py`), `BaseDepartmentModule` (`departments/base.py`), `ToolRegistry` (`tools/tool_registry.py`), and `MemoryEngine` (`memory/memory_engine.py`)—and specifies the exact event contracts, payload structures, base class requirements, and recommended patterns needed to replace mock stubs with production-ready execution logic.

---

## 2. Infrastructure Component Interaction Matrix

| Infrastructure Module | Target File | Department Interaction Mechanism | Integration Contract / Key Method |
|---|---|---|---|
| **Kernel** | `kernel/kernel.py` | Central control plane for dynamic module registration, health tracking, and event dispatch. | `register_module(module: Module)`, `send_event(event: Event)` |
| **EventBus** | `events/event_bus.py` | Asynchronous message broker supporting unicast (`destination`), broadcast (`*`), and topic pub/sub (`fnmatch`). | `handle_event(event: Event)`, `publish(event: Event)`, `subscribe_topic(module, pattern)` |
| **ModelRouter** | `models/model_router.py` | Multi-tier LLM selection engine with heuristic routing, automatic fallback cascade, and token/cost tracking. | `event_type="model.request_execution"` -> returns `event_type="model.execution_complete"` |
| **BaseDepartmentModule** | `departments/base.py` | Adapter bridging `BaseAgent` department managers/workers to Kernel `Module` interface. | `name` -> `department.<dept_name>`, handles `department.execute_task` & `task.assigned` |
| **ToolRegistry** | `tools/tool_registry.py` | Central tool execution engine enforcing `allowed_tools` security boundaries per agent. | `event_type="tool.execute"` -> returns `tool.execution_result` or `tool.execution_failed` |
| **MemoryEngine** | `memory/memory_engine.py` | SQLite persistent storage for events, tasks, artifacts, knowledge graph, agent metrics. | `event_type="memory.store_knowledge"`, `event_type="memory.query_knowledge"` |

---

## 3. Deep-Dive Component Architecture & Department Interaction Logic

### 3.1 Kernel (`kernel/kernel.py`)
- **Module Registration (`lines 16-30`)**: When a department module (wrapped via `BaseDepartmentModule`) calls `kernel.register_module(module)`:
  1. Validates that `module` implements `Module` interface and has a valid non-empty string `name`.
  2. Registers the module in `self.modules[module.name]`.
  3. Registers the module as a subscriber in `EventBus`.
  4. Calls `module.set_kernel(self)` to inject the Kernel reference.
- **Event Routing (`lines 51-53`)**: Modules emit events via `kernel.send_event(event)`, which forwards directly to `event_bus.handle_event(event)`.
- **System Shutdown (`lines 55-65`)**: Kernel broadcasts `system.shutdown` event to `destination="*"` on system termination.

### 3.2 EventBus (`events/event_bus.py`)
- **Routing Modes (`lines 120-144`)**:
  - **Direct Unicast**: Matches `event.destination == module.name` (e.g. `destination="department.engineering"`).
  - **Broadcast**: Matches `event.destination == "*"` (delivers to all registered modules except `source`).
  - **Topic Subscriptions (`subscribe_topic`)**: Matches `event.event_type` using wildcard glob patterns (`fnmatch.fnmatch`).
- **Error Isolation Boundary (`lines 158-171`)**: Each event delivery is executed concurrently inside `safe_deliver(module)`. If a handler raises an exception:
  - Error is caught and logged.
  - Event is recorded in `self.dead_letter_queue` with error details and timestamp.
  - Execution of other handlers continues uninterrupted.

### 3.3 ModelRouter (`models/model_router.py`)
- **Multi-Tier LLM Architecture (`lines 22-40`)**:
  - **Tier 1**: `GeminiFlashAdapter` (`models/adapters/gemini.py`) — fast, low-cost, default for summaries/pings/simple tasks.
  - **Tier 2**: `OpenRouterAdapter` (`models/adapters/openrouter.py`) — standard reasoning, coding, feature implementation.
  - **Tier 3**: `AntigravityAdapter` (`models/adapters/antigravity.py`) — deep architecture, complex research, root-cause analysis.
- **Heuristic Selection (`decide_model`, lines 47-101)**:
  1. *Explicit Hint*: Payload keys `tier`, `model_hint`, `model`, or `preferred_tier`.
  2. *Keyword Matching*:
     - Tier 3: `"architecture"`, `"design"`, `"refactor"`, `"security audit"`, `"optimization"`, `"deep research"`, `"root cause"`, `"complex task"`.
     - Tier 2: `"code"`, `"feature"`, `"implement"`, `"unit test"`, `"data model"`, `"department"`, `"search"`.
     - Tier 1: `"summary"`, `"format"`, `"ping"`, `"echo"`, `"log"`, `"simple"`, `"classify"`.
  3. *Word Count Fallback*: <10 words -> Tier 1, <50 words -> Tier 2, >=50 words -> Tier 3.
- **Cascading Fallback (`generate_with_fallback`, lines 111-144)**: If primary adapter fails, automatically attempts remaining adapters in fallback chain before failing.
- **Cost Tracking (`cost_tracker.py`, lines 167-175)**: Records token usage and USD cost for every model invocation.

### 3.4 BaseAgent & BaseDepartmentModule (`departments/base.py`, `registry/sdk/base_agent.py`)
- **`BaseAgent` (`registry/sdk/base_agent.py`, lines 4-43)**: Abstract base class requiring implementation of:
  - `allowed_tools() -> List[str]`
  - `forbidden_actions() -> List[str]`
  - `memory_access_level() -> str`
  - `can_handle(task_description: str) -> bool`
  - `async execute(task: Any) -> Any`
  - `validate(result: Any) -> bool`
  - `report() -> Any`
  - `remember(knowledge: Any) -> None`
- **`BaseDepartmentModule` (`departments/base.py`, lines 9-83)**:
  - Module property `name`: standardizes module name to `department.<dept_name>` (e.g. `department.engineering`, `department.research`).
  - Handles incoming events with `event_type` in `("department.execute_task", "task.assigned")` or `destination == self.name`.
  - Extracts task data, checks `agent.can_handle(...)` if available, calls `await self.agent.execute(task_data)`.
  - On success: emits `department.task_completed` event back to `event.source`.
  - On error: emits `department.task_failed` event back to `event.source` with error message.

### 3.5 ToolRegistry (`tools/tool_registry.py`)
- **Permission Boundary (`lines 37-51`)**: Inspects `agent.allowed_tools()`. If the tool requested is not in `allowed_tools`, raises `PermissionDenied` exception.
- **Event Interface (`lines 53-106`)**: Listens for `event_type="tool.execute"`. Expects payload: `{"tool_name": str, "agent": dict or object, "kwargs": dict}`. Responds with `tool.execution_result` or `tool.execution_failed`.

### 3.6 MemoryEngine (`memory/memory_engine.py`)
- **Storage & Query Interface (`lines 108-190`)**:
  - `event_type="memory.store_knowledge"`: Stores `Knowledge` model (observation, source, confidence, category, importance, embedding, expiration) into `knowledge_graph` SQLite table. Emits `memory.knowledge_stored`.
  - `event_type="memory.query_knowledge"`: Performs substring search across observations and categories, filtering out expired items. Emits `memory.query_results`.

---

## 4. Exact Event Schemas & Contract Specification

### 4.1 Event Envelope Schema (`shared/models.py`)
```python
class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str          # Name of dispatching module (e.g. "department.engineering")
    destination: str     # Target module name or "*" for broadcast
    event_type: str      # Format: "<domain>.<action>"
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 4.2 Department Execution Events

#### Request: Department Task Execution
- **Event Type**: `department.execute_task` (or `task.assigned` / unicast to `department.<dept>`)
- **Source**: `scheduler`, `opaque_harness`, or parent department manager
- **Destination**: `department.engineering` or `department.research`
- **Payload Schema**:
```json
{
  "task": {
    "id": "eng-task-101",
    "description": "Implement authentication microservice backend with unit tests",
    "requester": "scheduler",
    "status": "pending",
    "dependencies": []
  }
}
```

#### Response: Task Completed
- **Event Type**: `department.task_completed`
- **Source**: `department.engineering` (or `department.research`)
- **Destination**: `event.source` (the requester)
- **Payload Schema**:
```json
{
  "task_id": "eng-task-101",
  "status": "success",
  "result": {
    "status": "success",
    "department": "engineering",
    "executed_by": "BackendWorker",
    "output": "API endpoints implemented cleanly",
    "artifacts": ["auth_service.py"]
  }
}
```

#### Response: Task Failed
- **Event Type**: `department.task_failed`
- **Source**: `department.engineering` (or `department.research`)
- **Destination**: `event.source` (the requester)
- **Payload Schema**:
```json
{
  "task_id": "eng-task-101",
  "status": "failed",
  "error": "Compilation error: syntax error at line 42"
}
```

### 4.3 ModelRouter Events

#### Request: Model Execution Request
- **Event Type**: `model.request_execution`
- **Source**: `department.engineering` or `department.research`
- **Destination**: `model_router`
- **Payload Schema**:
```json
{
  "task_id": "task-eng-001",
  "task_description": "Implement user authentication module with unit test suite in code",
  "system": "You are an expert backend engineer.",
  "agent": {"identity": "eng_mgr"},
  "tier": "tier2",
  "tools": ["terminal", "ide"]
}
```

#### Response: Model Execution Complete
- **Event Type**: `model.execution_complete`
- **Source**: `model_router`
- **Destination**: `event.source` (the requesting department module)
- **Payload Schema**:
```json
{
  "task_id": "task-eng-001",
  "result": {
    "status": "success",
    "executed_by": "OpenRouterAdapter",
    "agent": "eng_mgr",
    "output": "def authenticate_user(username, password): ...",
    "tokens": {
      "prompt_tokens": 120,
      "completion_tokens": 85,
      "total_tokens": 205
    },
    "cost": 0.00041
  }
}
```

---

## 5. Milestone 2 Technical Department Requirements & Gap Analysis

### 5.1 Engineering Department (`departments/engineering/`)

#### Feature Requirements
1. **`F-ENG-1` (EngineeringManager)**:
   - File: `departments/engineering/manager.py`
   - Current State: Returns static mock output `{"status": "success", "task": task, "result": "mocked engineering manager result"}` (`line 23`).
   - Target State: Must inherit `BaseAgent`, instantiate/manage sub-workers (`BackendWorker`, `QAWorker`, `DevOpsWorker`), decompose engineering tasks, dispatch to specialized workers or `ModelRouter` / `ToolRegistry`, and aggregate real results.
2. **`F-ENG-2` (BackendWorker)**:
   - File: `departments/engineering/backend_worker.py`
   - Current State: Returns static mock output `{"status": "success", "task": task, "result": "mocked backend result"}` (`line 21`).
   - Target State: Execute functional backend tasks (API development, code refactoring, data processing), handle empty code artifacts cleanly, and interact with tools (`terminal`, `ide`).
3. **`F-ENG-3` (QAWorker & DevOpsWorker)**:
   - Files: `departments/engineering/qa_worker.py`, `departments/engineering/devops_worker.py`
   - Current State: Classes are declared in E2E test files (`tests/e2e/tier1/test_tier1_engineering.py`) but do not exist in `departments/engineering/`.
   - Target State: Create production worker modules inheriting `BaseAgent`:
     - `QAWorker`: allowed tools `["pytest", "coverage_tool"]`, handles test execution & validation tasks.
     - `DevOpsWorker`: allowed tools `["docker", "kubectl", "terminal"]`, handles deployment & infrastructure tasks.
4. **`F-ENG-4` (Unit & Integration Tests)**:
   - File: `tests/test_engineering.py`
   - Target State: Create comprehensive unit & integration tests covering `EngineeringManager`, `BackendWorker`, `QAWorker`, `DevOpsWorker`, `BaseDepartmentModule` wrapping, error boundaries, tool permissions, and model routing.

---

### 5.2 Research Department (`departments/research/`)

#### Feature Requirements
1. **`F-RES-1` (ResearchManager)**:
   - File: `departments/research/manager.py`
   - Current State: Returns static mock output `{"status": "delegated", "task": task}` (`line 21`).
   - Target State: Parse research query, identify target platforms or delegate to platform workers (`GithubWorker`, `HNWorker`, `ProductHuntWorker`, `RedditWorker`, `TwitterWorker`), aggregate platform search data, invoke `ModelRouter` for report summarization, store findings in `MemoryEngine` (`memory.store_knowledge`), and output structured research reports.
   - Note on Department Property: Standardize `department` attribute to `"research"` so module name matches `department.research`.
2. **`F-RES-2` (Platform Workers)**:
   - Files: `departments/research/workers/github.py`, `hn.py`, `product_hunt.py`, `reddit.py`, `twitter.py`
   - Current State: Currently return empty static arrays `{"status": "success", "source": "...", "data": []}`.
   - Target State: Refactor workers to perform functional query searches, handle empty queries, special characters, and malformed inputs cleanly, and return structured datasets with metadata (title, url, score, content/summary).
3. **`F-RES-3` (Unit & Integration Tests)**:
   - File: `tests/test_research.py`
   - Target State: Create unit & integration test file testing `ResearchManager`, platform workers, data aggregation, knowledge memory storage, timeout error recovery, and model summarization.

---

## 6. Verification & Pytest Suite Analysis

### 6.1 Current Test Suite Status
Running `PYTHONPATH=. ./.venv/bin/pytest` produces:
- **Total Tests**: 145 passed in 5.83s.
- **Pass Rate**: 100%.
- **Tier Breakdown**:
  - Tier 1 (Basic Module Tests): 48 / 48 passed (100%)
  - Tier 2 (Error Handling & Edge Cases): 45 / 45 passed (100%)
  - Tier 3 (Router & Multi-Dept Cascades): 11 / 11 passed (100%)
  - Tier 4 (Full OS E2E Lifecycle): 6 / 6 passed (100%)
  - Other (Unit Tests): 35 / 35 passed (100%)

### 6.2 Test Harness & Helper Utilities (`tests/e2e/`)
- **`OpaqueTestHarness` (`tests/e2e/conftest.py`)**: Subclass of `Module` that records all incoming events and provides `await wait_for_event(...)` for deterministic async assertion without race conditions.
- **Fixtures**:
  - `fresh_kernel`: Clean `Kernel` instance.
  - `harness_client`: `OpaqueTestHarness` attached to `fresh_kernel`.
  - `full_os_kernel`: Kernel pre-loaded with `ModelRouter`, `AgentRegistry`, `Scheduler`, `MemoryEngine`, `EchoDepartment`, and all department modules.
- **Helpers (`tests/e2e/helpers.py`)**:
  - `assert_valid_event(event)`
  - `assert_event_matches(event, source=..., destination=..., event_type=...)`
  - `assert_valid_task(task)`
  - `assert_valid_dag(dag)`
  - `assert_valid_knowledge(knowledge)`
  - `assert_valid_cost_tracker_payload(payload)`
  - `create_test_event(...)`, `create_test_task(...)`, `create_test_knowledge(...)`

---

## 7. Recommended Design Patterns & Implementation Rules

### Rule 1: No Hardcoded Mock Strings
All hardcoded mock strings (such as `"mocked engineering manager result"`, `"mocked backend result"`, `"delegated"`) MUST be eliminated. Implement functional task processing logic that inspects input parameters and computes structured outputs.

### Rule 2: Module Interface Adherence via BaseDepartmentModule
All Department Managers MUST be wrapped with `BaseDepartmentModule(agent)` when registering with Kernel. Ensure `agent.department` is lowercased (e.g. `"engineering"`, `"research"`) so the resulting module name is consistently `department.engineering` or `department.research`.

### Rule 3: Event-Driven Communication Contract
Departments MUST communicate with infrastructure modules exclusively via Kernel events:
- Model Requests: Dispatch `event_type="model.request_execution"` to `destination="model_router"`.
- Memory Storage: Dispatch `event_type="memory.store_knowledge"` to `destination="memory_engine"`.
- Tool Invocation: Dispatch `event_type="tool.execute"` to `destination="tool_registry"`.

### Rule 4: Robust Error Boundaries & Exception Propagation
Worker failures or LLM timeouts MUST be caught gracefully. `BaseDepartmentModule` handles uncaught exceptions by emitting `department.task_failed` with the error trace, preventing system-wide crashes.

---
