# Project: Synapse AI OS Backend Implementation

## Architecture
Synapse AI OS is an event-driven agent operating system architecture.
- **Kernel (`kernel/kernel.py`)**: Central control plane managing module registration (`register_module`), event routing delegation, and lifecycle hooks.
- **Event Bus (`events/event_bus.py`)**: Message broker supporting direct unicast (`destination == module_name`) and pub/sub broadcast (`destination == "*"`).
- **Model Router (`models/model_router.py`)**: Multi-tier LLM selection (Tier 1: Gemini Flash, Tier 2: OpenRouter, Tier 3: Antigravity CLI) backed by abstract `ModelAdapter` interfaces, fallback redundancy mechanisms, and token/cost tracking (`cost_tracker.py`).
- **Departments (`departments/`)**: Domain-specific managerial and worker agents (Engineering, Research, Marketing, Sales, Personal, Echo) inheriting `Module` and `BaseAgent`, listening for Kernel events, delegating subtasks to specialized workers, executing tools via `ToolRegistry`, and storing knowledge in `MemoryEngine`.
- **Memory Engine (`memory/memory_engine.py`)**: SQLite-backed storage for events, tasks, artifacts, knowledge graph, and metrics.
- **Task Scheduler (`scheduler/scheduler.py`)**: DAG scheduler mapping tasks to registered agents and handling model execution event callbacks.

