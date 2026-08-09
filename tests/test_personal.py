import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from registry.sdk.base_agent import BaseAgent
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker

class MockClient(Module):
    def __init__(self, name: str = "mock_client"):
        self._name = name
        self.kernel = None
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_personal_manager_initialization_and_inheritance():
    """Verify PersonalManager inherits Module and BaseAgent and initializes properties correctly."""
    manager = PersonalManager(id="prs_unit_1", name="Personal Manager")
    assert isinstance(manager, Module)
    assert isinstance(manager, BaseAgent)
    assert manager.name == "department.personal"
    assert manager.department == "personal"
    assert manager.role == "manager"
    assert "contacts" in manager.allowed_tools()
    assert "finances" in manager.allowed_tools()
    assert "authorize_payments" in manager.forbidden_actions()
    assert manager.memory_access_level() == "admin"
    assert len(manager.workers) == 1

@pytest.mark.asyncio
async def test_assistant_worker_initialization():
    """Verify AssistantWorker metadata and permissions."""
    worker = AssistantWorker(id="asst_unit_1", name="Charlie Assistant")
    assert isinstance(worker, BaseAgent)
    assert worker.department == "personal"
    assert worker.role == "assistant"
    assert "calendar" in worker.allowed_tools()
    assert "email" in worker.allowed_tools()
    assert "delete_emails" in worker.forbidden_actions()
    assert worker.memory_access_level() == "high"

@pytest.mark.asyncio
async def test_assistant_worker_can_handle():
    """Verify AssistantWorker capability matching."""
    worker = AssistantWorker()
    assert worker.can_handle("Schedule executive meeting") is True
    assert worker.can_handle("Review unread email messages") is True
    assert worker.can_handle("Perform SQL database migration") is False

@pytest.mark.asyncio
async def test_assistant_worker_execute_calendar_and_email_tasks():
    """Verify AssistantWorker task execution for calendar and email tasks without mock strings."""
    worker = AssistantWorker()

    # Calendar task
    cal_res = await worker.execute({"id": "cal-1", "description": "Schedule meeting with team tomorrow at 10am"})
    assert cal_res["status"] == "success"
    assert cal_res["action"] == "calendar_management"
    assert "Calendar events updated" in cal_res["result"]["output"]
    assert "mocked" not in str(cal_res).lower()
    assert worker.validate(cal_res) is True

    # Email task
    email_res = await worker.execute({"id": "em-1", "description": "Draft reply to executive email inquiry"})
    assert email_res["status"] == "success"
    assert email_res["action"] == "email_processing"
    assert "Drafted/reviewed messages" in email_res["result"]["output"]
    assert "mocked" not in str(email_res).lower()

@pytest.mark.asyncio
async def test_assistant_worker_forbidden_action():
    """Verify AssistantWorker blocks delete_emails forbidden action."""
    worker = AssistantWorker()
    task = {"id": "fail-1", "description": "Delete all emails", "action": "delete_emails"}
    with pytest.raises(PermissionError, match="delete_emails"):
        await worker.execute(task)

@pytest.mark.asyncio
async def test_personal_manager_schedule_delegation():
    """Verify PersonalManager delegates schedule/calendar tasks to AssistantWorker."""
    manager = PersonalManager()
    task = {"id": "prs-sched-1", "description": "Schedule personal lunch meeting with mentor"}
    res = await manager.execute(task)
    assert res["status"] == "success"
    assert res["manager"] == "department.personal"
    assert res["delegated_to"] == "Charlie Assistant"
    assert res["result"]["status"] == "success"
    assert "mocked" not in str(res).lower()
    assert manager.validate(res) is True

@pytest.mark.asyncio
async def test_personal_manager_finance_oversight():
    """Verify PersonalManager handles finance and contacts oversight and enforces payment policies."""
    manager = PersonalManager()

    # Normal finance oversight
    fin_task = {"id": "prs-fin-1", "description": "Review monthly personal expense budget"}
    res = await manager.execute(fin_task)
    assert res["status"] == "success"
    assert res["oversight_type"] == "finance_and_contacts"
    assert res["result"]["payments_authorized"] is False
    assert "mocked" not in str(res).lower()

    # Forbidden action check
    forbidden_task = {"id": "prs-fin-2", "description": "Pay wire transfer", "action": "authorize_payments"}
    with pytest.raises(PermissionError, match="authorize_payments"):
        await manager.execute(forbidden_task)

@pytest.mark.asyncio
async def test_personal_manager_kernel_registration_and_event_routing():
    """Verify PersonalManager registers with Kernel as Module and handles incoming events."""
    kernel = Kernel()
    manager = PersonalManager(id="prs_mgr_direct", name="Personal Manager")
    client = MockClient("test_requester")
    kernel.register_module(manager)
    kernel.register_module(client)

    assert "department.personal" in kernel.list_modules()

    exec_event = Event(
        source=client.name,
        destination="department.personal",
        event_type="department.execute_task",
        payload={"task": {"id": "prs-evt-1", "description": "Organize personal weekly agenda"}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    completed_event = client.received_events[0]
    assert completed_event.payload["status"] == "success"
    assert completed_event.payload["task_id"] == "prs-evt-1"
    assert "mocked" not in str(completed_event.payload).lower()

@pytest.mark.asyncio
async def test_personal_manager_event_failure_handling():
    """Verify PersonalManager emits department.task_failed on execution failure."""
    kernel = Kernel()
    manager = PersonalManager(id="prs_mgr_fail", name="Personal Manager")
    client = MockClient("test_requester")
    kernel.register_module(manager)
    kernel.register_module(client)

    exec_event = Event(
        source=client.name,
        destination="department.personal",
        event_type="department.execute_task",
        payload={"task": {"id": "prs-fail-1", "description": "Authorize payment", "action": "authorize_payments"}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    failed_event = client.received_events[0]
    assert failed_event.payload["status"] == "failed"
    assert failed_event.payload["task_id"] == "prs-fail-1"
    assert "authorize_payments" in failed_event.payload["error"]
