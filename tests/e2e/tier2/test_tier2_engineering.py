import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from kernel.kernel import Kernel
from departments.engineering.manager import EngineeringManager
from departments.engineering.backend_worker import BackendWorker
from departments.base import BaseDepartmentModule
from tools.tool_registry import ToolRegistry, PermissionDenied, ToolInterface
from registry.sdk.base_agent import BaseAgent
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event


class SampleTool(ToolInterface):
    name = "jira"
    description = "Jira issue tracking tool"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"action": "jira_exec", "kwargs": kwargs}


class UnauthorizedTool(ToolInterface):
    name = "deploy_prod"
    description = "Deploy to production"
    parameters = {}
    required_permissions = ["admin"]

    async def execute(self, **kwargs) -> Any:
        return {"action": "deployed"}


class FailingEngineeringWorker(BaseAgent):
    def __init__(self, id: str = "failing_eng_worker", name: str = "Failing Dev"):
        super().__init__(id=id, name=name, department="engineering", role="backend_developer")

    def allowed_tools(self) -> List[str]:
        return ["terminal"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "low"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        raise RuntimeError("Build error: Compilation failed in C++ module")

    def validate(self, result: Any) -> bool:
        return False

    def report(self) -> Any:
        return {"status": "error"}

    def remember(self, knowledge: Any) -> None:
        pass


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_unauthorized_tool_invocation_raising_permission_denied():
    """Verify ToolRegistry raises PermissionDenied when an agent invokes an unauthorized tool."""
    registry = ToolRegistry()
    registry.register(SampleTool())
    registry.register(UnauthorizedTool())

    manager = EngineeringManager("eng_mgr_1", "Alice")
    worker = BackendWorker("eng_wrk_1", "Bob")

    # EngineeringManager allowed_tools: ['jira', 'github'] -> deploy_prod is NOT allowed
    with pytest.raises(PermissionDenied, match="does not have permission to execute deploy_prod"):
        await registry.execute_tool(manager, "deploy_prod")

    # BackendWorker allowed_tools: ['terminal', 'ide'] -> jira is NOT allowed
    with pytest.raises(PermissionDenied, match="does not have permission to execute jira"):
        await registry.execute_tool(worker, "jira")


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_task_payload_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify BaseDepartmentModule handles invalid task event payloads without unhandled exceptions."""
    manager = EngineeringManager("eng_mgr_2", "Alice")
    dept_module = BaseDepartmentModule(manager)
    fresh_kernel.register_module(dept_module)

    # Send event with malformed payload (missing task struct)
    evt_invalid = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={}
    )

    await fresh_kernel.send_event(evt_invalid)

    # Department module processes invalid payload gracefully and responds with task completed event
    resp_evt = await harness_client.wait_for_event(event_type="department.task_completed")
    assert resp_evt.source == dept_module.name
    assert resp_evt.payload["status"] == "success"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_worker_execution_error_recovery(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify department event handler captures worker execution failures and emits task_failed events."""
    failing_worker = FailingEngineeringWorker()
    dept_module = BaseDepartmentModule(failing_worker)
    fresh_kernel.register_module(dept_module)

    exec_evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "task-eng-fail", "description": "Compile C++ module"}}
    )

    await fresh_kernel.send_event(exec_evt)

    fail_evt = await harness_client.wait_for_event(event_type="department.task_failed")
    assert fail_evt.payload["status"] == "failed"
    assert fail_evt.payload["task_id"] == "task-eng-fail"
    assert "Compilation failed in C++ module" in fail_evt.payload["error"]


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_code_artifact_handling():
    """Verify backend developer worker handles empty or missing code artifacts cleanly."""
    worker = BackendWorker("eng_wrk_2", "Bob")

    empty_code_task = {
        "id": "t-empty-code",
        "description": "backend refactor with empty diff",
        "code_artifact": ""
    }

    result = await worker.execute(empty_code_task)
    assert result["status"] == "success"
    assert result["task"] == empty_code_task
    assert worker.validate(result) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_tool_permissions():
    """Verify permission check robustness when agent returns empty, None, or invalid allowed_tools list."""
    registry = ToolRegistry()
    registry.register(SampleTool())

    class RestrictedAgent:
        id = "restricted_agent"
        allowed_tools = []

    class NoToolsAgent:
        id = "no_tools_agent"

    agent_empty = RestrictedAgent()
    agent_none = NoToolsAgent()

    with pytest.raises(PermissionDenied):
        await registry.execute_tool(agent_empty, "jira")

    with pytest.raises(PermissionDenied):
        await registry.execute_tool(agent_none, "jira")
