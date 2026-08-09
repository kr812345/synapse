import asyncio
import time
import logging
import traceback
from typing import Dict, Any, List
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from departments.research.manager import ResearchManager
from departments.research.workers.github import GithubWorker
from departments.research.workers.hn import HNWorker
from departments.research.workers.product_hunt import ProductHuntWorker
from departments.research.workers.reddit import RedditWorker
from departments.research.workers.twitter import TwitterWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress_harness_research")


class MockMemoryEngineModule(Module):
    def __init__(self):
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return "memory_engine"

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class MockRequesterModule(Module):
    def __init__(self, name: str = "test_requester"):
        self._name = name
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


async def run_worker_unit_and_edge_tests() -> Dict[str, Any]:
    logger.info("=== TEST TIER 1: Platform Worker Unit & Edge Cases ===")
    workers = {
        "github": GithubWorker(),
        "hn": HNWorker(),
        "product_hunt": ProductHuntWorker(),
        "reddit": RedditWorker(),
        "twitter": TwitterWorker(),
    }

    tier_results = {"passed": 0, "failed": 0, "details": []}

    # 1. Interface & properties check
    for name, worker in workers.items():
        assert worker.department == "Research"
        assert worker.role == "Worker"
        assert isinstance(worker.allowed_tools(), list)
        assert isinstance(worker.forbidden_actions(), list)
        assert worker.memory_access_level() == "isolated"
        assert worker.report()["status"] == "idle"
        assert worker.report()["source"] == name
    tier_results["passed"] += 1
    tier_results["details"].append("Interface compliance check: PASSED")

    # 2. Valid queries produce structured, non-empty data
    valid_queries = {
        "github": "python-asyncio",
        "hn": "Hacker News AI OS",
        "product_hunt": "LLM DevTool",
        "reddit": "LocalLLaMA benchmark",
        "twitter": "#AIOS trend",
    }
    for name, query in valid_queries.items():
        res = await workers[name].execute(query)
        assert workers[name].validate(res), f"Validation failed for worker {name}"
        assert res["status"] == "success"
        assert res["source"] == name
        assert len(res["data"]) > 0, f"Worker {name} returned empty data for valid query"
        assert res["metrics"], f"Worker {name} missing metrics"
    tier_results["passed"] += 1
    tier_results["details"].append("Valid queries non-empty structured data: PASSED")

    # 3. Blank and obscure queries return data: [] cleanly
    blank_and_obscure = ["", "obscure_library_xyz", "OBSCURE_LIBRARY_XYZ_999"]
    for name, worker in workers.items():
        for q in blank_and_obscure:
            res = await worker.execute(q)
            assert res["status"] == "success"
            assert res["data"] == [], f"Worker {name} did not return empty data list for query '{q}'"
    tier_results["passed"] += 1
    tier_results["details"].append("Blank & obscure queries empty data handling: PASSED")

    # 4. Whitespace query analysis
    ws_query = "   "
    ws_issues = []
    for name, worker in workers.items():
        res = await worker.execute(ws_query)
        if len(res.get("data", [])) > 0:
            ws_issues.append(f"Worker {name} returned mock data for pure whitespace query '{ws_query}'")
    if ws_issues:
        tier_results["details"].append(f"Whitespace query observation: {'; '.join(ws_issues)}")

    # 5. Malformed/Adversarial queries
    adversarial_inputs = [
        None,
        12345,
        {"some_weird_key": 999},
        ["list", "of", "items"],
        "A" * 5000,  # huge string
        "!@#$%^&*()_+-=[]{}|;:'\",.<>?/`~",  # special chars
    ]
    for name, worker in workers.items():
        for adv_input in adversarial_inputs:
            try:
                res = await worker.execute(adv_input)
                assert isinstance(res, dict)
                assert "status" in res
                assert isinstance(res.get("data"), list)
            except Exception as e:
                tier_results["failed"] += 1
                raise AssertionError(f"Worker {name} raised uncaught exception on adversarial input {type(adv_input)}: {e}")
    tier_results["passed"] += 1
    tier_results["details"].append("Adversarial/malformed inputs exception safety: PASSED")

    logger.info("-> Platform Worker Unit & Edge Cases: PASSED")
    return tier_results