## Code Layout
```
/root/synapse/
├── shared/
│   ├── interfaces.py          # Module and KernelInterface ABCs
│   └── models.py              # Event, AgentContract, Task, DAG, Knowledge schemas
├── kernel/
│   └── kernel.py              # Kernel implementation
├── events/
│   └── event_bus.py           # EventBus module implementation
├── models/
│   ├── model_router.py        # ModelRouter module
│   ├── cost_tracker.py        # Token usage & financial cost tracking
│   └── adapters/              # Provider adapters
│       ├── base.py            # ModelAdapter ABC
│       ├── gemini.py          # Gemini Flash adapter
│       ├── openrouter.py      # OpenRouter adapter
│       └── antigravity.py     # Antigravity CLI adapter
├── departments/
│   ├── base.py                # BaseAgent class & DepartmentModule adapter
│   ├── engineering/           # EngineeringManager, BackendWorker, QAWorker, etc.
│   ├── research/              # ResearchManager, GithubWorker, HNWorker, RedditWorker, etc.
│   ├── marketing/             # MarketingManager, SocialWorker, ContentWorker, etc.
│   ├── sales/                 # SalesManager, OutreachWorker
│   ├── personal/              # PersonalManager, AssistantWorker
│   └── echo/                  # EchoDepartment module
├── tools/
│   └── tool_registry.py       # ToolRegistry class & tool executions
└── tests/                     # Pytest suite
    ├── test_kernel.py
    ├── test_model_router.py
    ├── test_engineering.py
    ├── test_research.py
    ├── test_marketing.py
    ├── test_sales.py
    ├── test_personal.py
    └── test_echo.py
```

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | MR-01 | Define abstract `ModelAdapter(ABC)` with `async generate()` interface | M1 | Survey Explorer 1 |
| 2 | MR-02 | Implement Tier 1 `GeminiFlashAdapter` for simple/high-volume tasks | M1 | Survey Explorer 1 |
| 3 | MR-03 | Implement Tier 2 `OpenRouterAdapter` for standard reasoning/coding | M1 | Survey Explorer 1 |
| 4 | MR-04 | Implement Tier 3 `AntigravityAdapter` for deep reasoning/architecture | M1 | Survey Explorer 1 |
| 5 | MR-05 | Implement multi-tier heuristic routing in `decide_model` | M1 | Survey Explorer 1 |
| 6 | MR-06 | Implement automatic fallback/redundancy mechanism across adapters | M1 | Survey Explorer 1 |
| 7 | MR-07 | Implement `CostTracker` module (`cost_tracker.py`) for tokens and cost | M1 | Survey Explorer 1 |
| 8 | MR-08 | Replace hardcoded mock output in `ModelRouter.handle_event` with real adapter output | M1 | Survey Explorer 1 |
| 9 | MR-09 | Maintain `model.request_execution` & `model.execution_complete` event bus contract | M1 | Survey Explorer 1 |
| 10 | KERN-001 | Dynamic runtime module registration & kernel reference injection | M1 | Survey Explorer 2 |
| 11 | KERN-002 | Interface enforcement ensuring infrastructure and department managers implement `Module` | M1 | Survey Explorer 2 |
| 12 | KERN-003 | System shutdown event broadcasting (`system.shutdown`) | M1 | Survey Explorer 2 |
| 13 | KERN-004 | Kernel health monitoring and module tracking | M1 | Survey Explorer 2 |
| 14 | EVTB-001 | Direct unicast event routing support | M1 | Survey Explorer 2 |
| 15 | EVTB-002 | Pub/sub broadcast event routing support (`destination="*"`) | M1 | Survey Explorer 2 |
| 16 | EVTB-003 | Event topic subscriptions & wildcard patterns | M1 | Survey Explorer 2 |
| 17 | EVTB-004 | Decoupled async event queues (`asyncio.Queue`) | M1 | Survey Explorer 2 |
| 18 | EVTB-005 | Dead-letter queue for unroutable events | M1 | Survey Explorer 2 |
| 19 | EVTB-006 | Event payload schema validation | M1 | Survey Explorer 2 |
| 20 | EVTB-007 | Event handler error isolation and exception boundaries | M1 | Survey Explorer 2 |
| 21 | DEPT-001 | Department Module Adapter allowing `BaseAgent` departments to register with `Kernel` | M1 | Survey Explorer 2 |
| 22 | DEPT-004 | Wrap `ToolRegistry` as accessible Kernel module / service | M1 | Survey Explorer 2 |
| 23 | TEST-002 | Fix `PytestCollectionWarning` on `TestClient` in `tests/test_kernel.py` | M1 | Survey Explorer 2 |
| 24 | TEST-003 | Fix `datetime.utcnow()` deprecation warnings using `datetime.now(timezone.utc)` | M1 | Survey Explorer 2 |
| 25 | F-ENG-1 | Real task execution in `EngineeringManager` (remove `"mocked engineering manager result"`) | M2 | Survey Explorer 3 |
| 26 | F-ENG-2 | Real task execution in `BackendWorker` (remove `"mocked backend result"`) | M2 | Survey Explorer 3 |
| 27 | F-ENG-3 | Implement `QAWorker` and `DevOpsWorker` in engineering department | M2 | Survey Explorer 3 |
| 28 | F-ENG-4 | Create unit & integration test file `tests/test_engineering.py` | M2 | Survey Explorer 3 |
| 29 | F-RES-1 | Real task delegation & aggregation in `ResearchManager` (remove static `delegated` stub) | M2 | Survey Explorer 3 |
| 30 | F-RES-2 | Implement functional search & data processing across GitHub, HN, ProductHunt, Reddit, Twitter workers | M2 | Survey Explorer 3 |
| 31 | F-RES-3 | Create unit & integration test file `tests/test_research.py` | M2 | Survey Explorer 3 |
| 32 | F-MKT-1 | Real campaign management in `MarketingManager` (remove `"mocked marketing manager result"`) | M3 | Survey Explorer 3 |
| 33 | F-MKT-2 | Real post generation in `SocialWorker` (remove `"mocked social media result"`) | M3 | Survey Explorer 3 |
| 34 | F-MKT-3 | Implement `ContentWorker` in marketing department | M3 | Survey Explorer 3 |
| 35 | F-MKT-4 | Create unit & integration test file `tests/test_marketing.py` | M3 | Survey Explorer 3 |
| 36 | F-SLS-1 | Create `departments/sales/` directory, `__init__.py`, `manager.py`, `outreach_worker.py` | M3 | Survey Explorer 3 |
| 37 | F-SLS-2 | Implement functional `SalesManager` with lead generation & CRM tools | M3 | Survey Explorer 3 |
| 38 | F-SLS-3 | Implement functional `SalesWorker` with email draft & pitch generation | M3 | Survey Explorer 3 |
| 39 | F-SLS-4 | Create unit & integration test file `tests/test_sales.py` | M3 | Survey Explorer 3 |
| 40 | F-PRS-1 | Real assistant management in `PersonalManager` (remove `"mocked personal manager result"`) | M3 | Survey Explorer 3 |
| 41 | F-PRS-2 | Real task/schedule execution in `AssistantWorker` (remove `"mocked assistant result"`) | M3 | Survey Explorer 3 |
| 42 | F-PRS-3 | Create unit & integration test file `tests/test_personal.py` | M3 | Survey Explorer 3 |
| 43 | F-ECH-1 | Preserve and verify `EchoDepartment` ping/pong event module | M3 | Survey Explorer 3 |
| 44 | F-ECH-2 | Create unit & integration test file `tests/test_echo.py` | M3 | Survey Explorer 3 |
| 45 | TEST-004 | Full End-to-End event cascade integration verification & Tier 5 adversarial hardening | M4 | Survey Explorer 2 |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Model Router & Core Infrastructure | ModelAdapter pattern, Gemini/OpenRouter/Antigravity adapters, multi-tier heuristic router, cost tracking, EventBus queues & error boundaries, Pytest warning fixes | none | DONE |
| M2 | Technical Departments | Engineering Manager & Workers, Research Manager & Workers, tests/test_engineering.py, tests/test_research.py | M1 | DONE |
| M3 | Commercial & Operations Departments | Marketing Manager & Workers, Sales Manager & Workers (scaffolded), Personal Manager & Workers, Echo Department, test_marketing.py, test_sales.py, test_personal.py, test_echo.py | M1 | DONE |
| M4 | Final Milestone & Adversarial Hardening | E2E test suite validation (100% pass across all test tiers) + Tier 5 adversarial coverage hardening | M2, M3 | DONE |

## Interface Contracts

### Event Bus Envelope
```python
Event(
    id=str(uuid4()),
    source="module_name",
    destination="target_module" | "*",
    event_type="domain.action",
    payload=dict(),
    timestamp=datetime.now(timezone.utc)
)
```

### Model Router ↔ Kernel Event Contract
- Input Event: `event_type="model.request_execution"`
  - Payload: `{"task_id": str, "task_description": str, "agent": dict, "tools": list}`
- Output Event: `event_type="model.execution_complete"`
  - Payload: `{"task_id": str, "result": {"status": "success", "executed_by": str, "agent": str, "output": str, "tokens": dict, "cost": float}}`

### Department Manager ↔ Kernel Interface Contract
Every Department Manager must implement `Module` interface:
```python
class BaseDepartmentModule(Module):
    @property
    def name(self) -> str: ...
    def set_kernel(self, kernel: KernelInterface) -> None: ...
    async def handle_event(self, event: Event) -> None: ...
```

Event handling for departments:
- Listen for `event_type="department.execute_task"` or `event_type="task.assigned"`
- Emit `event_type="department.task_completed"` or `event_type="task.complete"`
