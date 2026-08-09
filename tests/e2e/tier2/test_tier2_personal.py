import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from kernel.kernel import Kernel
from departments.personal.manager import PersonalManager
from departments.personal.assistant_worker import AssistantWorker
from departments.base import BaseDepartmentModule
from tools.tool_registry import ToolRegistry, PermissionDenied, ToolInterface
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event


class FinanceToolMock(ToolInterface):
    name = "finances"
    description = "Personal finance management tool"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"action": "finance_record_added", "kwargs": kwargs}


class PaymentsToolMock(ToolInterface):
    name = "authorize_payments"
    description = "Payment authorization tool"
    parameters = {}
    required_permissions = ["admin"]

    async def execute(self, **kwargs) -> Any:
        return {"action": "payment_authorized"}


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_conflicting_schedule_slots():
    """Verify assistant worker handles overlapping or conflicting schedule time slots."""
    worker = AssistantWorker("prs_wrk_1", "Charlie")

    conflicting_schedule_task = {
        "id": "prs-sched-1",
        "action": "schedule_event",
        "slots": [
            {"start": "2026-08-10T10:00:00Z", "end": "2026-08-10T11:00:00Z"},
            {"start": "2026-08-10T10:30:00Z", "end": "2026-08-10T11:30:00Z"}
        ]
    }

    res = await worker.execute(conflicting_schedule_task)
    assert res["status"] == "success"
    assert worker.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_datetime_inputs():
    """Verify personal department task execution handles invalid or malformed datetime strings."""
    worker = AssistantWorker("prs_wrk_2", "Charlie")

    invalid_date_task = {
        "id": "prs-sched-2",
        "description": "schedule meeting",
        "date_time": "invalid_date_string_2026-99-99"
    }

    res = await worker.execute(invalid_date_task)
    assert res["status"] == "success"
    assert res["task"]["date_time"] == "invalid_date_string_2026-99-99"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_missing_contact_permissions():
    """Verify tool registry permission checks block forbidden financial / payment actions."""
    registry = ToolRegistry()
    registry.register(FinanceToolMock())
    registry.register(PaymentsToolMock())

    manager = PersonalManager("prs_mgr_1", "Personal Manager")
    worker = AssistantWorker("prs_wrk_3", "Charlie")

    # Manager allowed_tools: ['contacts', 'finances']
    fin_res = await registry.execute_tool(manager, "finances", amount=100.0)
    assert fin_res["action"] == "finance_record_added"

    # Manager forbidden_actions: ['authorize_payments']
    with pytest.raises(PermissionDenied):
        await registry.execute_tool(manager, "authorize_payments")

    # Worker allowed_tools: ['calendar', 'email'] -> finances is NOT allowed for worker
    with pytest.raises(PermissionDenied):
        await registry.execute_tool(worker, "finances")


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_assistant_tasks():
    """Verify AssistantWorker execution when task description or payload is empty."""
    worker = AssistantWorker("prs_wrk_4", "Charlie")

    assert worker.can_handle("schedule appointment") is True

    empty_task = {
        "id": "prs-empty-1",
        "description": ""
    }

    res = await worker.execute(empty_task)
    assert res["status"] == "success"
    assert worker.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_finance_payload_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify PersonalManager handles invalid finance payload data gracefully."""
    manager = PersonalManager("prs_mgr_2", "Personal Manager")
    dept_module = BaseDepartmentModule(manager)
    fresh_kernel.register_module(dept_module)

    evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "prs-fin-invalid",
                "description": "process personal transaction",
                "amount": "invalid_amount_str",
                "currency": None
            }
        }
    )

    await fresh_kernel.send_event(evt)

    resp_evt = await harness_client.wait_for_event(event_type="department.task_completed")
    assert resp_evt.payload["status"] == "success"
    assert resp_evt.payload["task_id"] == "prs-fin-invalid"