async def run_manager_synthesis_and_routing_tests() -> Dict[str, Any]:
    logger.info("=== TEST TIER 2: ResearchManager Synthesis & Routing ===")
    res_mgr = ResearchManager()
    tier_results = {"passed": 0, "failed": 0, "details": []}

    # 1. Interface contracts
    assert res_mgr.name == "department.research"
    assert res_mgr.department == "Research"
    assert res_mgr.role == "Manager"
    assert "delegate" in res_mgr.allowed_tools()
    assert res_mgr.memory_access_level() == "department_wide"
    assert res_mgr.report()["status"] == "active"
    assert len(res_mgr.report()["workers_available"]) == 5
    tier_results["passed"] += 1
    tier_results["details"].append("ResearchManager interface & properties: PASSED")

    # 2. Topic keyword routing
    assert res_mgr.can_handle("Deep research into market trends") is True
    assert res_mgr.can_handle("Search for technical analysis") is True
    assert res_mgr.can_handle("Unrelated task description") is False
    assert res_mgr.can_handle("") is False
    tier_results["passed"] += 1
    tier_results["details"].append("can_handle keyword matching: PASSED")

    # 3. Specific source filtering
    res_gh = await res_mgr.execute({"topic": "distributed systems", "source": "github"})
    assert res_gh["status"] == "delegated"
    assert res_gh["report"]["sources_queried"] == ["github"]
    assert "github" in res_gh["results"]
    assert "hn" not in res_gh["results"]

    # Specific sources list filtering
    res_multi = await res_mgr.execute({"topic": "agent runtime", "sources": ["hn", "twitter"]})
    assert set(res_multi["report"]["sources_queried"]) == {"hn", "twitter"}

    # Keyword auto-worker selection
    res_kw_github = await res_mgr.execute({"query": "Check github repo for vector db"})
    assert "github" in res_kw_github["report"]["sources_queried"]

    # Fallback all workers when no specific match
    res_fallback = await res_mgr.execute({"query": "Quantum computing algorithms"})
    assert set(res_fallback["report"]["sources_queried"]) == {"github", "hn", "product_hunt", "reddit", "twitter"}
    tier_results["passed"] += 1
    tier_results["details"].append("Worker selection & source filtering: PASSED")

    # 4. Report artifact synthesis schema validation
    report = res_fallback["report"]
    assert report["title"].startswith("Research Synthesis:")
    assert report["query"] == "Quantum computing algorithms"
    assert "timestamp" in report
    assert isinstance(report["sources_queried"], list)
    summary = report["summary"]
    assert "total_results" in summary
    assert "platform_breakdown" in summary
    assert "overall_sentiment" in summary
    assert isinstance(summary["key_findings"], list)
    assert len(summary["key_findings"]) >= 2
    assert isinstance(report["platform_data"], dict)
    assert res_mgr.validate(res_fallback) is True
    tier_results["passed"] += 1
    tier_results["details"].append("Report artifact schema & synthesis: PASSED")

    logger.info("-> ResearchManager Synthesis & Routing: PASSED")
    return tier_results


async def run_kernel_and_eventbus_integration_tests() -> Dict[str, Any]:
    logger.info("=== TEST TIER 3: Kernel & EventBus Async Integration ===")
    tier_results = {"passed": 0, "failed": 0, "details": []}

    kernel = Kernel()
    res_mgr = ResearchManager()
    requester = MockRequesterModule("client_module")
    mem_engine = MockMemoryEngineModule()

    kernel.register_module(res_mgr)
    kernel.register_module(requester)
    kernel.register_module(mem_engine)

    # 1. Unicast event handling (department.execute_task)
    evt_task = Event(
        source=requester.name,
        destination=res_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "task-req-1", "query": "autonomous AI agents", "sources": ["hn", "reddit"]}}
    )
    await kernel.send_event(evt_task)
    await asyncio.sleep(0.1)

    assert len(requester.received_events) == 1
    resp = requester.received_events.pop(0)
    assert resp.event_type == "department.task_completed"
    assert resp.payload["status"] == "success"
    assert resp.payload["task_id"] == "task-req-1"
    tier_results["passed"] += 1
    tier_results["details"].append("EventBus department.execute_task handling: PASSED")

    # Verify memory event was broadcast to memory_engine module
    assert len(mem_engine.received_events) >= 1
    mem_evt = mem_engine.received_events.pop(0)
    assert mem_evt.event_type == "memory.store_knowledge"
    assert mem_evt.destination == "memory_engine"
    assert "autonomous AI agents" in mem_evt.payload["knowledge"]["observation"]
    tier_results["passed"] += 1
    tier_results["details"].append("Memory engine knowledge store event emission: PASSED")

    # 2. Event type 'research.task' -> 'research.result'
    evt_res = Event(
        source=requester.name,
        destination=res_mgr.name,
        event_type="research.task",
        payload={"task": {"id": "task-req-2", "query": "neural networks"}}
    )
    await kernel.send_event(evt_res)
    await asyncio.sleep(0.1)

    assert len(requester.received_events) == 1
    resp2 = requester.received_events.pop(0)
    assert resp2.event_type == "research.result"
    assert resp2.payload["task_id"] == "task-req-2"
    tier_results["passed"] += 1
    tier_results["details"].append("EventBus research.task handling: PASSED")

    logger.info("-> Kernel & EventBus Async Integration: PASSED")
    return tier_results


