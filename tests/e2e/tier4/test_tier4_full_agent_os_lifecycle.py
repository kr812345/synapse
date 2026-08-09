"""
Tier 4 Real-World Application Scenario Tests: Full Agent OS Lifecycle, High Concurrency Stress, and System Disaster Recovery.
"""

import pytest
import asyncio
import sqlite3
from typing import List, Dict, Any

from shared.models import Event, Task, DAG, AgentContract, Knowledge
from kernel.kernel import Kernel
from models.model_router import ModelRouter
from agents.registry import AgentRegistry
from scheduler.scheduler import Scheduler
from memory.memory_engine import MemoryEngine
from departments.echo.echo_manager import EchoDepartment
from departments.base import BaseDepartmentModule
from departments.engineering.manager import EngineeringManager
from departments.research.manager import ResearchManager
from departments.marketing.manager import MarketingManager
from departments.personal.manager import PersonalManager

from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import (
    assert_valid_event,
    assert_event_matches,
    assert_valid_task,
    assert_valid_dag,
    assert_valid_knowledge,
    assert_valid_cost_tracker_payload,
    create_test_knowledge,
    create_test_task,
    create_test_dag,
    create_test_event,
)


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_os_boot_to_graceful_teardown(fresh_kernel, harness_client):
    """
    Full OS Boot to Graceful Teardown Lifecycle:
    Boot -> Register 9 modules -> Execute 20 multi-department tasks -> Verify CostTracker & MemoryEngine -> Shutdown.
    """
    # 1. Boot fresh kernel and register 9 distinct modules
    model_router = ModelRouter()
    agent_registry = AgentRegistry()
    scheduler = Scheduler()
    memory_engine = MemoryEngine()
    echo_dept = EchoDepartment()
    eng_module = BaseDepartmentModule(EngineeringManager("eng_mgr", "Engineering Manager"))
    res_module = BaseDepartmentModule(ResearchManager("res_mgr", "Research Manager"))
    mkt_module = BaseDepartmentModule(MarketingManager("mkt_mgr", "Marketing Manager"))
    prs_module = BaseDepartmentModule(PersonalManager("prs_mgr", "Personal Manager"))

    modules = [
        model_router,
        agent_registry,
        scheduler,
        memory_engine,
        echo_dept,
        eng_module,
        res_module,
        mkt_module,
        prs_module,
    ]

    for mod in modules:
        fresh_kernel.register_module(mod)

    # Verify at least 9 modules registered
    registered_modules = fresh_kernel.list_modules()
    assert len(registered_modules) >= 9
    for mod in modules:
        assert fresh_kernel.has_module(mod.name)

    # 2. Register agent contracts for 5 departments
    depts = ["engineering", "research", "marketing", "sales", "personal"]
    for dept in depts:
        agent_id = f"{dept}_os_agent"
        contract = AgentContract(
            identity=agent_id,
            department=dept,
            goal=f"OS execution agent for {dept}",
            responsibilities=[f"{dept}_ops"],
            forbidden_actions=[],
            allowed_tools=[f"{dept}_tool"],
            memory_access="admin",
            output_schema={},
        )
        await fresh_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="agent_registry",
                event_type="registry.register_agent",
                payload={"contract": contract.model_dump()},
            )
        )
        await harness_client.wait_for_event(
            event_type="registry.agent_registered",
            predicate=lambda e, aid=agent_id: e.payload.get("identity") == aid,
            timeout=3.0,
        )

    # 3. Create and execute 20 multi-department tasks
    tasks = []
    for i in range(20):
        target_dept = depts[i % len(depts)]
        t = create_test_task(
            description=f"OS Lifecycle Task #{i+1}: {target_dept.capitalize()} execution payload",
            requester=harness_client.name,
        )
        assert_valid_task(t)
        tasks.append(t)

    # Submit tasks in batches
    for t in tasks:
        await fresh_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="scheduler",
                event_type="task.create",
                payload={"task": t.model_dump()},
            )
        )

    # Wait for completion of all 20 tasks
    completed_ids = []
    for t in tasks:
        comp_evt = await harness_client.wait_for_event(
            event_type="task.complete",
            predicate=lambda e, tid=t.id: e.payload.get("task_id") == tid,
            timeout=5.0,
        )
        completed_ids.append(comp_evt.payload["task_id"])
        assert_valid_cost_tracker_payload(comp_evt.payload)

    assert len(completed_ids) == 20

    # 4. Store knowledge entries in MemoryEngine
    for idx in range(5):
        k = create_test_knowledge(
            observation=f"OS Boot Checkpoint #{idx+1} verified operational",
            source="os_lifecycle_test",
            category="system_checkpoint",
            confidence=0.99,
            importance=7,
        )
        assert_valid_knowledge(k)
        await fresh_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="memory_engine",
                event_type="memory.store_knowledge",
                payload={"knowledge": k.model_dump()},
            )
        )
        await harness_client.wait_for_event(
            event_type="memory.knowledge_stored",
            predicate=lambda e, kid=k.id: e.payload.get("knowledge_id") == kid,
            timeout=3.0,
        )

    # 5. Verify Health Status & CostTracker summary
    health = fresh_kernel.get_health_status()
    assert health["status"] == "healthy"
    assert health["module_count"] >= 9

    summary = model_router.cost_tracker.get_summary()
    assert summary["request_count"] >= 20
    assert summary["total_tokens"] > 0
    assert summary["total_cost_usd"] >= 0.0

    # 6. Graceful System Shutdown
    await fresh_kernel.shutdown()
    shutdown_evt = await harness_client.wait_for_event(
        event_type="system.shutdown",
        source="kernel",
        timeout=3.0,
    )
    assert_event_matches(
        shutdown_evt,
        source="kernel",
        destination="*",
        event_type="system.shutdown",
    )


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_high_concurrency_stress_test(full_os_kernel, harness_client):
    """
    High Concurrency Multi-Department Stress Test:
    50 concurrent tasks across all 6 departments via Scheduler & ModelRouter without message loss or queue deadlock.
    """
    # 1. Register agents for all 6 departments into AgentRegistry
    departments = ["engineering", "research", "marketing", "sales", "personal", "echo"]
    for dept in departments:
        agent_id = f"stress_worker_{dept}"
        contract = AgentContract(
            identity=agent_id,
            department=dept,
            goal=f"High concurrency load execution for {dept}",
            responsibilities=["stress_test"],
            forbidden_actions=[],
            allowed_tools=["load_tool"],
            memory_access="admin",
            output_schema={},
        )
        await full_os_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="agent_registry",
                event_type="registry.register_agent",
                payload={"contract": contract.model_dump()},
            )
        )
        await harness_client.wait_for_event(
            event_type="registry.agent_registered",
            predicate=lambda e, aid=agent_id: e.payload.get("identity") == aid,
            timeout=3.0,
        )

    # 2. Prepare 50 concurrent tasks across departments
    tasks = [
        create_test_task(
            description=f"Stress Task #{i+1} for department {departments[i % len(departments)]}",
            requester=harness_client.name,
        )
        for i in range(50)
    ]

    for t in tasks:
        assert_valid_task(t)

    # 3. Fire all 50 task creation events concurrently using asyncio.gather
    await asyncio.gather(*[
        full_os_kernel.send_event(
            create_test_event(
                source=harness_client.name,
                destination="scheduler",
                event_type="task.create",
                payload={"task": t.model_dump()},
            )
        )
        for t in tasks
    ])

    # 4. Wait for completion of all 50 tasks
    completed_task_ids = []
    for t in tasks:
        comp_evt = await harness_client.wait_for_event(
            event_type="task.complete",
            predicate=lambda e, tid=t.id: e.payload.get("task_id") == tid,
            timeout=10.0,
        )
        completed_task_ids.append(comp_evt.payload["task_id"])
        assert_valid_cost_tracker_payload(comp_evt.payload)

    # 5. Assertions: Zero task loss, no deadlocks, 50 completed tasks
    assert len(completed_task_ids) == 50
    assert set(completed_task_ids) == {t.id for t in tasks}

    scheduler = full_os_kernel.get_module("scheduler")
    assert scheduler is not None
    assert len(scheduler.tasks) >= 50
    for t in tasks:
        assert scheduler.tasks[t.id].status == "completed"

    model_router = full_os_kernel.get_module("model_router")
    assert model_router is not None
    summary = model_router.cost_tracker.get_summary()
    assert summary["request_count"] >= 50


