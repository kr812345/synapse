# E2E Infrastructure Analysis & Test Contract Report

**Agent**: `teamwork_preview_explorer`  
**Working Directory**: `/root/synapse/.agents/teamwork_preview_explorer_e2e_r1_1`  
**Date**: 2026-08-06  

---

## 1. Observation

Direct code examination of `/root/synapse/shared`, `/root/synapse/kernel`, `/root/synapse/events`, `/root/synapse/models`, `/root/synapse/docs`, `/root/synapse/PROJECT.md`, and existing test suites revealed the following structural details:

### 1.1 Core Class Specifications & Locations

1. **`shared/interfaces.py`**
   - `Module(ABC)` (lines 4-14): Abstract base class for all system modules.
     - `@property def name(self) -> str`: Abstract property returning unique module identifier string.
     - `async def handle_event(self, event: Event) -> None`: Abstract coroutine for receiving and processing events.
   - `KernelInterface(ABC)` (lines 16-23): Interface implemented by OS Kernel.
     - `def register_module(self, module: Module) -> None`
     - `async def send_event(self, event: Event) -> None`

2. **`shared/models.py`**
   - `Event(BaseModel)` (lines 6-12):
     - `id: str` (UUID4 default factory)
     - `source: str` (sender module name)
     - `destination: str` (target module name or `*` for broadcast)
     - `event_type: str` (namespaced event string, e.g. `model.request_execution`)
     - `payload: Dict[str, Any]` (event parameters/data)
     - `timestamp: datetime` (UTC timestamp, currently `datetime.utcnow`)
   - `AgentContract(BaseModel)` (lines 14-23): Agent definition metadata (`identity`, `department`, `goal`, `responsibilities`, `forbidden_actions`, `allowed_tools`, `memory_access`, `output_schema`, `confidence_score`).
   - `Task(BaseModel)` (lines 25-34): Work item schema (`id`, `description`, `requester`, `status`, `assigned_agent`, `result`, `dag_id`, `dependencies`, `created_at`).
   - `DAG(BaseModel)` (lines 36-42): Directed Acyclic Graph container (`id`, `name`, `requester`, `tasks`, `status`, `created_at`).
   - `Knowledge(BaseModel)` (lines 45-54): Structured memory item (`id`, `observation`, `source`, `confidence`, `category`, `importance`, `embedding`, `expiration`, `created_at`).

3. **`kernel/kernel.py`**
   - `Kernel(KernelInterface)` (lines 8-29):
     - `__init__()` (lines 9-11): Instantiates `self.event_bus = EventBus()` and `self.modules = {}`.
     - `register_module(module: Module) -> None` (lines 13-20): Adds module to `self.modules`, registers it as a subscriber with `self.event_bus`, and calls `module.set_kernel(self)` if available.
     - `async send_event(event: Event) -> None` (lines 22-24): Forwards `event` to `self.event_bus.handle_event(event)`.
     - `async shutdown()` (lines 26-28): Broadcasts `Event(source="kernel", destination="*", event_type="system.shutdown", payload={})`.

4. **`events/event_bus.py`**
   - `EventBus(Module)` (lines 10-44):
     - `__init__()` (lines 11-12): Initializes `self.subscribers: Dict[str, Module] = {}`.
     - `@property def name(self) -> str` (lines 14-16): Returns `"event_bus"`.
     - `register_subscriber(module: Module) -> None` (lines 18-22): Registers module in subscriber map; logs warning on duplicate registration.
     - `async handle_event(event: Event) -> None` (lines 24-44): Routes events:
       - Broadcast (`destination == "*"`): Uses `asyncio.gather` across all subscribers except `event.source`.
       - Unicast (`destination in self.subscribers`): Calls `module.handle_event(event)`.
       - Unroutable: Logs error if `destination` not in subscribers (Pending M1 Dead-Letter Queue requirement EVTB-005).

5. **`models/model_router.py`**
   - `ModelRouter(Module)` (lines 7-53):
     - `@property def name(self) -> str`: Returns `"model_router"`.
     - `set_kernel(kernel)` (lines 15-16): Injects kernel reference.
     - `decide_model(task_description: str) -> str` (lines 18-26): Word count heuristic (<10 words -> `"Gemini Flash"`, <50 words -> `"OpenRouter"`, >=50 words -> `"Antigravity CLI"`).
     - `async handle_event(event: Event) -> None` (lines 28-52): Listens for `model.request_execution`, extracts `task_id`, `task_description`, `agent`, evaluates model via `decide_model()`, generates simulated output payload, and emits `model.execution_complete` event back to `event.source`.

