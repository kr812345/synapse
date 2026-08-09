import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from departments.research.manager import ResearchManager
from departments.research.workers.github import GithubWorker
from departments.research.workers.hn import HNWorker
from departments.research.workers.product_hunt import ProductHuntWorker
from departments.research.workers.reddit import RedditWorker
from departments.research.workers.twitter import TwitterWorker


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


@pytest.mark.asyncio
async def test_research_manager_kernel_registration():
    """Verify ResearchManager inherits Module & BaseAgent and registers with Kernel."""
    kernel = Kernel()
    res_mgr = ResearchManager(id="res_mgr_test", name="Research Manager")

    assert isinstance(res_mgr, Module)
    assert res_mgr.name == "department.research"
    assert res_mgr.department == "Research"

    kernel.register_module(res_mgr)
    assert kernel.has_module("department.research")
    assert kernel.get_module("department.research") is res_mgr
    assert res_mgr.kernel is kernel


@pytest.mark.asyncio
async def test_research_manager_event_handling():
    """Verify department.execute_task event triggers research aggregation and emits department.task_completed."""
    kernel = Kernel()
    res_mgr = ResearchManager()
    receiver = MockReceiverModule("requester_module")

    kernel.register_module(res_mgr)
    kernel.register_module(receiver)

    task_event = Event(
        source=receiver.name,
        destination=res_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "res-101", "query": "LLM agent frameworks"}}
    )

    await kernel.send_event(task_event)
    await asyncio.sleep(0.05)

    assert len(receiver.received_events) == 1
    resp = receiver.received_events[0]
    assert resp.event_type == "department.task_completed"
    assert resp.payload["status"] == "success"
    assert resp.payload["task_id"] == "res-101"
    assert resp.payload["result"]["status"] == "delegated"
    assert "report" in resp.payload["result"]


@pytest.mark.asyncio
async def test_research_manager_multi_source_aggregation():
    """Verify ResearchManager delegates to multiple workers concurrently and aggregates findings into report artifact."""
    res_mgr = ResearchManager()

    result = await res_mgr.execute({
        "id": "res-102",
        "query": "vector databases",
        "sources": ["github", "hn", "reddit"]
    })

    assert result["status"] == "delegated"
    assert "report" in result
    report = result["report"]
    assert report["query"] == "vector databases"
    assert "github" in report["sources_queried"]
    assert "hn" in report["sources_queried"]
    assert "reddit" in report["sources_queried"]
    assert report["summary"]["total_results"] > 0


@pytest.mark.asyncio
async def test_research_workers_query_searches():
    """Test platform workers return non-empty structured data for valid queries."""
    gh = GithubWorker()
    hn = HNWorker()
    ph = ProductHuntWorker()
    rd = RedditWorker()
    tw = TwitterWorker()

    gh_res = await gh.execute("LLM framework")
    assert gh_res["status"] == "success"
    assert len(gh_res["data"]) > 0
    assert gh_res["metrics"]["total_repos"] > 0

    hn_res = await hn.execute("agent OS")
    assert hn_res["status"] == "success"
    assert len(hn_res["data"]) > 0
    assert hn_res["metrics"]["total_stories"] > 0

    ph_res = await ph.execute("AI developer tool")
    assert ph_res["status"] == "success"
    assert len(ph_res["data"]) > 0
    assert ph_res["metrics"]["total_launches"] > 0

    rd_res = await rd.execute("r/LocalLLaMA")
    assert rd_res["status"] == "success"
    assert len(rd_res["data"]) > 0
    assert rd_res["metrics"]["total_posts"] > 0

    tw_res = await tw.execute("#AIOS")
    assert tw_res["status"] == "success"
    assert len(tw_res["data"]) > 0
    assert tw_res["metrics"]["total_tweets"] > 0


@pytest.mark.asyncio
async def test_research_workers_obscure_blank_queries():
    """Test platform workers return data: [] for blank or obscure queries."""
    gh = GithubWorker()
    hn = HNWorker()

    gh_blank = await gh.execute("")
    assert gh_blank["data"] == []
    assert gh_blank["metrics"]["total_repos"] == 0

    hn_obscure = await hn.execute("obscure_library_xyz")
    assert hn_obscure["data"] == []
    assert hn_obscure["metrics"]["total_stories"] == 0


