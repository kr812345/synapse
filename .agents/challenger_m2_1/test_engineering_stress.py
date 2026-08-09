import asyncio
import pytest
import sys
from typing import List, Any
from unittest.mock import MagicMock

sys.path.insert(0, "/root/synapse")

from shared.models import Event, Knowledge, Task
from shared.interfaces import Module
from kernel.kernel import Kernel
from memory.memory_engine import MemoryEngine
from tools.tool_registry import ToolRegistry, ToolInterface
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from departments.engineering.qa_worker import QAWorker
from departments.engineering.devops_worker import DevOpsWorker


class MockReceiverModule(Module):
    """Captures outgoing events from Kernel for verification."""
    def __init__(self, name: str = "mock_receiver"):
        self._name = name
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class DummyTerminalTool(ToolInterface):
    name = "terminal"
    description = "Terminal execution tool"
    parameters = {"command": "str"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        cmd = kwargs.get("command", "")
        return {"status": "success", "stdout": f"Executed: {cmd}", "exit_code": 0}


@pytest.mark.asyncio
async def test_stress_keyword_routing_and_disambiguation():
    """Stress test routing across all 3 workers and architecture fallback."""
    eng_mgr = EngineeringManager()

    # QA routing tests
    qa_queries = [
        "run qa automated tests",
        "validate unit test coverage for module",
        "perform code review audit",
        "EXECUTE REGRESSION TESTS AND CODE REVIEW"
    ]
    for q in qa_queries:
        res = await eng_mgr.execute({"id": "qa-1", "description": q})
        assert res["status"] == "success"
        assert res["handled_by"] == "qa_engineer"
        assert "qa_test_execution" in res["result"]["output"]["action"]

    # DevOps routing tests
    devops_queries = [
        "deploy docker container to k8s cluster",
        "setup ci/cd pipeline automation",
        "configure kubernetes deployment and infra health check",
        "CONTAINERIZE APP WITH DOCKER AND K8S PIPELINE"
    ]
    for q in devops_queries:
        res = await eng_mgr.execute({"id": "do-1", "description": q})
        assert res["status"] == "success"
        assert res["handled_by"] == "devops_engineer"
        assert "devops_deployment_config" in res["result"]["output"]["action"]

    # Backend routing tests
    backend_queries = [
        "build backend fastapi endpoint for users",
        "create database crud service",
        "develop api route for authentication",
        "IMPLEMENT SQL DATA MODELS AND REST API"
    ]
    for q in backend_queries:
        res = await eng_mgr.execute({"id": "be-1", "description": q})
        assert res["status"] == "success"
        assert res["handled_by"] == "backend_developer"
        assert "backend_code_generation" in res["result"]["output"]["action"]

    # Manager / Architecture fallback tests
    res_arch = await eng_mgr.execute({"id": "ar-1", "description": "design high availability system architecture"})
    assert res_arch["status"] == "success"
    assert res_arch["handled_by"] == "manager"
    assert res_arch["result"]["action"] == "architecture_design"


@pytest.mark.asyncio
async def test_stress_malformed_and_extreme_payloads():
    """Stress test EngineeringManager and workers with malformed, empty, type-mismatched, and huge payloads."""
    eng_mgr = EngineeringManager()

    # 1. None task
    res_none = await eng_mgr.execute(None)
    assert res_none["status"] == "success"
    assert res_none["handled_by"] == "manager"

    # 2. Empty dict
    res_empty_dict = await eng_mgr.execute({})
    assert res_empty_dict["status"] == "success"
    assert res_empty_dict["handled_by"] == "manager"

    # 3. Empty string / whitespace string
    res_empty_str = await eng_mgr.execute("")
    assert res_empty_str["status"] == "success"
    assert res_empty_str["handled_by"] == "manager"

    res_spaces = await eng_mgr.execute("   \n\t  ")
    assert res_spaces["status"] == "success"
    assert res_spaces["handled_by"] == "manager"

    # 4. Non-string types
    res_int = await eng_mgr.execute(99999)
    assert res_int["status"] == "success"
    assert res_int["handled_by"] == "manager"

    res_list = await eng_mgr.execute(["backend task", "deploy docker"])
    assert res_list["status"] == "success"

    # 5. Giant payload (100,000 chars)
    huge_str = "backend code api " + "x" * 100000
    res_huge = await eng_mgr.execute({"id": "huge-1", "description": huge_str})
    assert res_huge["status"] == "success"
    assert res_huge["handled_by"] == "backend_developer"

    # 6. Special chars and Unicode
    unicode_str = "deploy 🚀 API microservice backend 🔥 / \\ \x00 \n \r ' \" ; -- DROP TABLE"
    res_unicode = await eng_mgr.execute({"id": "u-1", "description": unicode_str})
    assert res_unicode["status"] == "success"


@pytest.mark.asyncio
async def test_null_description_in_dict_payload():
    """Test payload {"id": "t-1", "description": None} to verify null description handling across manager & workers."""
    eng_mgr = EngineeringManager()
    backend_w = BackendWorker()
    qa_w = QAWorker()
    devops_w = DevOpsWorker()

    # Test direct execution on workers
    try:
        res_b = await backend_w.execute({"id": "tb-1", "description": None})
        assert res_b["status"] == "success"
    except (AttributeError, TypeError) as e:
        pytest.fail(f"BackendWorker raised unhandled exception on description=None: {type(e).__name__}: {e}")

    try:
        res_q = await qa_w.execute({"id": "tq-1", "description": None})
        assert res_q["status"] == "success"
    except (AttributeError, TypeError) as e:
        pytest.fail(f"QAWorker raised unhandled exception on description=None: {type(e).__name__}: {e}")

    try:
        res_d = await devops_w.execute({"id": "td-1", "description": None})
        assert res_d["status"] == "success"
    except (AttributeError, TypeError) as e:
        pytest.fail(f"DevOpsWorker raised unhandled exception on description=None: {type(e).__name__}: {e}")

    # Test manager execution
    try:
        res = await eng_mgr.execute({"id": "t-1", "description": None})
        assert res["status"] == "success"
    except (AttributeError, TypeError) as e:
        pytest.fail(f"EngineeringManager raised unhandled exception on task with description=None: {type(e).__name__}: {e}")


@pytest.mark.asyncio
async def test_non_dict_event_payload_in_handle_event():
    """Test handle_event when event.payload is None or non-dict."""
    kernel = Kernel()
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("test_client")

    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    evt_none_payload = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="department.execute_task",
        payload={}
    )
    evt_none_payload.payload = None

    try:
        await eng_mgr.handle_event(evt_none_payload)
    except AttributeError as e:
        pytest.fail(f"EngineeringManager.handle_event raised unhandled AttributeError on event.payload=None: {e}")