6. **Model Router Adapters & Cost Tracker Specifications (Target Architecture per `PROJECT.md` & `docs/tdd/08_model_routing.md`)**
   - `models/adapters/base.py`: `ModelAdapter(ABC)` with `async generate(self, prompt: str, tools: list) -> Dict[str, Any]` (MR-01).
   - `models/adapters/gemini.py`: Tier 1 `GeminiFlashAdapter` for simple/high-volume tasks (MR-02).
   - `models/adapters/openrouter.py`: Tier 2 `OpenRouterAdapter` for standard reasoning/coding (MR-03).
   - `models/adapters/antigravity.py`: Tier 3 `AntigravityAdapter` for deep reasoning/architecture (MR-04).
   - `models/cost_tracker.py`: `CostTracker` class tracking prompt tokens, completion tokens, total tokens, and financial cost (MR-07).

---

### 1.2 Event Type & Schema Registry

| Domain | Event Type | Destination | Standard Payload Structure | Description |
|---|---|---|---|---|
| System | `system.boot` | `*` | `{}` | Fired when Kernel initializes. |
| System | `system.shutdown` | `*` | `{}` | Fired by `kernel.shutdown()` during graceful teardown. |
| System | `module.registered` | `*` | `{"module_name": str}` | Emitted when a new module is registered. |
| Task | `task.create` | `scheduler` | `{"task": Task.model_dump()}` | Submits a new task to Scheduler. |
| Task | `task.assigned` | `*` | `{"task_id": str, "agent": str}` | Emitted when task is assigned to an agent. |
| Task | `task.executing` | `*` | `{"task_id": str}` | Agent begins execution. |
| Task | `task.complete` | `requester` | `{"task_id": str, "result": Dict[str, Any]}` | Task completed successfully. |
| Task | `task.failed` | `requester` | `{"task_id": str, "error": str}` | Task execution failed. |
| DAG | `dag.create` | `scheduler` | `{"dag": DAG.model_dump()}` | Submits task DAG graph. |
| DAG | `dag.complete` | `requester` | `{"dag_id": str}` | All tasks in DAG completed. |
| Registry | `registry.register_agent` | `agent_registry` | `{"contract": AgentContract.model_dump()}` | Registers an agent contract. |
| Registry | `registry.agent_registered`| `source` | `{"identity": str, "status": "success"}` | Agent registration response. |
| Registry | `registry.find_agent` | `agent_registry` | `{"task_description": str, "task_id": str}` | Queries registry for agent. |
| Registry | `registry.agent_found` | `source` | `{"contract": dict \| None, "task_id": str}` | Registry agent query result. |
| Model | `model.request_execution` | `model_router` | `{"task_id": str, "task_description": str, "agent": dict, "tools": list}` | Requests LLM execution. |
| Model | `model.execution_complete` | `source` | `{"task_id": str, "result": {"status": str, "executed_by": str, "agent": str, "output": str, "tokens": dict, "cost": float}}` | Execution response from Model Router. |
| Memory | `memory.store_knowledge` | `memory_engine` | `{"knowledge": Knowledge.model_dump()}` | Store fact/knowledge. |
| Memory | `memory.knowledge_stored` | `source` | `{"knowledge_id": str, "status": "success"}` | Storage confirmation. |
| Memory | `memory.query_knowledge` | `memory_engine` | `{"query": str}` | Search knowledge base. |
| Memory | `memory.query_results` | `source` | `{"query": str, "results": List[dict]}` | Memory query result. |

---

## 2. Logic Chain

1. **Observation**: `Kernel.register_module` (kernel/kernel.py:13-20) stores the module, calls `event_bus.register_subscriber(module)`, and injects kernel reference if `set_kernel` exists.
   - **Deduction**: Kernel serves as the single dependency injection point for the system. Tests can mock or replace any subscriber module by registering a custom test module under the exact target name.

