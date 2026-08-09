import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from departments.engineering.qa_worker import QAWorker
from departments.engineering.devops_worker import DevOpsWorker
from tools.tool_registry import ToolRegistry, ToolInterface


class MockReceiverModule(Module):
    """Mock receiver module to capture output events from Kernel."""
    def __init__(self, name: str = "mock_receiver"):
        self._name = name
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class MockTerminalTool(ToolInterface):
    name = "terminal"
    description = "Terminal tool for executing commands"
    parameters = {"command": "str"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"status": "executed", "command": kwargs.get("command", "")}


@pytest.mark.asyncio
async def test_engineering_manager_kernel_registration():
    """Verify EngineeringManager inherits Module & BaseAgent and registers directly with Kernel."""
    kernel = Kernel()
    eng_mgr = EngineeringManager(id="eng_mgr_test", name="Engineering Manager")

    assert isinstance(eng_mgr, Module)
    assert eng_mgr.name == "department.engineering"
    assert eng_mgr.department == "engineering"

    kernel.register_module(eng_mgr)
    assert kernel.has_module("department.engineering")
    assert kernel.get_module("department.engineering") is eng_mgr
    assert eng_mgr.kernel is kernel
    assert eng_mgr.backend_worker.kernel is kernel
    assert eng_mgr.qa_worker.kernel is kernel
    assert eng_mgr.devops_worker.kernel is kernel


@pytest.mark.asyncio
async def test_engineering_manager_event_handling_execute_task():
    """Verify department.execute_task event triggers task execution and emits department.task_completed."""
    kernel = Kernel()
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("requester_module")

    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    task_event = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "eng-101", "description": "build user API backend endpoint"}}
    )

    await kernel.send_event(task_event)
    await asyncio.sleep(0.05)

    assert len(receiver.received_events) == 1
    resp = receiver.received_events[0]
    assert resp.event_type == "department.task_completed"
    assert resp.payload["status"] == "success"
    assert resp.payload["task_id"] == "eng-101"
    assert resp.payload["result"]["handled_by"] == "backend_developer"


@pytest.mark.asyncio
async def test_engineering_manager_event_handling_engineering_task():
    """Verify engineering.task event triggers task execution and emits engineering.result."""
    kernel = Kernel()
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("requester_module")

    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    task_event = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="engineering.task",
        payload={"task": {"id": "eng-102", "description": "run qa automated unit tests"}}
    )

    await kernel.send_event(task_event)
    await asyncio.sleep(0.05)

    assert len(receiver.received_events) == 1
    resp = receiver.received_events[0]
    assert resp.event_type == "engineering.result"
    assert resp.payload["status"] == "success"
    assert resp.payload["task_id"] == "eng-102"
    assert resp.payload["result"]["handled_by"] == "qa_engineer"


@pytest.mark.asyncio
async def test_engineering_manager_worker_delegation():
    """Test task delegation to BackendWorker, QAWorker, DevOpsWorker, and direct architecture handling."""
    eng_mgr = EngineeringManager()

    # Backend task
    res_backend = await eng_mgr.execute({"id": "t1", "description": "create database API service endpoints"})
    assert res_backend["handled_by"] == "backend_developer"
    assert res_backend["result"]["output"]["action"] == "backend_code_generation"

    # QA task
    res_qa = await eng_mgr.execute({"id": "t2", "description": "validate test coverage and code review"})
    assert res_qa["handled_by"] == "qa_engineer"
    assert res_qa["result"]["output"]["action"] == "qa_test_execution"

    # DevOps task
    res_devops = await eng_mgr.execute({"id": "t3", "description": "deploy docker container and k8s manifest"})
    assert res_devops["handled_by"] == "devops_engineer"
    assert res_devops["result"]["output"]["action"] == "devops_deployment_config"

    # Architecture task
    res_arch = await eng_mgr.execute({"id": "t4", "description": "design high level system architecture"})
    assert res_arch["handled_by"] == "manager"
    assert res_arch["result"]["action"] == "architecture_design"


@pytest.mark.asyncio
async def test_backend_worker_execution():
    """Verify BackendWorker code generation, tool calls, and memory event integration."""
    kernel = Kernel()
    receiver = MockReceiverModule("memory_engine")
    kernel.register_module(receiver)

    worker = BackendWorker("b_test", "Backend Developer")
    worker.set_kernel(kernel)

    assert worker.can_handle("implement fastapi endpoint") is True
    assert worker.can_handle("design logo") is False

    res = await worker.execute({"id": "b-101", "description": "implement CRUD API endpoint"})
    assert res["status"] == "success"
    assert "FastAPI" in res["output"]["code"]
    assert res["memory_saved"] is True

    await asyncio.sleep(0.05)
    assert len(receiver.received_events) == 1
    mem_evt = receiver.received_events[0]
    assert mem_evt.event_type == "memory.store_knowledge"


