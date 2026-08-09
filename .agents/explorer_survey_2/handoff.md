# Handoff Report — Event Bus & Kernel Infrastructure Survey

## Executive Summary
This report presents an exhaustive architectural and code survey of the AI OS Kernel, Event Bus, Messaging System, Department wiring, and Test Infrastructure in `/root/synapse`.
While core in-memory routing, module registration, and basic event data structures are implemented, significant architectural gaps exist: department managers (Engineering, Marketing, Personal, Research) rely on hardcoded mock strings and are disconnected from the Kernel module event architecture; the Event Bus lacks error boundaries, dead-letter routing, event schema validation, and topic pub/sub subscriptions; and test coverage for department event handling is absent.

---

## 1. Observation

### 1.1 Codebase File Map & Infrastructure Components
The following files comprise the Kernel, Event Bus, Messaging, and Infrastructure layers:

| Component | File Path | Key Line Numbers | Description / Role |
|---|---|---|---|
| **Event Data Model** | `shared/models.py` | 6–12 | `Event` Pydantic model (`id`, `source`, `destination`, `event_type`, `payload`, `timestamp`). |
| **Domain Models** | `shared/models.py` | 14–55 | `AgentContract` (14-23), `Task` (25-34), `DAG` (36-42), `Knowledge` (45-54). |
| **Interfaces** | `shared/interfaces.py` | 4–24 | `Module` ABC (4-14, requires `name` & `async handle_event`), `KernelInterface` ABC (16-24, requires `register_module` & `async send_event`). |
| **Event Bus** | `events/event_bus.py` | 10–43 | Implements `Module`. Directunicast (`destination == name`) & broadcast (`destination == "*"`). Uses `asyncio.gather` for broadcasts. |
| **Kernel** | `kernel/kernel.py` | 8–29 | Implements `KernelInterface`. Holds `self.modules` dict & `self.event_bus`. Directs `send_event` to `event_bus.handle_event`. Injects `kernel` reference via `set_kernel`. |
| **Agent Registry** | `agents/registry.py` | 8–65 | Implements `Module`. Listens for `registry.register_agent` & `registry.find_agent`. |
| **Task Scheduler** | `scheduler/scheduler.py` | 9–137 | Implements `Module`. Listens for `dag.create`, `task.create`, `registry.agent_found`, `model.execution_complete`. |
| **Memory Engine** | `memory/memory_engine.py` | 11–194 | Implements `Module`. SQLite storage (`events`, `tasks`, `artifacts`, `knowledge_graph`, `agents`, `metrics`). Listens for `memory.store_knowledge` & `memory.query_knowledge`. |
| **Model Router** | `models/model_router.py` | 7–53 | Implements `Module`. Heuristic model choice (`words < 10` -> Gemini Flash, `< 50` -> OpenRouter, else Antigravity CLI). Simulates execution with hardcoded string (lines 38-43). |
| **Tool Registry** | `tools/tool_registry.py` | 17–36 | Tool execution & permission validation class. Not currently wrapped as a Kernel `Module`. |
| **Echo Department** | `departments/echo/echo_manager.py` | 7–30 | Implements `Module`. Listens for `ping` and sends `pong` event via `Kernel`. |

### 1.2 Department Integration Status & Mock Analysis
Observation of `departments/` reveals a architectural disconnect between `EchoDepartment` and all other departments:

```python
# departments/echo/echo_manager.py:7
class EchoDepartment(Module):  # Inherits Module, connects to Kernel
    def set_kernel(self, kernel: KernelInterface):
        self.kernel = kernel

# departments/engineering/manager.py:5
class EngineeringManager(BaseAgent):  # Inherits BaseAgent, NOT Module!
    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked engineering manager result"}  # Line 23
```

- **Engineering Department** (`departments/engineering/manager.py:23`, `backend_worker.py`): Manager inherits `BaseAgent`, missing `Module` implementation, missing `name` property, missing `handle_event` method, missing `set_kernel`. `execute()` returns `"mocked engineering manager result"`.
- **Marketing Department** (`departments/marketing/manager.py:23`, `social_worker.py`): Manager inherits `BaseAgent`, missing `Module` implementation. `execute()` returns `"mocked marketing manager result"`.
- **Personal Department** (`departments/personal/manager.py:23`, `assistant_worker.py`): Manager inherits `BaseAgent`, missing `Module` implementation. `execute()` returns `"mocked personal manager result"`.
- **Research Department** (`departments/research/manager.py:21`, `workers/*.py`): Manager inherits `BaseAgent`, missing `Module` implementation. `execute()` returns `{"status": "delegated", "task": task}`. Workers (`github.py`, `hn.py`, `reddit.py`, `twitter.py`, `product_hunt.py`) return empty/mocked lists (e.g. `github.py:21`: `{"status": "success", "source": "github", "data": []}`).

