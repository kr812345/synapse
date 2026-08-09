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
logger = logging.getLogger("stress_harness_research_it2")


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


async def test_platform_worker_edge_cases() -> Dict[str, Any]:
    logger.info("=== TIER 1: Platform Worker Edge & Adversarial Cases ===")
    workers = {
        "github": GithubWorker(),
        "hn": HNWorker(),
        "product_hunt": ProductHuntWorker(),
        "reddit": RedditWorker(),
        "twitter": TwitterWorker(),
    }

    tier_results = {"passed": 0, "failed": 0, "details": []}

    # 1. Null / None / Blank / Obscure Inputs to workers
    edge_inputs = [
        None,
        "",
        "   ",
        "obscure_quantum_lib_9999",
        "NONEXISTENT_KEYWORD_404_XYZ",
        {"query": None},
        {"sources": None},
        {"topic": None, "query": None},
        12345,
        ["list", "of", "items"],
        "A" * 5000,
        "!@#$%^&*()_+-=[]{}|;:'\",.<>?/`~",
    ]

    for name, worker in workers.items():
        # can_handle robust check
        assert worker.can_handle(None) is False
        assert worker.can_handle(1234) is False
        assert worker.can_handle([]) is False

        for inp in edge_inputs:
            try:
                res = await worker.execute(inp)
                assert isinstance(res, dict), f"Worker {name} did not return dict for {type(inp)}"
                assert res["status"] in ["success", "error"]
                assert res["source"] == name
                assert isinstance(res.get("data"), list)
                assert "metrics" in res
                assert worker.validate(res) is True
            except Exception as e:
                tier_results["failed"] += 1
                raise AssertionError(f"Worker {name} crashed on input {inp}: {e}\n{traceback.format_exc()}")

    tier_results["passed"] += 1
    tier_results["details"].append("Platform Workers Null/Blank/Obscure/Adversarial Input robustness: PASSED")

    logger.info("-> Platform Worker Edge & Adversarial Cases: PASSED")
    return tier_results


async def test_research_manager_null_and_sources_none() -> Dict[str, Any]:
    logger.info("=== TIER 2: ResearchManager task={'sources': None} & Payload Edge Cases ===")
    res_mgr = ResearchManager()
    tier_results = {"passed": 0, "failed": 0, "details": []}

    # 1. task={"sources": None}
    res_sources_none = await res_mgr.execute({"query": "AI safety research", "sources": None})
    assert res_sources_none["status"] == "delegated"
    assert "report" in res_sources_none
    assert set(res_sources_none["report"]["sources_queried"]) == {"github", "hn", "product_hunt", "reddit", "twitter"}
    assert res_mgr.validate(res_sources_none) is True
    tier_results["passed"] += 1
    tier_results["details"].append("task={'sources': None} default fallback: PASSED")

    # 2. task={"sources": None, "query": None, "description": None}
    res_all_none = await res_mgr.execute({"sources": None, "query": None, "description": None, "topic": None})
    assert res_all_none["status"] == "delegated"
    assert "report" in res_all_none
    assert res_mgr.validate(res_all_none) is True
    tier_results["passed"] += 1
    tier_results["details"].append("task with all fields None: PASSED")

    # 3. task=None
    res_none_task = await res_mgr.execute(None)
    assert res_none_task["status"] == "delegated"
    assert "report" in res_none_task
    assert res_mgr.validate(res_none_task) is True
    tier_results["passed"] += 1
    tier_results["details"].append("task=None execution: PASSED")

    # 4. can_handle null safety
    assert res_mgr.can_handle(None) is False
    assert res_mgr.can_handle(1234) is False
    assert res_mgr.can_handle({}) is False
    tier_results["passed"] += 1
    tier_results["details"].append("ResearchManager can_handle null safety: PASSED")

    logger.info("-> ResearchManager task={'sources': None} & Payload Edge Cases: PASSED")
    return tier_results