@pytest.mark.tier4
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_system_disaster_recovery_and_memory_persistence(tmp_path, harness_client):
    """
    System Disaster Recovery & Memory Persistence:
    Kernel restart reloading active tasks & knowledge graph state from SQLite MemoryEngine.
    """
    db_file = str(tmp_path / "synapse_disaster_recovery.db")

    # =========================================================================
    # PHASE 1: Pre-Crash Operations
    # =========================================================================
    kernel_p1 = Kernel()
    memory_p1 = MemoryEngine(db_path=db_file)
    router_p1 = ModelRouter()
    registry_p1 = AgentRegistry()
    scheduler_p1 = Scheduler()
    harness_p1 = OpaqueTestHarness("harness_p1")

    for mod in [memory_p1, router_p1, registry_p1, scheduler_p1, harness_p1]:
        kernel_p1.register_module(mod)

    # Register an agent
    contract = AgentContract(
        identity="dr_agent",
        department="disaster_recovery",
        goal="Handle system persistence and recovery",
        responsibilities=["data_integrity"],
        forbidden_actions=[],
        allowed_tools=["backup_tool"],
        memory_access="admin",
        output_schema={},
    )
    await kernel_p1.send_event(
        create_test_event(
            source=harness_p1.name,
            destination="agent_registry",
            event_type="registry.register_agent",
            payload={"contract": contract.model_dump()},
        )
    )
    await harness_p1.wait_for_event(event_type="registry.agent_registered", timeout=3.0)

    # Store 10 Knowledge items into SQLite MemoryEngine
    knowledge_items = []
    for idx in range(10):
        k = create_test_knowledge(
            observation=f"Disaster Recovery Checkpoint Record #{idx+1}: Cluster state persistent",
            source="system_dr_harness",
            category=f"checkpoint_cat_{idx % 3}",
            confidence=0.95 + (idx * 0.005),
            importance=idx + 1,
        )
        assert_valid_knowledge(k)
        knowledge_items.append(k)

        await kernel_p1.send_event(
            create_test_event(
                source=harness_p1.name,
                destination="memory_engine",
                event_type="memory.store_knowledge",
                payload={"knowledge": k.model_dump()},
            )
        )
        await harness_p1.wait_for_event(
            event_type="memory.knowledge_stored",
            predicate=lambda e, kid=k.id: e.payload.get("knowledge_id") == kid,
            timeout=3.0,
        )

    # Store active tasks into SQLite tasks table via MemoryEngine DB cursor
    cursor_p1 = memory_p1.conn.cursor()
    saved_tasks = []
    for idx in range(5):
        t = create_test_task(
            description=f"Active persistent task #{idx+1} pre-crash checkpoint",
            requester="dr_test_requester",
        )
        saved_tasks.append(t)
        cursor_p1.execute(
            """
            INSERT INTO tasks (id, description, status, assigned_agent, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (t.id, t.description, "pending", "dr_agent", t.created_at.isoformat()),
        )
    memory_p1.conn.commit()

    # =========================================================================
    # PHASE 2: Simulated System Crash / Disaster
    # =========================================================================
    memory_p1.conn.close()
    kernel_p1 = None
    memory_p1 = None

    # =========================================================================
    # PHASE 3: Post-Disaster Recovery & State Reload
    # =========================================================================
    kernel_p2 = Kernel()
    memory_p2 = MemoryEngine(db_path=db_file)
    harness_p2 = OpaqueTestHarness("harness_p2")

    kernel_p2.register_module(memory_p2)
    kernel_p2.register_module(harness_p2)

    # Query all stored knowledge from recovered MemoryEngine
    await kernel_p2.send_event(
        create_test_event(
            source=harness_p2.name,
            destination="memory_engine",
            event_type="memory.query_knowledge",
            payload={"query": "Disaster Recovery Checkpoint"},
        )
    )

    query_evt = await harness_p2.wait_for_event(
        event_type="memory.query_results",
        predicate=lambda e: e.payload.get("query") == "Disaster Recovery Checkpoint",
        timeout=3.0,
    )
    assert_valid_event(query_evt)
    results = query_evt.payload["results"]

    # Verify all 10 Knowledge records survived kernel restart intact
    assert len(results) == 10
    retrieved_ids = {r["id"] for r in results}
    expected_ids = {k.id for k in knowledge_items}
    assert retrieved_ids == expected_ids

    for r in results:
        assert "Disaster Recovery Checkpoint Record" in r["observation"]
        assert r["source"] == "system_dr_harness"
        assert 0.95 <= r["confidence"] <= 1.0
        assert 1 <= r["importance"] <= 10

    # Inspect raw SQLite database tables to verify task state persistence
    raw_conn = sqlite3.connect(db_file)
    raw_cursor = raw_conn.cursor()
    raw_cursor.execute("SELECT id, description, status FROM tasks")
    db_tasks = raw_cursor.fetchall()
    assert len(db_tasks) == 5

    db_task_ids = {row[0] for row in db_tasks}
    expected_task_ids = {t.id for t in saved_tasks}
    assert db_task_ids == expected_task_ids

    raw_cursor.execute("SELECT COUNT(*) FROM knowledge_graph")
    kg_count = raw_cursor.fetchone()[0]
    assert kg_count == 10

    raw_conn.close()
    memory_p2.conn.close()
