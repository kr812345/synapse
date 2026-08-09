import pytest
import asyncio
from departments.base import BaseDepartmentModule
from departments.research.manager import ResearchManager
from departments.research.workers.github import GithubWorker
from departments.research.workers.hn import HNWorker
from departments.research.workers.product_hunt import ProductHuntWorker
from departments.research.workers.reddit import RedditWorker
from departments.research.workers.twitter import TwitterWorker
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_research_manager_task_delegation(fresh_kernel, harness_client):
    """Test ResearchManager task delegation via BaseDepartmentModule and Kernel event routing."""
    res_mgr = ResearchManager(id="res_mgr_1", name="Research Manager")
    dept_module = BaseDepartmentModule(res_mgr)

    fresh_kernel.register_module(dept_module)

    exec_event = create_test_event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "res-t1", "description": "conduct market research report"}}
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
    assert completed_event.payload["task_id"] == "res-t1"
    assert completed_event.payload["result"]["status"] == "delegated"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_github_worker_data_search():
    """Test GithubWorker capabilities, topic matching, and repo data search execution."""
    worker = GithubWorker(id="gh_w1", name="GitHub Worker")

    assert worker.department == "Research"
    assert worker.role == "Worker"
    assert "github_api_search" in worker.allowed_tools()
    assert worker.can_handle("search github repository trending topics") is True
    assert worker.can_handle("post tweet") is False

    res = await worker.execute({"query": "AI OS repositories"})
    assert res["status"] == "success"
    assert res["source"] == "github"
    assert isinstance(res["data"], list)
    assert worker.validate(res) is True


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_hn_worker_story_search():
    """Test HNWorker capabilities, topic matching, and Hacker News story search execution."""
    worker = HNWorker(id="hn_w1", name="HN Worker")

    assert worker.department == "Research"
    assert "hn_api_search" in worker.allowed_tools()
    assert worker.can_handle("fetch hacker news top stories") is True
    assert worker.can_handle("hn discussions") is True
    assert worker.can_handle("delete database") is False

    res = await worker.execute({"query": "LLM agent frameworks"})
    assert res["status"] == "success"
    assert res["source"] == "hn"
    assert isinstance(res["data"], list)
    assert worker.validate(res) is True


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_product_hunt_reddit_workers():
    """Test ProductHuntWorker and RedditWorker search capabilities and task execution outputs."""
    ph_worker = ProductHuntWorker(id="ph_w1", name="PH Worker")
    rd_worker = RedditWorker(id="rd_w1", name="Reddit Worker")

    # Product Hunt worker assertions
    assert ph_worker.can_handle("search product hunt launches") is True
    ph_res = await ph_worker.execute({"query": "AI developer tools"})
    assert ph_res["status"] == "success"
    assert ph_res["source"] == "product_hunt"
    assert ph_worker.validate(ph_res) is True

    # Reddit worker assertions
    assert rd_worker.can_handle("search reddit subreddits for feedback") is True
    rd_res = await rd_worker.execute({"query": "r/LocalLLaMA posts"})
    assert rd_res["status"] == "success"
    assert rd_res["source"] == "reddit"
    assert rd_worker.validate(rd_res) is True


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_twitter_worker_social_research():
    """Test TwitterWorker capabilities, topic handling, and social sentiment research execution."""
    worker = TwitterWorker(id="tw_w1", name="Twitter Worker")

    assert worker.department == "Research"
    assert "twitter_api_search" in worker.allowed_tools()
    assert worker.can_handle("monitor twitter trends for AI OS") is True
    assert worker.can_handle("deploy server") is False

    res = await worker.execute({"query": "#AIOS"})
    assert res["status"] == "success"
    assert res["source"] == "twitter"
    assert isinstance(res["data"], list)
    assert worker.validate(res) is True