async def run_concurrency_and_stress_harness() -> Dict[str, Any]:
    logger.info("=== TEST TIER 4: Concurrency & Multi-Topic Stress Harness ===")
    tier_results = {"passed": 0, "failed": 0, "details": []}

    res_mgr = ResearchManager()

    topics = [
        "LLM alignment and safety",
        "obscure_library_xyz",
        "Autonomous Agent Frameworks",
        "",
        "Vector database indexing algorithms",
        "GitHub repository search",
        "Hacker News top stories",
        "Product Hunt launch strategies",
        "Reddit r/LocalLLaMA posts",
        "Twitter hashtag trends #AI",
    ]

    NUM_CONCURRENT_REQUESTS = 50
    start_time = time.time()

    async def execute_single_request(idx: int):
        topic = topics[idx % len(topics)]
        sources_option = None if idx % 2 == 0 else ["github", "hn"]
        task_payload = {
            "id": f"stress-req-{idx}",
            "topic": topic,
        }
        if sources_option:
            task_payload["sources"] = sources_option

        res = await res_mgr.execute(task_payload)
        return idx, res

    tasks = [execute_single_request(i) for i in range(NUM_CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    logger.info(f"Executed {NUM_CONCURRENT_REQUESTS} concurrent multi-topic research tasks in {elapsed:.3f} seconds.")

    # Verification of stress results
    success_count = 0
    for res in results:
        assert not isinstance(res, Exception), f"Request raised exception during stress run: {res}"
        idx, res_dict = res
        assert res_dict["status"] == "delegated"
        assert "report" in res_dict
        assert "summary" in res_dict["report"]
        success_count += 1

    assert success_count == NUM_CONCURRENT_REQUESTS
    tier_results["passed"] += 1
    tier_results["details"].append(f"Concurrent multi-topic stress test ({NUM_CONCURRENT_REQUESTS} tasks in {elapsed:.3f}s): PASSED")

    logger.info(f"-> Concurrency & Multi-Topic Stress Harness: PASSED ({success_count}/{NUM_CONCURRENT_REQUESTS} successful)")
    return tier_results


async def main():
    logger.info("Starting Research Department Stress Harness Verification...")
    results_summary = []
    try:
        t1 = await run_worker_unit_and_edge_tests()
        results_summary.append(("Tier 1: Worker Unit & Edge", t1))
        t2 = await run_manager_synthesis_and_routing_tests()
        results_summary.append(("Tier 2: Manager Synthesis & Routing", t2))
        t3 = await run_kernel_and_eventbus_integration_tests()
        results_summary.append(("Tier 3: Kernel & EventBus Integration", t3))
        t4 = await run_concurrency_and_stress_harness()
        results_summary.append(("Tier 4: Concurrency & Stress Harness", t4))

        logger.info("\n=======================================================")
        logger.info("         EMPIRICAL STRESS TEST RESULTS SUMMARY         ")
        logger.info("=======================================================")
        total_passed = 0
        total_failed = 0
        for name, t_res in results_summary:
            total_passed += t_res["passed"]
            total_failed += t_res["failed"]
            logger.info(f"{name}: {t_res['passed']} passed, {t_res['failed']} failed")
            for detail in t_res["details"]:
                logger.info(f"  - {detail}")
        logger.info("=======================================================")

        if total_failed == 0:
            logger.info("FINAL STRESS HARNESS VERDICT: APPROVE")
            return 0
        else:
            logger.info("FINAL STRESS HARNESS VERDICT: REJECT")
            return 1
    except Exception as e:
        logger.error(f"STRESS HARNESS EXECUTION FAILED: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
