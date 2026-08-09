import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from shared.models import Event
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from departments.engineering.qa_worker import QAWorker
from departments.engineering.devops_worker import DevOpsWorker


class MockTaskObjWithNoneDesc:
    def __init__(self):
        self.id = "mock-task-none-desc"
        self.description = None


class MockTaskObjWithoutAttrs:
    pass


class MockEventWithNonePayload:
    def __init__(self):
        self.source = "test_caller"
        self.destination = "department.engineering"
        self.event_type = "department.execute_task"
        self.payload = None


@pytest.mark.asyncio
async def test_engineering_manager_event_payload_none():
    manager = EngineeringManager()
    kernel = MagicMock()
    kernel.send_event = AsyncMock()
    manager.set_kernel(kernel)

    # Test with pydantic Event where payload attribute is manually set to None
    event1 = Event(
        source="test_caller",
        destination="department.engineering",
        event_type="department.execute_task",
        payload={}
    )
    event1.payload = None

    await manager.handle_event(event1)

    assert kernel.send_event.called
    response_event1 = kernel.send_event.call_args[0][0]
    assert response_event1.event_type == "department.task_completed"
    assert response_event1.payload["status"] == "success"

    # Test with duck-typed mock event having payload = None
    kernel.send_event.reset_mock()
    event2 = MockEventWithNonePayload()
    await manager.handle_event(event2)

    assert kernel.send_event.called
    response_event2 = kernel.send_event.call_args[0][0]
    assert response_event2.event_type == "department.task_completed"
    assert response_event2.payload["status"] == "success"


@pytest.mark.asyncio
async def test_engineering_manager_task_none_in_payload():
    manager = EngineeringManager()
    kernel = MagicMock()
    kernel.send_event = AsyncMock()
    manager.set_kernel(kernel)

    event = Event(
        source="test_caller",
        destination="department.engineering",
        event_type="engineering.task",
        payload={"task": None}
    )

    await manager.handle_event(event)

    assert kernel.send_event.called
    response_event = kernel.send_event.call_args[0][0]
    assert response_event.event_type == "engineering.result"
    assert response_event.payload["status"] == "success"


@pytest.mark.asyncio
async def test_engineering_manager_task_dict_description_none():
    manager = EngineeringManager()
    kernel = MagicMock()
    kernel.send_event = AsyncMock()
    manager.set_kernel(kernel)

    event = Event(
        source="test_caller",
        destination="department.engineering",
        event_type="task.assigned",
        payload={"task": {"id": "t-null-desc", "description": None}}
    )

    await manager.handle_event(event)

    assert kernel.send_event.called
    response_event = kernel.send_event.call_args[0][0]
    assert response_event.event_type == "task.complete"
    assert response_event.payload["status"] == "success"
    assert response_event.payload["task_id"] == "t-null-desc"


@pytest.mark.asyncio
async def test_engineering_manager_task_dict_task_description_none():
    manager = EngineeringManager()
    result = await manager.execute({"task_id": "t-raw-null", "task_description": None})
    assert result["status"] == "success"
    assert result["handled_by"] == "manager"


@pytest.mark.asyncio
async def test_engineering_manager_non_dict_task_types():
    manager = EngineeringManager()
    
    res_int = await manager.execute(12345)
    assert res_int["status"] == "success"

    res_list = await manager.execute(["code", "backend"])
    assert res_list["status"] == "success"
    assert res_list["handled_by"] == "backend_developer"

    res_obj = await manager.execute(MockTaskObjWithNoneDesc())
    assert res_obj["status"] == "success"

    res_empty_obj = await manager.execute(MockTaskObjWithoutAttrs())
    assert res_empty_obj["status"] == "success"


@pytest.mark.asyncio
async def test_engineering_workers_none_and_bad_types():
    workers = [BackendWorker(), QAWorker(), DevOpsWorker()]
    
    for worker in workers:
        # None task
        r1 = await worker.execute(None)
        assert r1["status"] == "success"

        # Dict with None description
        r2 = await worker.execute({"id": "w-null", "description": None})
        assert r2["status"] == "success"

        # Non-string types
        r3 = await worker.execute(9999)
        assert r3["status"] == "success"

        r4 = await worker.execute(MockTaskObjWithNoneDesc())
        assert r4["status"] == "success"


def test_can_handle_adversarial_inputs():
    agents = [EngineeringManager(), BackendWorker(), QAWorker(), DevOpsWorker()]

    adversarial_inputs = [None, 123, 45.67, [], {}, False, True, MockTaskObjWithNoneDesc()]
    for agent in agents:
        for inp in adversarial_inputs:
            assert agent.can_handle(inp) is False

    # Empty and whitespace strings
    for agent in agents:
        assert agent.can_handle("") is False
        assert agent.can_handle("   ") is False


@pytest.mark.asyncio
async def test_engineering_manager_exception_isolation():
    manager = EngineeringManager()
    kernel = MagicMock()
    kernel.send_event = AsyncMock()
    manager.set_kernel(kernel)

    # Force qa_worker execute to raise an exception
    manager.qa_worker.execute = AsyncMock(side_effect=RuntimeError("QA worker crashed under load"))

    event = Event(
        source="test_caller",
        destination="department.engineering",
        event_type="department.execute_task",
        payload={"task": {"id": "t-crash", "description": "run QA tests"}}
    )

    await manager.handle_event(event)

    assert kernel.send_event.called
    failure_event = kernel.send_event.call_args[0][0]
    assert failure_event.event_type == "department.task_failed"
    assert failure_event.payload["status"] == "failed"
    assert failure_event.payload["task_id"] == "t-crash"
    assert "QA worker crashed under load" in failure_event.payload["error"]
