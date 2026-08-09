# Scope: Milestone 1 — Model Router & Core Infrastructure

## Architecture
Milestone 1 establishes the core event control plane, module lifecycle, model execution engine, department interface adapters, tool registry module wrapping, and pytest warning fixes for Synapse AI OS.

## Feature Inventory (Milestone 1)

| # | Feature | Description | File Target | Status |
|---|---------|-------------|-------------|--------|
| 1 | MR-01 | Define abstract `ModelAdapter(ABC)` with `async generate()` interface | `models/adapters/base.py` | DONE |
| 2 | MR-02 | Implement Tier 1 `GeminiFlashAdapter` for simple/high-volume tasks | `models/adapters/gemini.py` | DONE |
| 3 | MR-03 | Implement Tier 2 `OpenRouterAdapter` for standard reasoning/coding | `models/adapters/openrouter.py` | DONE |
| 4 | MR-04 | Implement Tier 3 `AntigravityAdapter` for deep reasoning/architecture | `models/adapters/antigravity.py` | DONE |
| 5 | MR-05 | Implement multi-tier heuristic routing in `decide_model` | `models/model_router.py` | DONE |
| 6 | MR-06 | Implement automatic fallback/redundancy mechanism across adapters | `models/model_router.py` | DONE |
| 7 | MR-07 | Implement `CostTracker` module (`cost_tracker.py`) for tokens and cost | `models/cost_tracker.py` | DONE |
| 8 | MR-08 | Replace hardcoded mock output in `ModelRouter.handle_event` with real adapter output | `models/model_router.py` | DONE |
| 9 | MR-09 | Maintain `model.request_execution` & `model.execution_complete` event bus contract | `models/model_router.py` | DONE |
| 10 | KERN-001 | Dynamic runtime module registration & kernel reference injection | `kernel/kernel.py` | DONE |
| 11 | KERN-002 | Interface enforcement ensuring infrastructure and department managers implement `Module` | `kernel/kernel.py` | DONE |
| 12 | KERN-003 | System shutdown event broadcasting (`system.shutdown`) | `kernel/kernel.py` | DONE |
| 13 | KERN-004 | Kernel health monitoring and module tracking | `kernel/kernel.py` | DONE |
| 14 | EVTB-001 | Direct unicast event routing support | `events/event_bus.py` | DONE |
| 15 | EVTB-002 | Pub/sub broadcast event routing support (`destination="*"`) | `events/event_bus.py` | DONE |
| 16 | EVTB-003 | Event topic subscriptions & wildcard patterns | `events/event_bus.py` | DONE |
| 17 | EVTB-004 | Decoupled async event queues (`asyncio.Queue`) | `events/event_bus.py` | DONE |
| 18 | EVTB-005 | Dead-letter queue for unroutable events | `events/event_bus.py` | DONE |
| 19 | EVTB-006 | Event payload schema validation | `events/event_bus.py` | DONE |
| 20 | EVTB-007 | Event handler error isolation and exception boundaries | `events/event_bus.py` | DONE |
| 21 | DEPT-001 | Department Module Adapter allowing `BaseAgent` departments to register with `Kernel` | `departments/base.py` | DONE |
| 22 | DEPT-004 | Wrap `ToolRegistry` as accessible Kernel module / service | `tools/tool_registry.py` | DONE |
| 23 | TEST-002 | Fix `PytestCollectionWarning` on `TestClient` in `tests/test_kernel.py` | `tests/test_kernel.py` | DONE |
| 24 | TEST-003 | Fix `datetime.utcnow()` deprecation warnings using `datetime.now(timezone.utc)` | `shared/models.py`, `memory/memory_engine.py` | DONE |

## Milestones Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Model Router & Core Infrastructure | Features MR-01 to MR-09, KERN-001..004, EVTB-001..007, DEPT-001, DEPT-004, TEST-002, TEST-003 | none | DONE |