### 1.3 Test Infrastructure & Pytest Execution
Running `PYTHONPATH=. ./.venv/bin/pytest` produces the following output:

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /root/synapse
plugins: asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 9 items

tests/test_base_agent.py .                                               [ 11%]
tests/test_kernel.py ..                                                  [ 33%]
tests/test_memory.py .                                                   [ 44%]
tests/test_model_router.py .                                             [ 55%]
tests/test_registry.py .                                                 [ 66%]
tests/test_scheduler.py ..                                               [ 88%]
tests/test_tool_registry.py .                                            [100%]

=============================== warnings summary ===============================
tests/test_kernel.py:8
  PytestCollectionWarning: cannot collect test class 'TestClient' because it has a __init__ constructor (from: tests/test_kernel.py)
    class TestClient(Module):

tests/test_kernel.py: 3 warnings
tests/test_memory.py: 5 warnings
tests/test_model_router.py: 4 warnings
tests/test_registry.py: 4 warnings
tests/test_scheduler.py: 26 warnings
  DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
======================== 9 passed, 44 warnings in 2.16s ========================
```

Key observations:
1. All 9 current tests pass.
2. `tests/test_kernel.py:8` raises a `PytestCollectionWarning` because `TestClient` starts with `Test` so pytest attempts to collect it as a test class.
3. 44 warnings regarding `datetime.utcnow()` deprecation across `models.py` and `memory_engine.py`.
4. No test files exist for any department (`test_engineering.py`, `test_marketing.py`, `test_research.py`, `test_personal.py`, `test_echo.py`).

---

## 2. Logic Chain

### 2.1 Event Routing & Kernel Topology Reasoning
1. **Observation**: `Kernel.register_module(module)` stores `module` in `self.modules` dict and invokes `self.event_bus.register_subscriber(module)`. If `module` has `set_kernel`, `kernel` is injected.
2. **Observation**: `Kernel.send_event(event)` delegates directly to `await self.event_bus.handle_event(event)`.
3. **Observation**: `EventBus.handle_event(event)` checks if `event.destination == "*"`. If broadcast, it iterates `self.subscribers` (excluding `event.source`) and executes `await asyncio.gather(*tasks)`. If directunicast (`event.destination in self.subscribers`), it calls `await module.handle_event(event)`.
4. **Deduction**: The event routing model operates purely via direct nested async function invocation. If `Module A` sends an event to `Module B`, which in turn sends an event to `Module C`, the entire call stack is synchronous within the event loop stack. Unhandled exceptions in `Module C` fail the entire cascade back to `Module A`.
5. **Deduction**: There is currently no async queue buffer (`asyncio.Queue`) or event bus task pool separating modules.

### 2.2 Department Connection Disconnection Reasoning
1. **Observation**: In `docs/architecture.md:36-38`, `Kernel <--> Research`, `Kernel <--> Marketing`, `Kernel <--> Engineering`.
2. **Observation**: In `docs/tdd/01_overall_architecture.md:41-44`, departments connect to the `Kernel`.
3. **Observation**: `EchoDepartment` is the ONLY department implementing `Module` and attaching to `Kernel`.
4. **Observation**: `EngineeringManager`, `MarketingManager`, `PersonalManager`, and `ResearchManager` implement `BaseAgent` instead of `Module`.
5. **Deduction**: `Scheduler` dispatches task execution to `ModelRouter` via event `model.request_execution` (`scheduler/scheduler.py:108-114`). `ModelRouter` generates a simulated response without ever invoking any Department Manager or Department Worker (`models/model_router.py:38-43`).
6. **Conclusion**: Department Managers must either inherit from both `Module` and `BaseAgent` or be wrapped inside a Department Module adapter so they can register with `Kernel`, listen for events (`task.assigned`, `department.execute_task`), dispatch to workers, and produce real results.

---

## 3. Caveats
- **Read-Only Scope**: This report contains findings, structural analysis, and inventory specifications. No source code modifications were performed during this exploration phase.
- **Database Backend**: `MemoryEngine` currently defaults to SQLite `:memory:` for MVP. Production specs in TDD Phase 4 call for PostgreSQL + pgvector.
- **Model Router Integration**: Actual LLM API calls (Gemini Flash, OpenRouter, Antigravity CLI) are currently stubbed in `ModelRouter`.

---

## 4. Conclusion
The AI OS Kernel and Event Bus infrastructure provides a clean, working foundation for in-memory module registration and event delivery. However, to fulfill Requirements R1 & R2 of the original request, the following core structural changes are required:
1. Department Managers (`EngineeringManager`, `MarketingManager`, `PersonalManager`, `ResearchManager`) must be refactored to implement the `Module` interface and connect directly to the `Kernel`.
2. The `ModelRouter` and `Scheduler` must be connected to dispatch work directly to Department Modules rather than returning hardcoded simulated responses.
3. Pytest coverage must be expanded with department-specific tests, and existing Pytest collection/deprecation warnings must be fixed.

---

## 5. Verification Method

### 5.1 Verification Commands
To verify the findings in this report, execute the following commands from `/root/synapse`:

```bash
# 1. Run full test suite and inspect output & warnings
PYTHONPATH=. ./.venv/bin/pytest -v

