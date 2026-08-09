import pytest
import asyncio
from departments.base import BaseDepartmentModule
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_personal_manager_assistant_management(fresh_kernel, harness_client):
    """Test PersonalManager assistant task management via BaseDepartmentModule and Kernel event routing."""
    prs_mgr = PersonalManager(id="prs_mgr_1", name="Personal Manager")
    dept_module = BaseDepartmentModule(prs_mgr)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "prs-t1", "description": "organize personal daily agenda"}}
    )

    await fresh_kernel.send_event(exec_event)

    completed_event = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=dept_module.name,
        timeout=2.0
    )

    assert_event_matches(
        completed_event,
        source=dept_module.name,
        destination=harness_client.name,
        event_type="department.task_completed"
    )
    assert completed_event.payload["status"] == "success"
    assert completed_event.payload["task_id"] == "prs-t1"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_assistant_worker_schedule_execution():
    """Test AssistantWorker schedule task handling, can_handle logic, and execution output."""
    worker = AssistantWorker(id="asst_1", name="Charlie Assistant")

    assert worker.department == "personal"
    assert worker.role == "assistant"
    assert "calendar" in worker.allowed_tools()
    assert worker.can_handle("schedule calendar meeting with team") is True
    assert worker.can_handle("delete production database") is False

    result = await worker.execute({"task_id": "a-1", "description": "schedule meeting"})
    assert result["status"] == "success"
    assert "task" in result


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_assistant_worker_task_execution():
    """Test AssistantWorker general task execution capabilities."""
    worker = AssistantWorker(id="asst_2", name="Charlie Assistant")

    task_payload = {"task_id": "a-2", "description": "personal errand reminder"}
    result = await worker.execute(task_payload)

    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["task"] == task_payload


@pytest.mark.tier1
@pytest.mark.e2e
def test_personal_manager_permissions():
    """Test PersonalManager allowed tools, forbidden actions, and memory access level."""
    prs_mgr = PersonalManager(id="prs_mgr_2", name="Personal Manager")

    tools = prs_mgr.allowed_tools()
    assert isinstance(tools, list)
    assert "contacts" in tools
    assert "finances" in tools

    forbidden = prs_mgr.forbidden_actions()
    assert isinstance(forbidden, list)
    assert "authorize_payments" in forbidden

    assert prs_mgr.memory_access_level() == "admin"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_personal_department_event_routing(fresh_kernel, harness_client):
    """Test direct event routing to Personal department via task.assigned event type."""
    prs_mgr = PersonalManager(id="prs_mgr_3", name="Personal Manager")
    dept_module = BaseDepartmentModule(prs_mgr)

    fresh_kernel.register_module(dept_module)

    assigned_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="task.assigned",
        payload={"task": {"id": "prs-t2", "description": "personal schedule planning"}}
    )

    await fresh_kernel.send_event(assigned_event)

    completed_event = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=dept_module.name,
        timeout=2.0
    )

    assert completed_event.payload["task_id"] == "prs-t2"
