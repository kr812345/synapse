import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from kernel.kernel import Kernel
from departments.marketing.manager import MarketingManager
from departments.marketing.social_worker import SocialWorker
from departments.base import BaseDepartmentModule
from tools.tool_registry import ToolRegistry, PermissionDenied, ToolInterface
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event


class SocialToolMock(ToolInterface):
    name = "twitter"
    description = "Twitter API"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"action": "tweet_posted", "kwargs": kwargs}


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_target_channel_handling():
    """Verify marketing manager and social worker handle invalid/unsupported channels gracefully."""
    worker = SocialWorker("mkt_wrk_1", "Alice")

    invalid_channel_task = {
        "id": "mkt-t1",
        "channel": "unsupported_channel_xyz",
        "content": "Announcement post"
    }

    result = await worker.execute(invalid_channel_task)
    assert result["status"] == "success"
    assert result["task"]["channel"] == "unsupported_channel_xyz"
    assert worker.validate(result) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_campaign_budget_specs():
    """Verify marketing manager forbidden action policies and campaign specs handling."""
    manager = MarketingManager("mkt_mgr_1", "Marketing Lead")

    # Check forbidden actions policy
    assert "spend_over_budget" in manager.forbidden_actions()

    empty_specs_task = {
        "id": "mkt-t2",
        "description": "Run ad campaign",
        "budget": 0,
        "specs": {}
    }

    res = await manager.execute(empty_specs_task)
    assert res["status"] == "success"
    assert res["task"]["budget"] == 0
    assert manager.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_unauthorized_social_tool_execution():
    """Verify ToolRegistry blocks unauthorized marketing tools and forbidden budget actions."""
    registry = ToolRegistry()
    registry.register(SocialToolMock())

    manager = MarketingManager("mkt_mgr_2", "Marketing Lead")
    worker = SocialWorker("mkt_wrk_2", "Alice")

    # SocialWorker allowed_tools: ['twitter', 'linkedin']
    res = await registry.execute_tool(worker, "twitter", tweet="Hello world")
    assert res["action"] == "tweet_posted"

    # MarketingManager allowed_tools: ['analytics', 'campaign_manager'] -> twitter is not allowed for manager
    with pytest.raises(PermissionDenied, match="does not have permission to execute twitter"):
        await registry.execute_tool(manager, "twitter")


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_long_post_truncation_edge_cases():
    """Verify handling of excessively long post content (edge case boundary stress)."""
    worker = SocialWorker("mkt_wrk_3", "Alice")

    # 10,000 character post content
    long_content = "X" * 10_000
    task = {
        "id": "mkt-long-post",
        "content": long_content,
        "channel": "twitter"
    }

    res = await worker.execute(task)
    assert res["status"] == "success"
    assert len(res["task"]["content"]) == 10_000
    assert worker.validate(res) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_missing_content_templates(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify MarketingManager processing when requested template is missing."""
    manager = MarketingManager("mkt_mgr_3", "Marketing Manager")
    dept_module = BaseDepartmentModule(manager)
    fresh_kernel.register_module(dept_module)

    evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "mkt-tmpl-1",
                "description": "Generate marketing campaign using template_missing_xyz",
                "template": None
            }
        }
    )

    await fresh_kernel.send_event(evt)

    completed_evt = await harness_client.wait_for_event(event_type="department.task_completed")
    assert completed_evt.payload["status"] == "success"
    assert completed_evt.payload["task_id"] == "mkt-tmpl-1"