# 2. Inspect kernel module registration
python3 -c "from kernel.kernel import Kernel; k = Kernel(); print(k.modules)"

# 3. Verify department module compliance (will show EchoDepartment as Module, others as BaseAgent)
python3 -c "from shared.interfaces import Module; from departments.echo.echo_manager import EchoDepartment; from departments.engineering.manager import EngineeringManager; print('Echo is Module:', issubclass(EchoDepartment, Module)); print('Eng is Module:', issubclass(EngineeringManager, Module))"
```

### 5.2 Specific Files to Inspect
- `shared/interfaces.py`: `Module` and `KernelInterface` abstract definitions.
- `kernel/kernel.py`: `Kernel` class implementation.
- `events/event_bus.py`: `EventBus` subscriber dictionary and routing logic.
- `departments/echo/echo_manager.py`: Working reference of a department module.
- `departments/engineering/manager.py`: Non-compliant department agent returning mock string.
- `tests/test_kernel.py`: Location of `TestClient` pytest collection warning.

---

## Feature Inventory Additions

The following enumerated features and requirements must be added to the project Feature Inventory for Event Bus, Kernel, Messaging, and Infrastructure:

### Category: Kernel Architecture (KERN)
- **KERN-001: Dynamic Module Registration**: Kernel must allow modules to register at runtime via `kernel.register_module(module)` and inject kernel reference via `set_kernel()`.
- **KERN-002: Kernel Interface Enforcement**: All core infrastructure (EventBus, Scheduler, MemoryEngine, ModelRouter, AgentRegistry, ToolRegistry) and Department Managers must implement `Module`.
- **KERN-003: Graceful System Shutdown**: Kernel must broadcast `system.shutdown` event to all registered subscribers upon `kernel.shutdown()`.
- **KERN-004: Kernel Health Monitoring**: Kernel must track active registered modules and monitor event loop responsiveness.

### Category: Event Bus & Messaging (EVTB)
- **EVTB-001: Direct Unicast Event Routing**: EventBus must route events directly to specified module `destination`.
- **EVTB-002: Pub/Sub Broadcast Event Routing**: EventBus must deliver broadcast events (`destination="*"`) to all registered modules except the sender.
- **EVTB-003: Event Type Topic Subscriptions**: EventBus must support subscribing modules to specific event types or wildcard patterns (e.g. `task.*`, `memory.*`).
- **EVTB-004: Event Durability & Async Queues**: EventBus must support decoupled async event queues (`asyncio.Queue`) to prevent deep coroutine stack recursion.
- **EVTB-005: Dead-Letter Queue & Routing Failures**: EventBus must route unmapped destination events to a Dead-Letter Queue and emit a routing failure error event back to the sender.
- **EVTB-006: Event Schema & Payload Validation**: EventBus must validate event payload schemas against standard event types (`task.create`, `task.complete`, `memory.store_knowledge`, etc.).
- **EVTB-007: Event Error Isolation**: EventBus must catch exceptions in module event handlers, preventing single-module failures from crashing the routing loop.

### Category: Department Kernel Wiring (DEPT)
- **DEPT-001: Department Module Adapter**: All department managers (Engineering, Marketing, Personal, Research) must implement `Module` interface and register with `Kernel`.
- **DEPT-002: Department Task Lifecycle Handling**: Department managers must listen for kernel events (`task.assigned`, `department.execute_task`), delegate tasks to specialized workers, and return structured output events.
- **DEPT-003: Removal of Mock Responses**: Replace all mocked return strings (e.g. `"mocked engineering manager result"`) across all departments with functional task execution and tool calls.
- **DEPT-004: Tool Registry Kernel Integration**: Wrap `ToolRegistry` as a Kernel module or standard service accessible to department workers during task execution.

### Category: Test Infrastructure & Quality (TEST)
- **TEST-001: Department Pytest Suite**: Create dedicated unit/integration tests for each department (`tests/test_engineering.py`, `tests/test_marketing.py`, `tests/test_research.py`, `tests/test_personal.py`, `tests/test_echo.py`).
- **TEST-002: Fix Pytest Collection Warnings**: Rename test helper classes (e.g. `TestClient` in `tests/test_kernel.py`) to avoid `PytestCollectionWarning`.
- **TEST-003: Deprecate Naive Datetime Usage**: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` across `models.py` and `memory_engine.py` to resolve Python 3.12 deprecation warnings.
- **TEST-004: End-to-End Event Cascade Verification**: Integration test verifying complete event flow: Requester -> Kernel -> Scheduler -> Registry -> Department Manager -> Worker -> ModelRouter -> ToolRegistry -> MemoryEngine -> Requester.
