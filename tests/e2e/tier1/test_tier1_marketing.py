import pytest
import asyncio
from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from departments.base import BaseDepartmentModule
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from tools.tool_registry import ToolRegistry, ToolInterface
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


class ContentWorker(BaseAgent):
    """Content Worker agent for testing marketing blog posts, press releases, and articles."""
    def __init__(self, id: str = "content_worker_1", name: str = "Carol Content"):
        super().__init__(id=id, name=name, department="marketing", role="content_writer")

    def allowed_tools(self) -> List[str]:
        return ["cms_editor", "seo_analyzer"]

    def forbidden_actions(self) -> List[str]:
        return ["publish_unapproved_copy"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        return "content" in task_description.lower() or "blog" in task_description.lower() or "article" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "role": self.role, "task": task, "result": "content article generated"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass


class MockAnalyticsTool(ToolInterface):
    name = "analytics"
    description = "Marketing analytics dashboard tool"
    parameters = {"metric": "str"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"status": "success", "metric": kwargs.get("metric", "conversion_rate"), "value": 0.15}


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_marketing_manager_campaign_management(fresh_kernel, harness_client):
    """Test MarketingManager campaign task execution via BaseDepartmentModule and Kernel event routing."""
    mkt_mgr = MarketingManager(id="mkt_mgr_1", name="Marketing Manager")
    dept_module = BaseDepartmentModule(mkt_mgr)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "mkt-t1", "description": "launch marketing Q3 campaign"}}
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
    assert completed_event.payload["task_id"] == "mkt-t1"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_social_worker_post_generation():
    """Test SocialWorker capabilities, topic handling, and social media post execution."""
    worker = SocialWorker(id="social_1", name="Alice Social")

    assert worker.department == "marketing"
    assert worker.role == "social_media_manager"
    assert "twitter" in worker.allowed_tools()
    assert worker.can_handle("draft social media campaign announcement") is True
    assert worker.can_handle("deploy k8s pod") is False

    result = await worker.execute({"task_id": "s-1", "description": "draft post for product release"})
    assert result["status"] == "success"
    assert "task" in result


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_content_worker_blog_generation():
    """Test ContentWorker capabilities, topic matching, and blog post content generation."""
    worker = ContentWorker(id="content_1", name="Carol Content")

    assert worker.department == "marketing"
    assert worker.role == "content_writer"
    assert "cms_editor" in worker.allowed_tools()
    assert worker.can_handle("write blog content article for new release") is True
    assert worker.can_handle("fix database deadlock") is False

    result = await worker.execute("Write introduction blog article")
    assert result["status"] == "success"
    assert result["role"] == "content_writer"
    assert "content article generated" in result["result"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_marketing_analytics_tool_execution(fresh_kernel, harness_client):
    """Test executing marketing analytics tools via ToolRegistry module."""
    registry = ToolRegistry()
    tool = MockAnalyticsTool()
    registry.register(tool)

    fresh_kernel.register_module(registry)

    mkt_mgr = MarketingManager(id="mkt_analytics_user", name="Marketing Manager")

    exec_event = create_test_event(
        source=harness_client.name,
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "analytics",
            "agent": {"id": mkt_mgr.id, "allowed_tools": mkt_mgr.allowed_tools()},
            "kwargs": {"metric": "click_through_rate"}
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
    assert result_event.payload["result"]["metric"] == "click_through_rate"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_marketing_department_broadcast_event(fresh_kernel, harness_client):
    """Test Marketing department handling pub/sub broadcast events."""
    mkt_mgr = MarketingManager(id="mkt_bcast", name="Marketing Manager")
    dept_module = BaseDepartmentModule(mkt_mgr)

    fresh_kernel.register_module(dept_module)

    broadcast = create_test_event(
        source=harness_client.name,
        destination="*",
        event_type="task.assigned",
        payload={"task": {"id": "mkt-b1", "description": "marketing campaign strategy"}}
    )

    await fresh_kernel.send_event(broadcast)

    completed_event = await harness_client.wait_for_event(
        event_type="department.task_completed",
        source=dept_module.name,
        timeout=2.0
    )

    assert completed_event.payload["task_id"] == "mkt-b1"
