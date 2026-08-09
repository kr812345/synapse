## 2026-08-05T21:31:26Z
You are Worker 2 for Milestone 1: Core Infrastructure Implementation (KERN, EVTB, DEPT, TEST).
Working Directory: /root/synapse/.agents/worker_m1_2
Project Directory: /root/synapse

Exclusively Owned Files:
- kernel/kernel.py
- events/event_bus.py
- departments/base.py
- tools/tool_registry.py
- shared/models.py
- memory/memory_engine.py
- tests/test_kernel.py

Required Reference Files to Read First:
- /root/synapse/.agents/ORIGINAL_REQUEST.md
- /root/synapse/PROJECT.md
- /root/synapse/.agents/sub_orch_m1/SCOPE.md
- /root/synapse/.agents/explorer_m1_2/analysis.md
- /root/synapse/.agents/explorer_m1_2/handoff.md
- /root/synapse/.agents/explorer_m1_3/analysis.md
- /root/synapse/.agents/explorer_m1_3/handoff.md

Tasks:
1. Implement KERN-001 to KERN-004 in `kernel/kernel.py`: dynamic module registration (`register_module`, `unregister_module`), `set_kernel` injection, `Module` interface check, system shutdown event broadcasting (`system.shutdown`), kernel health monitoring (`get_health_status()`).
2. Implement EVTB-001 to EVTB-007 in `events/event_bus.py`: direct unicast event routing, pub/sub broadcast (`destination="*"`), topic subscriptions (`subscribe_topic`, fnmatch wildcards), decoupled `asyncio.Queue`, dead-letter queue (DLQ), payload validation, error boundary isolation.
3. Implement DEPT-001 in `departments/base.py`: `BaseDepartmentModule(Module)` adapter class bridging `BaseAgent` departments to `Kernel`.
4. Implement DEPT-004 in `tools/tool_registry.py`: Wrap `ToolRegistry` as a `Module` (`name="tool_registry"`), enabling event-driven tool execution.
5. Implement TEST-002: Rename `TestClient` class in `tests/test_kernel.py` to `MockKernelClient` to eliminate `PytestCollectionWarning`.
6. Implement TEST-003: Replace deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` across `shared/models.py` and `memory/memory_engine.py`.
7. Execute pytest command: `PYTHONPATH=. ./.venv/bin/pytest tests/test_kernel.py`.
