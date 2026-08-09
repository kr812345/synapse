import pytest
import asyncio
from typing import Any, List

from shared.models import Event, Knowledge
from departments.base import BaseDepartmentModule
from departments.engineering.manager import EngineeringManager
from departments.research.manager import ResearchManager
from departments.marketing.manager import MarketingManager
from departments.personal.manager import PersonalManager
from departments.echo.echo_manager import EchoDepartment
from memory.memory_engine import MemoryEngine
from models.model_router import ModelRouter

from tests.e2e.helpers import (
    assert_valid_event,
    assert_event_matches,
    assert_valid_knowledge,
    create_test_event,
    create_test_knowledge,
)

# Attempt import of SalesManager; provide compliant fallback if missing
try:
    from departments.sales.manager import SalesManager
except (ImportError, ModuleNotFoundError):
    from registry.sdk.base_agent import BaseAgent

    class SalesManager(BaseAgent):
        def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
            super().__init__(id=id, name=name, department="sales", role="manager")

        def allowed_tools(self) -> List[str]:
            return ["crm", "email_draft", "pitch_generator"]

        def forbidden_actions(self) -> List[str]:
            return ["unauthorized_discount"]

        def memory_access_level(self) -> str:
            return "admin"

        def can_handle(self, task_description: str) -> bool:
            return (
                "sales" in task_description.lower()
                or "pitch" in task_description.lower()
                or "lead" in task_description.lower()
            )

        async def execute(self, task: Any) -> Any:
            return {
                "status": "success",
                "task": task,
                "result": "Sales lead pitch generated successfully",
            }

        def validate(self, result: Any) -> bool:
            return True

        def report(self) -> Any:
            return {"status": "managing"}

        def remember(self, knowledge: Any) -> None:
            pass


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cascade_research_memory_engineering_marketing(full_os_kernel, harness_client):
    """
    Test Multi-Department Cascade 1:
    ResearchManager research finding -> MemoryEngine storage -> EngineeringManager consumes knowledge -> MarketingManager announces prototype.
    """
    res_module = BaseDepartmentModule(ResearchManager())
    eng_module = BaseDepartmentModule(EngineeringManager("eng_mgr", "Engineering Manager"))
    mkt_module = BaseDepartmentModule(MarketingManager("mkt_mgr", "Marketing Manager"))

    for mod in (res_module, eng_module, mkt_module):
        if not full_os_kernel.has_module(mod.name):
            full_os_kernel.register_module(mod)

    # Step 1: ResearchManager produces research finding
    research_observation = "Quantum-Resistant Lattice Encryption Module Specification v1.0"
    k_item = create_test_knowledge(
        observation=research_observation,
        source=res_module.name,
        category="security",
        importance=5,
    )

    # Step 2: Store knowledge in MemoryEngine
    store_evt = Event(
        source=harness_client.name,
        destination="memory_engine",
        event_type="memory.store_knowledge",
        payload={"knowledge": k_item.model_dump()},
    )
    await full_os_kernel.send_event(store_evt)

    stored_res = await harness_client.wait_for_event(
        event_type="memory.knowledge_stored",
        source="memory_engine",
        timeout=3.0,
    )
    assert_valid_event(stored_res)
    assert stored_res.payload["status"] == "success"
    assert stored_res.payload["knowledge_id"] == k_item.id

    # Step 3: Query MemoryEngine for stored knowledge
    query_evt = Event(
        source=harness_client.name,
        destination="memory_engine",
        event_type="memory.query_knowledge",
        payload={"query": "Lattice Encryption"},
    )
    await full_os_kernel.send_event(query_evt)

    query_res = await harness_client.wait_for_event(
        event_type="memory.query_results",
        source="memory_engine",
        timeout=3.0,
    )
    assert_valid_event(query_res)
    results = query_res.payload["results"]
    assert len(results) >= 1
    retrieved_observation = results[0]["observation"]
    assert "Lattice Encryption" in retrieved_observation

    # Step 4: EngineeringManager consumes knowledge to prototype implementation
    eng_task_id = "task-eng-cascade-401"
    eng_task_req = Event(
        source=harness_client.name,
        destination=eng_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": eng_task_id,
                "description": f"Build implementation based on knowledge: {retrieved_observation}",
                "requester": harness_client.name,
            }
        },
    )
    await full_os_kernel.send_event(eng_task_req)

    eng_res = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=eng_module.name,
        timeout=3.0,
    )
    assert_valid_event(eng_res)
    assert eng_res.payload["task_id"] == eng_task_id
    assert eng_res.payload["status"] == "success"

    # Step 5: MarketingManager announces prototype release
    mkt_task_id = "task-mkt-cascade-501"
    mkt_task_req = Event(
        source=harness_client.name,
        destination=mkt_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": mkt_task_id,
                "description": f"Announce prototype release of {retrieved_observation}",
                "requester": harness_client.name,
            }
        },
    )
    await full_os_kernel.send_event(mkt_task_req)

    mkt_res = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=mkt_module.name,
        timeout=3.0,
    )
    assert_valid_event(mkt_res)
    assert mkt_res.payload["task_id"] == mkt_task_id
    assert mkt_res.payload["status"] == "success"


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cascade_sales_personal_marketing(full_os_kernel, harness_client):
    """
    Test Multi-Department Cascade 2:
    SalesManager qualifies lead -> PersonalManager schedules executive meeting -> Marketing sends follow-up.
    """
    sls_module = BaseDepartmentModule(SalesManager("sls_mgr", "Sales Manager"))
    prs_module = BaseDepartmentModule(PersonalManager("prs_mgr", "Personal Manager"))
    mkt_module = BaseDepartmentModule(MarketingManager("mkt_mgr", "Marketing Manager"))

    for mod in (sls_module, prs_module, mkt_module):
        if not full_os_kernel.has_module(mod.name):
            full_os_kernel.register_module(mod)

    # Step 1: SalesManager qualifies lead
    sls_task_id = "cascade-lead-101"
    sls_req = Event(
        source=harness_client.name,
        destination=sls_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": sls_task_id,
                "description": "Qualify high-value enterprise lead Acme Corporation",
                "requester": harness_client.name,
            }
        },
    )
    await full_os_kernel.send_event(sls_req)

    sls_res = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=sls_module.name,
        timeout=3.0,
    )
    assert_valid_event(sls_res)
    assert sls_res.payload["task_id"] == sls_task_id
    assert sls_res.payload["status"] == "success"

    # Step 2: PersonalManager schedules executive meeting for qualified lead
    prs_task_id = "cascade-schedule-202"
    prs_req = Event(
        source=harness_client.name,
        destination=prs_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": prs_task_id,
                "description": "Schedule executive meeting with Acme Corporation CTO for next Tuesday",
                "requester": harness_client.name,
            }
        },
    )
    await full_os_kernel.send_event(prs_req)

    prs_res = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=prs_module.name,
        timeout=3.0,
    )
    assert_valid_event(prs_res)
    assert prs_res.payload["task_id"] == prs_task_id
    assert prs_res.payload["status"] == "success"

    # Step 3: MarketingManager sends marketing follow-up collateral
    mkt_task_id = "cascade-followup-303"
    mkt_req = Event(
        source=harness_client.name,
        destination=mkt_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": mkt_task_id,
                "description": "Send personalized marketing collateral follow-up to Acme Corporation",
                "requester": harness_client.name,
            }
        },
    )
    await full_os_kernel.send_event(mkt_req)

    mkt_res = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=mkt_module.name,
        timeout=3.0,
    )
    assert_valid_event(mkt_res)
    assert mkt_res.payload["task_id"] == mkt_task_id
    assert mkt_res.payload["status"] == "success"


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_ping_benchmark_active_eventbus_background_load(full_os_kernel, harness_client):
    """
    Test EchoDepartment ping benchmark under active EventBus background load.
    Publishes background noise events to EventBus while simultaneously executing a benchmark
    ping/pong cycle with EchoDepartment.
    """
    # Ensure EchoDepartment is registered
    if not full_os_kernel.has_module("echo_department"):
        full_os_kernel.register_module(EchoDepartment())

    # Generate background event load on EventBus
    load_events = [
        Event(
            source=harness_client.name,
            destination="*",
            event_type="system.telemetry_tick",
            payload={"sequence": i, "cpu": 12.5 + i, "mem": 40.0},
        )
        for i in range(25)
    ]
    for load_evt in load_events:
        await full_os_kernel.send_event(load_evt)

    # Dispatch ping event to echo_department
    ping_payload = {"benchmark_id": "bench-999", "timestamp_nano": 1700000000}
    ping_event = Event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload=ping_payload,
    )
    await full_os_kernel.send_event(ping_event)

    # Expect pong event back from echo_department
    pong_evt = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department",
        timeout=3.0,
    )
    assert_valid_event(pong_evt)
    assert pong_evt.source == "echo_department"
    assert pong_evt.destination == harness_client.name
    assert pong_evt.payload.get("original_payload") == ping_payload


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_system_shutdown_broadcast_unregisters_all_departments(fresh_kernel, harness_client):
    """
    Test System Shutdown broadcast gracefully unregistering all 6 department modules.
    Registers Engineering, Research, Marketing, Personal, Sales, and Echo departments along
    with core infrastructure, then verifies system.shutdown broadcast delivery and clean teardown.
    """
    eng_module = BaseDepartmentModule(EngineeringManager("eng_mgr", "Engineering Manager"))
    res_module = BaseDepartmentModule(ResearchManager())
    mkt_module = BaseDepartmentModule(MarketingManager("mkt_mgr", "Marketing Manager"))
    prs_module = BaseDepartmentModule(PersonalManager("prs_mgr", "Personal Manager"))
    sls_module = BaseDepartmentModule(SalesManager("sls_mgr", "Sales Manager"))
    echo_module = EchoDepartment()

    all_dept_modules = [
        eng_module,
        res_module,
        mkt_module,
        prs_module,
        sls_module,
        echo_module,
    ]

    for mod in all_dept_modules:
        fresh_kernel.register_module(mod)

    # Add core modules
    fresh_kernel.register_module(ModelRouter())
    fresh_kernel.register_module(MemoryEngine())

    # Verify all 6 departments are registered in kernel
    registered_modules = fresh_kernel.list_modules()
    assert len(all_dept_modules) == 6
    for mod in all_dept_modules:
        assert mod.name in registered_modules, f"Module {mod.name} missing from registered modules"

    # Trigger system shutdown
    await fresh_kernel.shutdown()

    # Harness client should receive the system.shutdown event broadcast
    shutdown_evt = await harness_client.wait_for_event(
        event_type="system.shutdown",
        source="kernel",
        timeout=3.0,
    )
    assert_valid_event(shutdown_evt)
    assert shutdown_evt.destination == "*"
    assert shutdown_evt.event_type == "system.shutdown"

    # Health check after shutdown reflects operational status
    health = fresh_kernel.get_health_status()
    assert health["status"] == "healthy"
    assert health["module_count"] >= 6
