import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from registry.sdk.base_agent import BaseAgent
from departments.sales.manager import SalesManager
from departments.sales.outreach_worker import OutreachWorker, SalesWorker

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
async def test_sales_manager_initialization_and_inheritance():
    """Verify SalesManager inherits Module and BaseAgent and initializes properties correctly."""
    manager = SalesManager(id="sls_unit_1", name="Sales Manager")
    assert isinstance(manager, Module)
    assert isinstance(manager, BaseAgent)
    assert manager.name == "department.sales"
    assert manager.department == "sales"
    assert manager.role == "manager"
    assert "crm_search" in manager.allowed_tools()
    assert "grant_unauthorized_discount" in manager.forbidden_actions()
    assert manager.memory_access_level() == "admin"
    assert len(manager.workers) >= 1

@pytest.mark.asyncio
async def test_sales_manager_can_handle():
    """Verify SalesManager capability matching."""
    manager = SalesManager()
    assert manager.can_handle("Qualify enterprise sales lead") is True
    assert manager.can_handle("Draft cold pitch email") is True
    assert manager.can_handle("Deploy GPU cluster") is False

@pytest.mark.asyncio
async def test_sales_manager_lead_qualification_thresholds():
    """Verify lead score qualification thresholds: <=0 unqualified, <30 disqualified, >=30 qualified."""
    manager = SalesManager()

    # <= 0 -> unqualified
    res_zero = await manager.execute({"description": "Qualify lead", "lead_score": 0})
    assert res_zero["status"] == "success"
    assert res_zero["qualification"] == "unqualified"

    res_neg = await manager.execute({"description": "Qualify lead", "lead_score": -10})
    assert res_neg["status"] == "success"
    assert res_neg["qualification"] == "unqualified"

    # < 30 -> disqualified
    res_disq = await manager.execute({"description": "Qualify lead", "lead_score": 15})
    assert res_disq["status"] == "success"
    assert res_disq["qualification"] == "disqualified"

    # >= 30 -> qualified
    res_qual = await manager.execute({"description": "Qualify lead", "lead_score": 85})
    assert res_qual["status"] == "success"
    assert res_qual["qualification"] == "qualified"

@pytest.mark.asyncio
async def test_sales_manager_empty_company_and_missing_crm_fields():
    """Verify empty company name defaults to 'unknown' and missing email/contact_name are flagged."""
    manager = SalesManager()
    task = {
        "id": "sls-crm-1",
        "description": "Process CRM lead",
        "company": "",
        "email": "",
        "contact_name": "",
        "lead_score": 50,
        "template": None
    }
    res = await manager.execute(task)
    assert res["status"] == "success"
    assert res["company"] == "unknown"
    assert "email" in res["missing_crm_fields"]
    assert "contact_name" in res["missing_crm_fields"]
    assert res["email_template"] == "default_outreach"

@pytest.mark.asyncio
async def test_sales_manager_required_output_substrings_and_no_mocks():
    """Verify SalesManager output contains required key substrings and no mock strings."""
    manager = SalesManager()
    res = await manager.execute({"description": "Lead campaign", "lead_score": 60, "company": "Acme Corp"})
    assert "lead generation campaign executed" in res["result"]
    assert "Sales lead pitch generated successfully" in res["result"]
    assert "mocked" not in str(res).lower()
    assert manager.validate(res) is True

@pytest.mark.asyncio
async def test_sales_manager_kernel_module_registration_and_event_handling():
    """Verify SalesManager direct Kernel Module registration and task completion event emission."""
    kernel = Kernel()
    manager = SalesManager(id="sls_mgr_direct", name="Sales Manager")
    client = MockClient("test_requester")
    kernel.register_module(manager)
    kernel.register_module(client)

    assert "department.sales" in kernel.list_modules()

    exec_event = Event(
        source=client.name,
        destination="department.sales",
        event_type="department.execute_task",
        payload={"task": {"id": "sls-evt-100", "description": "Lead generation for enterprise clients"}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    completed_event = client.received_events[0]
    assert completed_event.payload["status"] == "success"
    assert completed_event.payload["task_id"] == "sls-evt-100"
    assert "lead generation campaign executed" in str(completed_event.payload["result"])
    assert "mocked" not in str(completed_event.payload).lower()

@pytest.mark.asyncio
async def test_sales_manager_event_failure_handling():
    """Verify SalesManager emits department.task_failed on execution failure."""
    kernel = Kernel()
    manager = SalesManager(id="sls_mgr_fail", name="Sales Manager")
    client = MockClient("test_requester")
    kernel.register_module(manager)
    kernel.register_module(client)

    exec_event = Event(
        source=client.name,
        destination="department.sales",
        event_type="department.execute_task",
        payload={"task": {"id": "sls-fail-1", "description": "Discount request", "action": "grant_unauthorized_discount"}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    failed_event = client.received_events[0]
    assert failed_event.payload["status"] == "failed"
    assert failed_event.payload["task_id"] == "sls-fail-1"
    assert "grant_unauthorized_discount" in failed_event.payload["error"]

@pytest.mark.asyncio
async def test_outreach_worker_pitch_generation():
    """Verify OutreachWorker capabilities, tool access, and pitch output containing required substring."""
    worker = OutreachWorker(id="outreach_unit_1", name="Oscar Outreach")
    assert worker.department == "sales"
    assert worker.role == "outreach_specialist"
    assert "pitch_generator" in worker.allowed_tools()
    assert "send_spam_blast" in worker.forbidden_actions()
    assert worker.can_handle("Draft cold email pitch for prospect") is True

    result = await worker.execute("Draft cold email pitch for prospect")
    assert result["status"] == "success"
    assert result["role"] == "outreach_specialist"
    assert "custom sales pitch generated" in result["result"]
    assert "mocked" not in str(result).lower()

@pytest.mark.asyncio
async def test_sales_worker_alias_compatibility():
    """Verify SalesWorker alias behaves identically to OutreachWorker."""
    assert SalesWorker is OutreachWorker
    worker = SalesWorker(id="alias_worker", name="Alias Sales Worker")
    assert worker.role == "outreach_specialist"
    res = await worker.execute("Generate custom pitch")
    assert "custom sales pitch generated" in res["result"]