2. **Observation**: `EventBus.handle_event` (events/event_bus.py:28-43) distinguishes broadcast (`destination == "*"`) vs unicast (`destination in subscribers`). Broadcast excludes sender (`name != event.source`).
   - **Deduction**: Opaque-box contract requires that (a) unicast events deliver strictly to the target module, (b) broadcast events deliver to all registered modules *except* the originator, and (c) unknown destinations do not crash the bus (and must route to a Dead-Letter Queue once EVTB-005 is completed).

3. **Observation**: `ModelRouter.handle_event` (models/model_router.py:28-52) responds to `model.request_execution` with `model.execution_complete`, containing `task_id` and `result` payload.
   - **Deduction**: In M1/M4 E2E testing, callers (like `Scheduler` or `BaseAgent`) do not care *how* ModelRouter computes or calls LLMs, as long as `model.execution_complete` is returned to `event.source` with valid `status`, `executed_by`, `output`, `tokens`, and `cost` payload keys.

4. **Observation**: `ModelRouter.decide_model` currently uses word counts (<10 words -> Gemini Flash, <50 words -> OpenRouter, >=50 words -> Antigravity CLI).
   - **Deduction**: Testable heuristic contract must verify tier transitions across word length thresholds, as well as fallback behavior when primary adapters raise API errors.

5. **Observation**: Current models and tests use `datetime.utcnow()` (e.g. `shared/models.py:12`). Python 3.12 raises `DeprecationWarning`.
   - **Deduction**: Core event creation and time formatting must be updated to `datetime.now(timezone.utc)` (TEST-003) to ensure clean test execution under strict warning flags.

---

## 3. Caveats

- **No Caveats**: All core infrastructure code in `shared`, `kernel`, `events`, and `models` was fully inspected line-by-line.
- **Scope Note**: Non-infrastructure department workers (Engineering, Research, Marketing, Sales, Personal) were examined for interface compliance but their internal business logic implementation is in M2/M3 scope.

---

## 4. Conclusion & Testable Opaque-Box Contracts

### 4.1 Kernel Contract
1. **Module Lifecycle**: Registering a module must add it to `Kernel.modules`, subscribe it to `EventBus`, and invoke `module.set_kernel(kernel)` if the method exists.
2. **Event Dispatch**: `kernel.send_event(event)` must route events without mutating event parameters.
3. **Shutdown Signal**: `kernel.shutdown()` must broadcast `system.shutdown` event to all registered modules except `kernel`.

### 4.2 Event Bus Contract
1. **Unicast Delivery**: `destination == module_name` delivers event strictly to that module.
2. **Broadcast Delivery**: `destination == "*"` delivers event to all modules except `event.source`.
3. **Error Isolation**: Exception raised in subscriber `handle_event` must not prevent remaining broadcast subscribers from receiving event (`EVTB-007`).
4. **Dead-Letter Queue (DLQ)**: Events with unknown destinations must be routed to `dlq` module or queue instead of silently dropping (`EVTB-005`).

### 4.3 Model Router Contract (Adapters, Heuristics, Fallback, CostTracker)
1. **Event Contract**: Must consume `model.request_execution` and reply with `model.execution_complete` to `event.source`.
2. **Heuristic Selection**:
   - Tier 1 (`GeminiFlashAdapter`): Simple / high-volume / <10 words.
   - Tier 2 (`OpenRouterAdapter`): Standard reasoning / coding / 10-49 words.
   - Tier 3 (`AntigravityAdapter`): Deep reasoning / architecture / >=50 words.
3. **Fallback Redundancy**: If primary tier adapter fails (e.g. API exception), ModelRouter automatically falls back to secondary/tertiary adapter without raising an unhandled exception to the requester.
4. **CostTracker Integration**: `result` payload must include token breakdown (`prompt_tokens`, `completion_tokens`, `total_tokens`) and computed financial cost (`cost`).

---

## 5. End-to-End Test Recommendations (Tiers 1 - 4)

