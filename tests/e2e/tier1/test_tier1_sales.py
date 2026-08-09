import pytest
import asyncio
from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from departments.base import BaseDepartmentModule
from tools.tool_registry import ToolRegistry, ToolInterface
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


class SalesManager(BaseAgent):
    """Sales Manager agent for lead generation and commercial operations."""
    def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
        super().__init__(id=id, name=name, department="sales", role="manager")

    def allowed_tools(self) -> List[str]:
        return ["crm_search", "lead_qualifier", "email_sender"]

    def forbidden_actions(self) -> List[str]:
        return ["grant_unauthorized_discount"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "sales" in task_description.lower() or "lead" in task_description.lower() or "deal" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "lead generation campaign executed"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass


class OutreachWorker(BaseAgent):
    """Outreach Worker agent for email pitch generation and client outreach."""
    def __init__(self, id: str = "outreach_w1", name: str = "Oscar Outreach"):
        super().__init__(id=id, name=name, department="sales", role="outreach_specialist")

    def allowed_tools(self) -> List[str]:
        return ["email_draft", "pitch_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["send_spam_blast"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        return "pitch" in task_description.lower() or "outreach" in task_description.lower() or "email" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "role": self.role, "task": task, "result": "custom sales pitch generated"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass


class FailingSalesWorker(BaseAgent):
    """Failing Sales agent to test exception handling and task failure events."""
    def __init__(self, id: str = "failing_sls", name: str = "Failing Sales Agent"):
        super().__init__(id=id, name=name, department="sales", role="failing_worker")

    def allowed_tools(self) -> List[str]:
        return []

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "low"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        raise RuntimeError("CRM API connection refused")

    def validate(self, result: Any) -> bool:
        return False

    def report(self) -> Any:
        return {}

    def remember(self, knowledge: Any) -> None:
        pass


class MockCRMTool(ToolInterface):
    name = "crm_search"
    description = "CRM database lookup tool"
    parameters = {"query": "str"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"status": "success", "query": kwargs.get("query", ""), "records_found": 5}


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sales_manager_lead_generation(fresh_kernel, harness_client):
    """Test SalesManager lead generation task execution via BaseDepartmentModule and Kernel event routing."""
    sls_mgr = SalesManager(id="sls_mgr_1", name="Sales Manager")
    dept_module = BaseDepartmentModule(sls_mgr)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "sls-t1", "description": "lead generation for enterprise clients"}}
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
    assert completed_event.payload["task_id"] == "sls-t1"
    assert "lead generation campaign executed" in completed_event.payload["result"]["result"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_outreach_worker_pitch_generation():
    """Test OutreachWorker capabilities, can_handle matching, and pitch generation task execution."""
    worker = OutreachWorker(id="outreach_1", name="Oscar Outreach")

    assert worker.department == "sales"
    assert worker.role == "outreach_specialist"
    assert "pitch_generator" in worker.allowed_tools()
    assert worker.can_handle("generate email pitch for client prospect") is True
    assert worker.can_handle("refactor C++ codebase") is False

    result = await worker.execute("Draft cold outreach email pitch")
    assert result["status"] == "success"
    assert result["role"] == "outreach_specialist"
    assert "custom sales pitch generated" in result["result"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_crm_tool_execution(fresh_kernel, harness_client):
    """Test executing CRM tools via ToolRegistry module for sales agents."""
    registry = ToolRegistry()
    tool = MockCRMTool()
    registry.register(tool)

    fresh_kernel.register_module(registry)

    sls_mgr = SalesManager(id="sls_crm_user", name="Sales Manager")

    exec_event = create_test_event(
        source=harness_client.name,
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "crm_search",
            "agent": {"id": sls_mgr.id, "allowed_tools": sls_mgr.allowed_tools()},
            "kwargs": {"query": "Acme Corp"}
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
    assert result_event.payload["result"]["records_found"] == 5


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sales_department_task_failure_handling(fresh_kernel, harness_client):
    """Test that task execution exceptions in BaseDepartmentModule emit department.task_failed events."""
    failing_agent = FailingSalesWorker()
    dept_module = BaseDepartmentModule(failing_agent)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "sls-fail-1", "description": "query sales database"}}
    )

    await fresh_kernel.send_event(exec_event)

    failure_event = await harness_client.wait_for_event(
        event_type="department.task_failed",
        source=dept_module.name,
        timeout=2.0
    )

    assert_event_matches(
        failure_event,
        source=dept_module.name,
        destination=harness_client.name,
        event_type="department.task_failed"
    )
    assert failure_event.payload["status"] == "failed"
    assert failure_event.payload["task_id"] == "sls-fail-1"
    assert "CRM API connection refused" in failure_event.payload["error"]


@pytest.mark.tier1
@pytest.mark.e2e
def test_sales_manager_allowed_tools_and_permissions():
    """Test SalesManager allowed tools, forbidden actions, and memory access permissions."""
    sls_mgr = SalesManager()

    tools = sls_mgr.allowed_tools()
    assert isinstance(tools, list)
    assert "crm_search" in tools
    assert "email_sender" in tools

    forbidden = sls_mgr.forbidden_actions()
    assert isinstance(forbidden, list)
    assert "grant_unauthorized_discount" in forbidden

    assert sls_mgr.memory_access_level() == "admin"