async def test_event_bus_payload_none() -> Dict[str, Any]:
    logger.info("=== TIER 3: Kernel & EventBus Event(..., payload=None) Stress ===")
    tier_results = {"passed": 0, "failed": 0, "details": []}

    kernel = Kernel()
    res_mgr = ResearchManager()
    requester = MockRequesterModule("test_client")
    mem_engine = MockMemoryEngineModule()

    kernel.register_module(res_mgr)
    kernel.register_module(requester)
    kernel.register_module(mem_engine)

    # 1. Event with payload=None constructed via model_construct (testing handler null-safety when payload attribute is None)
    evt_none_payload = Event.model_construct(
        id="evt-none-payload",
        source=requester.name,
        destination=res_mgr.name,
        event_type="department.execute_task",
        payload=None
    )
    await kernel.send_event(evt_none_payload)
    await asyncio.sleep(0.1)

    assert len(requester.received_events) == 1
    resp1 = requester.received_events.pop(0)
    assert resp1.event_type == "department.task_completed"
    assert resp1.payload["status"] == "success"
    assert "result" in resp1.payload
    tier_results["passed"] += 1
    tier_results["details"].append("Event.model_construct(payload=None) for department.execute_task: PASSED")

    # 2. Event with payload=None for research.task
    evt_research_none = Event.model_construct(
        id="evt-research-none",
        source=requester.name,
        destination=res_mgr.name,
        event_type="research.task",
        payload=None
    )
    await kernel.send_event(evt_research_none)
    await asyncio.sleep(0.1)

    assert len(requester.received_events) == 1
    resp2 = requester.received_events.pop(0)
    assert resp2.event_type == "research.result"
    assert resp2.payload["status"] == "success"
    tier_results["passed"] += 1
    tier_results["details"].append("Event.model_construct(payload=None) for research.task: PASSED")

    # 3. Event with payload={"task": {"sources": None}}
    evt_sources_none = Event(
        source=requester.name,
        destination=res_mgr.name,
        event_type="department.execute_task",
        payload={"task": {"id": "req-sources-none", "sources": None, "topic": "vector search"}}
    )
    await kernel.send_event(evt_sources_none)
    await asyncio.sleep(0.1)

    assert len(requester.received_events) == 1
    resp3 = requester.received_events.pop(0)
    assert resp3.event_type == "department.task_completed"
    assert resp3.payload["task_id"] == "req-sources-none"
    assert resp3.payload["status"] == "success"
    tier_results["passed"] += 1
    tier_results["details"].append("Event with task={'sources': None}: PASSED")

    # 4. Direct call to handle_event with event=None or event.payload=None
    await res_mgr.handle_event(None) # should not crash
    tier_results["passed"] += 1
    tier_results["details"].append("Direct handle_event(None): PASSED")

    logger.info("-> Kernel & EventBus Event(..., payload=None) Stress: PASSED")
    return tier_results


async def test_high_concurrency_and_obscure_queries() -> Dict[str, Any]:
    logger.info("=== TIER 4: High Concurrency (100 Requests) & Synthesis Report Verification ===")
    tier_results = {"passed": 0, "failed": 0, "details": []}

    res_mgr = ResearchManager()

    scenarios = [
        {"topic": "Quantum Machine Learning", "sources": ["github", "hn"]},
        {"query": "obscure_lib_x_9999", "sources": None},
        {"description": "", "sources": None},
        {"topic": None, "sources": None},
        {"query": "   ", "sources": ["twitter", "reddit"]},
        None,
        {"sources": None, "query": "Synapse AI OS"},
        {"topic": "!@#$%^&*()_+-=[]{}|;:'\",.<>?/`~", "sources": None},
        {"sources": ["invalid_source_1", "invalid_source_2"]},
        {"topic": "Autonomous Agents", "sources": ["product_hunt"]},
    ]

    NUM_CONCURRENT_REQUESTS = 100
    start_time = time.time()

    async def execute_request(idx: int):
        task_input = scenarios[idx % len(scenarios)]
        res = await res_mgr.execute(task_input)
        return idx, res

    tasks = [execute_request(i) for i in range(NUM_CONCURRENT_REQUESTS)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    logger.info(f"Executed {NUM_CONCURRENT_REQUESTS} concurrent requests in {elapsed:.3f} seconds.")

    success_count = 0
    for idx, res in enumerate(results):
        assert not isinstance(res, Exception), f"Request {idx} failed with exception: {res}"
        idx_num, res_dict = res
        assert res_dict["status"] == "delegated"
        report = res_dict.get("report", {})
        assert report["title"].startswith("Research Synthesis:")
        assert "summary" in report
        summary = report["summary"]
        assert "total_results" in summary
        assert "platform_breakdown" in summary
        assert "key_findings" in summary
        assert isinstance(summary["key_findings"], list)
        assert len(summary["key_findings"]) >= 2
        assert res_mgr.validate(res_dict) is True
        success_count += 1

    assert success_count == NUM_CONCURRENT_REQUESTS
    tier_results["passed"] += 1
    tier_results["details"].append(f"100 Concurrent requests stress test in {elapsed:.3f}s: PASSED (100% success)")

    logger.info("-> High Concurrency & Synthesis Report Verification: PASSED")
    return tier_results


async def main():
    logger.info("Starting Research Stress Test Harness Iteration 2...")
    results_summary = []
    try:
        t1 = await test_platform_worker_edge_cases()
        results_summary.append(("Tier 1: Worker Edge & Adversarial", t1))
        t2 = await test_research_manager_null_and_sources_none()
        results_summary.append(("Tier 2: ResearchManager task={'sources': None}", t2))
        t3 = await test_event_bus_payload_none()
        results_summary.append(("Tier 3: EventBus payload=None", t3))
        t4 = await test_high_concurrency_and_obscure_queries()
        results_summary.append(("Tier 4: High Concurrency (100 Requests)", t4))

        logger.info("\n=======================================================")
        logger.info("     EMPIRICAL STRESS TEST IT2 RESULTS SUMMARY          ")
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
            logger.info("FINAL STRESS HARNESS IT2 VERDICT: APPROVE")
            return 0
        else:
            logger.info("FINAL STRESS HARNESS IT2 VERDICT: REJECT")
            return 1
    except Exception as e:
        logger.error(f"STRESS HARNESS IT2 EXECUTION FAILED: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