### Tier 1: Infrastructure Unit & Component Contracts (`tests/e2e/test_tier1_infrastructure.py`)
- **T1-KERN-01**: Verify dynamic module registration, subscriber attachment, and kernel reference injection.
- **T1-KERN-02**: Verify `Kernel.shutdown()` broadcasts `system.shutdown` to all registered modules except sender.
- **T1-EVTB-01**: Verify point-to-point (unicast) routing delivers event to target module.
- **T1-EVTB-02**: Verify broadcast (`destination="*"`) delivers to all registered modules except sender.
- **T1-EVTB-03**: Verify schema validation rejects malformed events (missing `source`, `event_type`, or `destination`).
- **T1-EVTB-04**: Verify exception in one subscriber does not crash EventBus or block other subscribers (error boundary).
- **T1-MR-01**: Verify `ModelRouter.decide_model()` word count heuristics (<10 -> Gemini Flash, 10-49 -> OpenRouter, >=50 -> Antigravity).
- **T1-MR-02**: Verify `CostTracker` accurately calculates token usage costs per model provider tier.
- **T1-TIME-01**: Verify all events use UTC time without `utcnow()` deprecation warnings.

### Tier 2: Subsystem Cascade & Integration Contracts (`tests/e2e/test_tier2_subsystems.py`)
- **T2-CASCADE-01**: Full task cascade: `Scheduler` (`task.create`) -> `AgentRegistry` (`registry.find_agent`) -> `ModelRouter` (`model.request_execution`) -> `Scheduler` -> `Requester` (`task.complete`).
- **T2-MEM-01**: Memory persistence cascade: `Requester` -> `Kernel` -> `MemoryEngine` (`memory.store_knowledge`) -> `memory.knowledge_stored` -> query (`memory.query_knowledge`) -> `memory.query_results`.
- **T2-DLQ-01**: Dead-letter queue routing: Unroutable event destination is captured in DLQ subscriber queue without event loop failure.
- **T2-MR-FAILOVER**: Model Router adapter failover: Mock primary adapter (`OpenRouterAdapter`) raising exception triggers automated fallback to `GeminiFlashAdapter` or `AntigravityAdapter` with `executed_by` reflecting fallback adapter.

### Tier 3: Departmental & Inter-Departmental Workflow Contracts (`tests/e2e/test_tier3_departments.py`)
- **T3-DEPT-REG**: `BaseDepartmentModule` wrapping Department Manager allows registration with Kernel and receives Kernel reference.
- **T3-ENG-WORKFLOW**: Engineering Department execution: `EngineeringManager` receives task -> delegates to `BackendWorker` / `QAWorker` -> uses `ToolRegistry` -> returns task completion.
- **T3-TOOL-PERM**: ToolRegistry permission enforcement: Agent invoking tool not listed in `allowed_tools` raises `PermissionDenied`.
- **T3-MULTI-DEPT**: Inter-departmental coordination: `ResearchManager` completes market research task, emits event triggering `MarketingManager` campaign creation task via Kernel EventBus.

### Tier 4: System End-to-End & Lifecycle Contracts (`tests/e2e/test_tier4_e2e_system.py`)
- **T4-DAG-EXEC**: Complex DAG execution: 3-node task graph (Task A -> Task B & C in parallel -> Task D dependant on B & C) submitted via `dag.create` executes asynchronously, unblocks dependent tasks, emits `dag.complete`.
- **T4-FULL-LIFECYCLE**: Full OS Lifecycle: Boot Kernel -> Register all infrastructure & departments -> Submit multi-department DAG -> Execute multi-tier LLM models with cost tracking -> Persist knowledge in MemoryEngine -> Shutdown system via `kernel.shutdown()`.
- **T4-CONCURRENCY**: High concurrency stress: Submit 50 concurrent tasks through Kernel & ModelRouter; verify 100% completion rate without event drop or race conditions.

---

## 6. Verification Method

1. **Inspect Code Files**:
   - `shared/interfaces.py`
   - `shared/models.py`
   - `kernel/kernel.py`
   - `events/event_bus.py`
   - `models/model_router.py`
   - `docs/tdd/06_event_system.md`
   - `docs/tdd/08_model_routing.md`
2. **Execute Pytest Suite**:
   ```bash
   PYTHONPATH=. /root/synapse/.venv/bin/pytest tests/
   ```
3. **Invalidation Conditions**:
   - If `Kernel.send_event()` modifies event payload attributes unexpectedly.
   - If `EventBus` broadcasts events back to `event.source`.
   - If `ModelRouter` fails to emit `model.execution_complete` to `event.source`.