@pytest.mark.asyncio
async def test_research_manager_memory_store_integration():
    """Verify ResearchManager emits memory storage event to Kernel during research execution."""
    kernel = Kernel()
    receiver = MockReceiverModule("memory_engine")
    kernel.register_module(receiver)

    res_mgr = ResearchManager()
    res_mgr.set_kernel(kernel)

    await res_mgr.execute({"id": "res-mem", "query": "autonomous AI agents"})

    await asyncio.sleep(0.05)
    assert len(receiver.received_events) == 1
    mem_evt = receiver.received_events[0]
    assert mem_evt.event_type == "memory.store_knowledge"
    assert mem_evt.destination == "memory_engine"


@pytest.mark.asyncio
async def test_research_manager_handle_event_none_payload():
    """Verify ResearchManager.handle_event handles Event(payload=None) gracefully without crashing."""
    kernel = Kernel()
    res_mgr = ResearchManager()
    receiver = MockReceiverModule("requester_module")

    kernel.register_module(res_mgr)
    kernel.register_module(receiver)

    task_event = Event(
        source=receiver.name,
        destination=res_mgr.name,
        event_type="department.execute_task",
        payload={"task": "dummy"}
    )
    task_event.payload = None  # Force payload to None

    try:
        await kernel.send_event(task_event)
        await asyncio.sleep(0.05)
    except AttributeError as exc:
        pytest.fail(f"ResearchManager.handle_event raised unhandled AttributeError on payload=None: {exc}")

    assert len(receiver.received_events) == 1
    resp = receiver.received_events[0]
    assert resp.event_type in ("department.task_completed", "department.task_failed")


@pytest.mark.asyncio
async def test_research_manager_execute_null_description():
    """Verify ResearchManager.execute handles task dict with description=None without raising AttributeError."""
    res_mgr = ResearchManager()

    task_payload = {"id": "res-null-desc", "description": None}

    try:
        res = await res_mgr.execute(task_payload)
        assert res["status"] == "delegated"
        assert "report" in res
    except AttributeError as exc:
        pytest.fail(f"ResearchManager.execute raised AttributeError on task description=None: {exc}")


@pytest.mark.asyncio
async def test_research_manager_execute_null_sources():
    """Verify ResearchManager.execute handles task dict with sources=None without raising TypeError."""
    res_mgr = ResearchManager()

    task_payload = {"id": "res-null-src", "query": "AI systems", "sources": None}

    try:
        res = await res_mgr.execute(task_payload)
        assert res["status"] == "delegated"
        assert "report" in res
    except TypeError as exc:
        pytest.fail(f"ResearchManager.execute raised TypeError on sources=None: {exc}")


@pytest.mark.asyncio
async def test_research_manager_execute_none_task():
    """Verify ResearchManager.execute handles task=None gracefully."""
    res_mgr = ResearchManager()

    try:
        res = await res_mgr.execute(None)
        assert res["status"] == "delegated"
        assert "report" in res
    except Exception as exc:
        pytest.fail(f"ResearchManager.execute raised unexpected exception on task=None: {exc}")


@pytest.mark.asyncio
async def test_research_workers_none_input_robustness():
    """Verify all platform research workers handle None and null query tasks without crashing."""
    gh = GithubWorker()
    hn = HNWorker()
    ph = ProductHuntWorker()
    rd = RedditWorker()
    tw = TwitterWorker()

    for worker in [gh, hn, ph, rd, tw]:
        res_null = await worker.execute({"query": None, "description": None})
        assert res_null["status"] == "success"
        assert res_null["data"] == []

        res_none = await worker.execute(None)
        assert res_none["status"] == "success"


@pytest.mark.asyncio
async def test_research_can_handle_none_inputs():
    """Verify can_handle returns False safely for None, numeric, dict, and list inputs across research manager and workers."""
    res_mgr = ResearchManager()
    workers = list(res_mgr.workers.values())

    invalid_inputs = [None, 100, 3.14, [], {}, False]
    for agent in [res_mgr] + workers:
        for inp in invalid_inputs:
            assert agent.can_handle(inp) is False
