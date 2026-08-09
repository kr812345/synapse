import pytest
import asyncio
from typing import List, Any
from shared.models import Event, Knowledge
from kernel.kernel import Kernel
from departments.research.manager import ResearchManager
from departments.research.workers.github import GithubWorker
from departments.research.workers.hn import HNWorker
from departments.base import BaseDepartmentModule
from registry.sdk.base_agent import BaseAgent
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_knowledge, create_test_knowledge, create_test_event


class TimeoutResearchWorker(BaseAgent):
    def __init__(self, id: str = "timeout_worker", name: str = "Timeout Research Worker"):
        super().__init__(id, name, "Research", "Worker")

    def allowed_tools(self) -> List[str]:
        return ["search_api"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "isolated"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        raise TimeoutError("Research worker connection timed out after 30s")

    def validate(self, result: Any) -> bool:
        return False

    def report(self) -> Any:
        return {"status": "error"}

    def remember(self, knowledge: Any) -> None:
        pass


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_worker_network_timeout_error_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify research worker timeout exception handling and failure event propagation."""
    worker = TimeoutResearchWorker()
    dept_module = BaseDepartmentModule(worker)
    fresh_kernel.register_module(dept_module)

    exec_evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "res-t1", "description": "Search web for docs"}}
    )

    await fresh_kernel.send_event(exec_evt)

    fail_evt = await harness_client.wait_for_event(event_type="department.task_failed")
    assert fail_evt.payload["status"] == "failed"
    assert fail_evt.payload["task_id"] == "res-t1"
    assert "timed out" in fail_evt.payload["error"]


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_search_results_aggregation():
    """Verify research workers return structured empty dataset without indexing errors."""
    github_worker = GithubWorker()
    hn_worker = HNWorker()

    res_gh = await github_worker.execute("search repo containing obscure_library_xyz")
    assert res_gh["status"] == "success"
    assert res_gh["source"] == "github"
    assert isinstance(res_gh["data"], list)
    assert len(res_gh["data"]) == 0
    assert github_worker.validate(res_gh) is True

    res_hn = await hn_worker.execute("search stories about obscure_library_xyz")
    assert res_hn["status"] == "success"
    assert res_hn["source"] == "hn"
    assert isinstance(res_hn["data"], list)
    assert hn_worker.validate(res_hn) is True


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_malformed_query_handling():
    """Verify research worker can_handle and execute methods against malformed query strings."""
    github_worker = GithubWorker()

    # Empty string query
    assert github_worker.can_handle("") is False
    res_empty = await github_worker.execute("")
    assert res_empty["status"] == "success"

    # Special character inputs
    special_query = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/`~"
    res_special = await github_worker.execute(special_query)
    assert res_special["status"] == "success"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_knowledge_category_storage():
    """Verify validation boundary checks for Knowledge schema (confidence bounds, empty fields)."""
    # 1. Valid knowledge instance
    valid_k = create_test_knowledge(
        observation="Valid research observation",
        category="security_advisory",
        confidence=0.95
    )
    assert_valid_knowledge(valid_k)

    # 2. Out of bounds confidence (> 1.0) raises validation assertion error
    with pytest.raises(AssertionError, match="confidence"):
        invalid_confidence_k = Knowledge(
            observation="Obs",
            source="src",
            category="test",
            confidence=1.5,
            importance=5
        )
        assert_valid_knowledge(invalid_confidence_k)

    # 3. Empty observation string raises validation assertion error
    with pytest.raises(AssertionError, match="observation"):
        invalid_obs_k = Knowledge(
            observation="",
            source="src",
            category="test",
            confidence=0.8,
            importance=5
        )
        assert_valid_knowledge(invalid_obs_k)


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_missing_research_sources():
    """Verify ResearchManager task delegation when unsupported source is requested."""
    manager = ResearchManager()

    unsupported_source_task = {
        "id": "res-task-99",
        "query": "Find research papers",
        "source": "nonexistent_research_engine_99"
    }

    res = await manager.execute(unsupported_source_task)
    assert res["status"] == "delegated"
    assert res["task"]["source"] == "nonexistent_research_engine_99"
    assert manager.validate(res) is True