@pytest.mark.asyncio
async def test_qa_worker_execution():
    """Verify QAWorker Pytest code generation, test metrics, and code review."""
    worker = QAWorker("qa_test", "QA Specialist")

    assert worker.can_handle("run regression unit test suite") is True
    assert worker.can_handle("deploy k8s") is False

    res = await worker.execute({"id": "q-101", "description": "validate authentication logic"})
    assert res["status"] == "success"
    assert res["role"] == "qa_engineer"
    assert "import pytest" in res["output"]["generated_tests"]
    assert res["output"]["test_results"]["passed"] == 5


@pytest.mark.asyncio
async def test_devops_worker_execution():
    """Verify DevOpsWorker Dockerfile, Kubernetes manifest, and infra health check output."""
    worker = DevOpsWorker("d_test", "DevOps Engineer")

    assert worker.can_handle("deploy docker container to k8s cluster") is True
    assert worker.can_handle("write backend code") is False

    res = await worker.execute({"id": "d-101", "description": "deploy staging environment"})
    assert res["status"] == "success"
    assert res["role"] == "devops_engineer"
    assert "FROM python:3.12-slim" in res["output"]["dockerfile"]
    assert res["output"]["k8s_manifest"]["kind"] == "Deployment"
    assert res["output"]["infra_status"] == "healthy"


@pytest.mark.asyncio
async def test_no_mocked_strings_in_engineering_outputs():
    """Assert that no engineering manager or worker outputs contain mock strings."""
    eng_mgr = EngineeringManager()
    backend_w = BackendWorker()

    mgr_res = await eng_mgr.execute({"id": "chk-1", "description": "engineering task"})
    backend_res = await backend_w.execute({"id": "chk-2", "description": "backend task"})

    assert "mocked engineering manager result" not in str(mgr_res)
    assert "mocked backend result" not in str(backend_res)


@pytest.mark.asyncio
async def test_engineering_manager_handle_event_none_payload():
    """Verify EngineeringManager.handle_event handles Event(payload=None) gracefully without crashing."""
    kernel = Kernel()
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("requester_module")

    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    task_event = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="department.execute_task",
        payload={"task": "dummy"}
    )
    task_event.payload = None  # Force payload to None

    try:
        await kernel.send_event(task_event)
        await asyncio.sleep(0.05)
    except AttributeError as exc:
        pytest.fail(f"EngineeringManager.handle_event raised unhandled AttributeError on payload=None: {exc}")

    assert len(receiver.received_events) == 1
    resp = receiver.received_events[0]
    assert resp.event_type in ("department.task_completed", "department.task_failed")


@pytest.mark.asyncio
async def test_engineering_manager_execute_null_description():
    """Verify EngineeringManager.execute handles task dict with description=None without raising AttributeError."""
    eng_mgr = EngineeringManager()

    task_payload = {"id": "eng-null-desc", "description": None}

    try:
        res = await eng_mgr.execute(task_payload)
        assert res["status"] == "success"
        assert "handled_by" in res
    except AttributeError as exc:
        pytest.fail(f"EngineeringManager.execute raised AttributeError on task description=None: {exc}")


@pytest.mark.asyncio
async def test_engineering_manager_execute_none_task():
    """Verify EngineeringManager.execute handles task=None gracefully."""
    eng_mgr = EngineeringManager()

    try:
        res = await eng_mgr.execute(None)
        assert res["status"] == "success"
        assert res["handled_by"] == "manager"
    except Exception as exc:
        pytest.fail(f"EngineeringManager.execute raised unexpected exception on task=None: {exc}")


@pytest.mark.asyncio
async def test_engineering_workers_none_input_robustness():
    """Verify BackendWorker, QAWorker, and DevOpsWorker handle None task inputs without crashing."""
    backend_w = BackendWorker()
    qa_w = QAWorker()
    devops_w = DevOpsWorker()

    for worker in [backend_w, qa_w, devops_w]:
        res_null_desc = await worker.execute({"id": "w-null", "description": None})
        assert res_null_desc["status"] == "success"

        res_none_task = await worker.execute(None)
        assert res_none_task["status"] == "success"


@pytest.mark.asyncio
async def test_engineering_can_handle_none_inputs():
    """Verify can_handle returns False safely for None, numeric, dict, and list inputs across all engineering agents."""
    eng_mgr = EngineeringManager()
    backend_w = BackendWorker()
    qa_w = QAWorker()
    devops_w = DevOpsWorker()

    invalid_inputs = [None, 123, 45.6, [], {}, True]
    for agent in [eng_mgr, backend_w, qa_w, devops_w]:
        for inp in invalid_inputs:
            assert agent.can_handle(inp) is False