@pytest.mark.asyncio
async def test_can_handle_edge_cases():
    """Verify can_handle method on manager and workers handles invalid types without throwing exceptions."""
    eng_mgr = EngineeringManager()
    backend_w = BackendWorker()
    qa_w = QAWorker()
    devops_w = DevOpsWorker()

    invalid_inputs = [None, 123, [], {}, True, False, 3.14]
    for agent in [eng_mgr, backend_w, qa_w, devops_w]:
        for inp in invalid_inputs:
            assert agent.can_handle(inp) is False


@pytest.mark.asyncio
async def test_task_model_object_payload():
    """Test executing with pydantic Task object instance."""
    eng_mgr = EngineeringManager()
    task_obj = Task(id="task-obj-1", description="implement backend user auth service", requester="user")

    res = await eng_mgr.execute(task_obj)
    assert res["status"] == "success"
    assert res["handled_by"] == "backend_developer"


@pytest.mark.asyncio
async def test_end_to_end_kernel_memory_integration():
    """Verify EngineeringManager & Workers execute tasks via Kernel and successfully persist knowledge in MemoryEngine."""
    kernel = Kernel()
    memory_eng = MemoryEngine(db_path=":memory:")
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("test_client")

    kernel.register_module(memory_eng)
    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    task_evt = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "task-mem-101", "description": "build scalable FastAPI backend service"}}
    )

    await kernel.send_event(task_evt)
    await asyncio.sleep(0.1)

    assert len(receiver.received_events) >= 1
    complete_evt = [e for e in receiver.received_events if e.event_type == "department.task_completed"][0]
    assert complete_evt.payload["status"] == "success"
    assert complete_evt.payload["task_id"] == "task-mem-101"

    query_evt = Event(
        source=receiver.name,
        destination=memory_eng.name,
        event_type="memory.query_knowledge",
        payload={"query": "FastAPI"}
    )
    await kernel.send_event(query_evt)
    await asyncio.sleep(0.1)

    query_res_evt = [e for e in receiver.received_events if e.event_type == "memory.query_results"][0]
    assert len(query_res_evt.payload["results"]) > 0
    found_obs = query_res_evt.payload["results"][0]["observation"]
    assert "FastAPI" in found_obs or "backend" in found_obs.lower()


@pytest.mark.asyncio
async def test_tool_registry_integration():
    """Verify BackendWorker interacts with ToolRegistry when tool_registry module is registered in Kernel."""
    kernel = Kernel()
    tool_reg = ToolRegistry()
    dummy_tool = DummyTerminalTool()
    tool_reg.register(dummy_tool)

    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("test_client")

    kernel.register_module(tool_reg)
    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    task_evt = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="engineering.task",
        payload={"task": {"id": "tool-task-1", "description": "create backend database API endpoint"}}
    )

    await kernel.send_event(task_evt)
    await asyncio.sleep(0.1)

    res_event = [e for e in receiver.received_events if e.event_type == "engineering.result"][0]
    assert res_event.payload["status"] == "success"
    worker_res = res_event.payload["result"]["result"]
    assert len(worker_res["tool_calls"]) == 1
    assert worker_res["tool_calls"][0]["tool"] == "terminal"
    assert worker_res["tool_calls"][0]["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_event_handler_failure_isolation():
    """Verify EngineeringManager emits department.task_failed when a worker execution raises an exception."""
    kernel = Kernel()
    eng_mgr = EngineeringManager()
    receiver = MockReceiverModule("test_client")

    kernel.register_module(eng_mgr)
    kernel.register_module(receiver)

    eng_mgr.backend_worker.execute = MagicMock(side_effect=RuntimeError("Simulated worker fatal failure"))

    task_evt = Event(
        source=receiver.name,
        destination=eng_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "fail-task-1", "description": "build backend service"}}
    )

    await kernel.send_event(task_evt)
    await asyncio.sleep(0.1)

    assert len(receiver.received_events) == 1
    fail_evt = receiver.received_events[0]
    assert fail_evt.event_type == "department.task_failed"
    assert fail_evt.payload["status"] == "failed"
    assert fail_evt.payload["task_id"] == "fail-task-1"
    assert "Simulated worker fatal failure" in fail_evt.payload["error"]
