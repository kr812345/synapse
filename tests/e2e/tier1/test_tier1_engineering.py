import pytest
import asyncio
from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from departments.base import BaseDepartmentModule
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from tools.tool_registry import ToolRegistry, ToolInterface
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


class QAWorker(BaseAgent):
    """QA Worker agent for testing engineering department quality assurance tasks."""
    def __init__(self, id: str = "qa_worker_1", name: str = "Alice QA"):
        super().__init__(id=id, name=name, department="engineering", role="qa_engineer")

    def allowed_tools(self) -> List[str]:
        return ["pytest", "coverage_tool"]

    def forbidden_actions(self) -> List[str]:
        return ["skip_failing_tests"]

    def memory_access_level(self) -> str:
        return "high"

    def can_handle(self, task_description: str) -> bool:
        return "qa" in task_description.lower() or "test" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "role": self.role, "task": task, "result": "qa suite validation passed"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass


class DevOpsWorker(BaseAgent):
    """DevOps Worker agent for testing engineering department deployment and infra tasks."""
    def __init__(self, id: str = "devops_worker_1", name: str = "Dave DevOps"):
        super().__init__(id=id, name=name, department="engineering", role="devops_engineer")

    def allowed_tools(self) -> List[str]:
        return ["docker", "kubectl", "terminal"]

    def forbidden_actions(self) -> List[str]:
        return ["drop_production_db"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "devops" in task_description.lower() or "deploy" in task_description.lower() or "infra" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "role": self.role, "task": task, "result": "deployment pipeline executed"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass


class MockEngineeringTool(ToolInterface):
    name = "terminal"
    description = "Terminal tool for executing commands"
    parameters = {"command": "str"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"status": "executed", "command": kwargs.get("command", "")}


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_engineering_manager_task_execution(fresh_kernel, harness_client):
    """Test EngineeringManager task execution via BaseDepartmentModule and Kernel event routing."""
    eng_mgr = EngineeringManager(id="eng_mgr_1", name="Engineering Manager")
    dept_module = BaseDepartmentModule(eng_mgr)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "eng-t1", "description": "build engineering core module"}}
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
    assert completed_event.payload["task_id"] == "eng-t1"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_backend_worker_task_execution():
    """Test BackendWorker capabilities, can_handle logic, and direct task execution."""
    worker = BackendWorker(id="backend_1", name="Bob Developer")

    assert worker.department == "engineering"
    assert worker.role == "backend_developer"
    assert "terminal" in worker.allowed_tools()
    assert worker.can_handle("implement backend API endpoint") is True
    assert worker.can_handle("social marketing post") is False

    result = await worker.execute({"task_id": "b-1", "description": "build API route"})
    assert result["status"] == "success"
    assert "task" in result


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_qa_worker_task_execution():
    """Test QAWorker capabilities, task handling, and test validation execution."""
    worker = QAWorker(id="qa_1", name="Alice QA")

    assert worker.department == "engineering"
    assert worker.role == "qa_engineer"
    assert "pytest" in worker.allowed_tools()
    assert worker.can_handle("run qa integration test suite") is True
    assert worker.can_handle("design logo") is False

    result = await worker.execute("Run regression test suite")
    assert result["status"] == "success"
    assert result["role"] == "qa_engineer"
    assert "qa suite validation passed" in result["result"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_devops_worker_task_execution():
    """Test DevOpsWorker capabilities, deployment task handling, and execution output."""
    worker = DevOpsWorker(id="devops_1", name="Dave DevOps")

    assert worker.department == "engineering"
    assert worker.role == "devops_engineer"
    assert "docker" in worker.allowed_tools()
    assert worker.can_handle("deploy k8s cluster infra") is True
    assert worker.can_handle("write blog article") is False

    result = await worker.execute("Deploy staging environment")
    assert result["status"] == "success"
    assert result["role"] == "devops_engineer"
    assert "deployment pipeline executed" in result["result"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_engineering_tool_execution(fresh_kernel, harness_client):
    """Test tool execution by engineering agents via ToolRegistry module."""
    registry = ToolRegistry()
    tool = MockEngineeringTool()
    registry.register(tool)

    fresh_kernel.register_module(registry)

    worker = BackendWorker(id="backend_tool_user", name="Bob Developer")

    exec_event = create_test_event(
        source=harness_client.name,
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "terminal",
            "agent": {"id": worker.id, "allowed_tools": worker.allowed_tools()},
            "kwargs": {"command": "pytest tests/"}
        }
    )

    await fresh_kernel.send_event(exec_event)

    result_event = await harness_client.wait_for_event(
        event_type="tool.execution_result",
        source="tool_registry",
        timeout=2.0
    )

    assert_event_matches(
        result_event,
        source="tool_registry",
        destination=harness_client.name,
        event_type="tool.execution_result"
    )
    assert result_event.payload["status"] == "success"
    assert result_event.payload["result"]["status"] == "executed"
    assert result_event.payload["result"]["command"] == "pytest tests/"
