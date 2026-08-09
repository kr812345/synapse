import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from registry.sdk.base_agent import BaseAgent
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from departments.marketing.content_worker import ContentWorker

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
async def test_marketing_manager_initialization_and_inheritance():
    """Verify MarketingManager inherits both Module and BaseAgent and initializes properly."""
    mkt_mgr = MarketingManager(id="mkt_test_1", name="Marketing Manager Test")
    assert isinstance(mkt_mgr, Module)
    assert isinstance(mkt_mgr, BaseAgent)
    assert mkt_mgr.name == "department.marketing"
    assert mkt_mgr.department == "marketing"
    assert mkt_mgr.role == "manager"
    assert "analytics" in mkt_mgr.allowed_tools()
    assert "spend_over_budget" in mkt_mgr.forbidden_actions()
    assert mkt_mgr.memory_access_level() == "admin"
    assert len(mkt_mgr.workers) == 2

@pytest.mark.asyncio
async def test_marketing_manager_can_handle():
    """Verify MarketingManager capability matching for marketing tasks."""
    mkt_mgr = MarketingManager()
    assert mkt_mgr.can_handle("Launch social marketing campaign") is True
    assert mkt_mgr.can_handle("Write blog content article") is True
    assert mkt_mgr.can_handle("Fix Kubernetes cluster memory leak") is False

@pytest.mark.asyncio
async def test_marketing_manager_execution_real_payload():
    """Verify MarketingManager executes tasks returning structured payloads without mock strings."""
    mkt_mgr = MarketingManager()
    task = {
        "id": "mkt-101",
        "description": "Launch Q3 marketing campaign for AI OS",
        "budget": 5000,
        "specs": {"target_audience": "developers"},
        "template": "q3_launch_template"
    }
    res = await mkt_mgr.execute(task)
    assert res["status"] == "success"
    assert res["budget"] == 5000
    assert res["template"] == "q3_launch_template"
    assert res["specs"]["target_audience"] == "developers"
    assert len(res["worker_results"]) > 0
    assert "mocked" not in str(res).lower()
    assert mkt_mgr.validate(res) is True

@pytest.mark.asyncio
async def test_marketing_manager_negative_budget_raises_error():
    """Verify MarketingManager raises ValueError for invalid negative budget."""
    mkt_mgr = MarketingManager()
    task = {
        "id": "mkt-102",
        "description": "Invalid campaign",
        "budget": -1000
    }
    with pytest.raises(ValueError, match="Invalid negative campaign budget"):
        await mkt_mgr.execute(task)

@pytest.mark.asyncio
async def test_marketing_manager_kernel_module_registration_and_event_handling():
    """Verify MarketingManager direct Kernel Module registration and handle_event routing."""
    kernel = Kernel()
    mkt_mgr = MarketingManager(id="mkt_mgr_direct", name="Marketing Manager")
    client = MockClient("test_requester")
    kernel.register_module(mkt_mgr)
    kernel.register_module(client)

    assert "department.marketing" in kernel.list_modules()

    exec_event = Event(
        source=client.name,
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": {"id": "mkt-evt-1", "description": "Run marketing product launch campaign"}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    completed_event = client.received_events[0]
    assert completed_event.payload["status"] == "success"
    assert completed_event.payload["task_id"] == "mkt-evt-1"
    assert "mocked" not in str(completed_event.payload).lower()

@pytest.mark.asyncio
async def test_marketing_manager_event_failure_handling():
    """Verify MarketingManager emits department.task_failed when task execution fails."""
    kernel = Kernel()
    mkt_mgr = MarketingManager(id="mkt_mgr_fail", name="Marketing Manager")
    client = MockClient("test_requester")
    kernel.register_module(mkt_mgr)
    kernel.register_module(client)

    exec_event = Event(
        source=client.name,
        destination="department.marketing",
        event_type="department.execute_task",
        payload={"task": {"id": "mkt-fail-1", "description": "Bad campaign", "budget": -500}}
    )
    await kernel.send_event(exec_event)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    failed_event = client.received_events[0]
    assert failed_event.payload["status"] == "failed"
    assert failed_event.payload["task_id"] == "mkt-fail-1"
    assert "Invalid negative campaign budget" in failed_event.payload["error"]

@pytest.mark.asyncio
async def test_social_worker_post_generation():
    """Verify SocialWorker creates real social posts and handles long content up to 10k chars."""
    worker = SocialWorker(id="social_unit_1", name="Alice Social")
    assert worker.department == "marketing"
    assert worker.role == "social_media_manager"
    assert "twitter" in worker.allowed_tools()
    assert "post_without_approval" in worker.forbidden_actions()

    long_text = "Feature announcement: " + ("A" * 9500)
    task = {
        "id": "soc-100",
        "description": "Post feature release",
        "content": long_text,
        "channel": "linkedin"
    }
    result = await worker.execute(task)
    assert result["status"] == "success"
    assert result["channel"] == "linkedin"
    assert result["post_content"].startswith("[LINKEDIN]")
    assert len(result["post_content"]) > 9500
    assert "mocked" not in str(result).lower()

@pytest.mark.asyncio
async def test_social_worker_forbidden_action_prevention():
    """Verify SocialWorker prevents forbidden actions."""
    worker = SocialWorker()
    task = {
        "id": "soc-forbidden",
        "description": "Post without approval",
        "action": "post_without_approval"
    }
    with pytest.raises(PermissionError, match="post_without_approval"):
        await worker.execute(task)

@pytest.mark.asyncio
async def test_content_worker_blog_generation():
    """Verify ContentWorker capabilities, tool list, and article generation."""
    worker = ContentWorker(id="content_unit_1", name="Carol Content")
    assert worker.department == "marketing"
    assert worker.role == "content_writer"
    assert "cms_editor" in worker.allowed_tools()
    assert "seo_analyzer" in worker.allowed_tools()
    assert "publish_unapproved_copy" in worker.forbidden_actions()
    assert worker.can_handle("Write technical blog article on microservices") is True

    result = await worker.execute("Write technical blog article on microservices")
    assert result["status"] == "success"
    assert result["role"] == "content_writer"
    assert "content article generated" in result["result"]
    assert "mocked" not in str(result).lower()
