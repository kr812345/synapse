import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from registry.sdk.base_agent import BaseAgent
from shared.interfaces import KernelInterface, Module
from shared.models import Event

from .workers.github import GithubWorker
from .workers.hn import HNWorker
from .workers.product_hunt import ProductHuntWorker
from .workers.reddit import RedditWorker
from .workers.twitter import TwitterWorker

logger = logging.getLogger(__name__)


class ResearchManager(BaseAgent, Module):
    """
    Research Department Manager responsible for parsing research requests,
    delegating tasks to platform workers (GitHub, HN, Product Hunt, Reddit, Twitter),
    aggregating results, and emitting research report artifacts.
    """

    def __init__(
        self,
        id: str = "research_manager",
        name: str = "Research Manager",
        department: str = "Research",
        role: str = "Manager",
        confidence_score: float = 1.0,
    ):
        BaseAgent.__init__(self, id, name, department, role, confidence_score)
        self._agent_name = name
        self.kernel: Optional[KernelInterface] = None
        self.workers: Dict[str, BaseAgent] = {
            "github": GithubWorker(),
            "hn": HNWorker(),
            "product_hunt": ProductHuntWorker(),
            "reddit": RedditWorker(),
            "twitter": TwitterWorker(),
        }

    @property
    def name(self) -> str:
        return "department.research"

    @name.setter
    def name(self, value: str) -> None:
        self._agent_name = value

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["delegate", "summarize", "aggregate_research", "generate_report"]

    def forbidden_actions(self) -> List[str]:
        return ["direct_execution", "delete_artifacts"]

    def memory_access_level(self) -> str:
        return "department_wide"

    def can_handle(self, task_description: str) -> bool:
        if not task_description or not isinstance(task_description, str):
            return False
        task_str = task_description.lower()
        return any(
            kw in task_str
            for kw in [
                "research",
                "market",
                "study",
                "trend",
                "search",
                "analysis",
            ]
        )

    async def handle_event(self, event: Event) -> None:
        """Process incoming events directed to ResearchManager module."""
        if event and (
            event.event_type
            in ("department.execute_task", "task.assigned", "research.task")
            or event.destination == self.name
        ):
            task_id = None
            try:
                payload = (event.payload if event and event.payload is not None else {})
                if isinstance(payload, dict):
                    task_data = payload.get("task", payload)
                else:
                    task_data = payload

                if isinstance(task_data, dict):
                    task_id = task_data.get("id") or task_data.get("task_id")
                elif hasattr(task_data, "id"):
                    task_id = getattr(task_data, "id", None)
                else:
                    task_id = None

                result = await self.execute(task_data)
                if self.kernel:
                    out_event_type = "research.result" if event.event_type == "research.task" else "department.task_completed"
                    response_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type=out_event_type,
                        payload={
                            "task_id": task_id,
                            "status": "success",
                            "result": result,
                        },
                    )
                    await self.kernel.send_event(response_event)
            except Exception as exc:
                logger.error(
                    f"Execution error in ResearchManager: {exc}", exc_info=True
                )
                if self.kernel:
                    failure_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_failed",
                        payload={
                            "task_id": task_id,
                            "status": "failed",
                            "error": str(exc),
                        },
                    )
                    await self.kernel.send_event(failure_event)

    async def execute(self, task: Any) -> Dict[str, Any]:
        """
        Parse task, delegate to appropriate platform workers, aggregate findings,
        and produce a research report artifact.
        """
        query = ""
        requested_source = None
        requested_sources = []

        if task is None:
            task = {}

        if isinstance(task, dict):
            raw_q = (
                task.get("query")
                or task.get("description")
                or task.get("topic")
            )
            query = raw_q if raw_q is not None else ""
            requested_source = task.get("source")
            requested_sources = task.get("sources") or []
        elif hasattr(task, "description"):
            raw_q = getattr(task, "description", "")
            query = raw_q if raw_q is not None else ""
        else:
            query = str(task) if task else ""

        if not isinstance(query, str):
            query = str(query) if query is not None else ""

        # Determine target workers
        target_workers: Dict[str, BaseAgent] = {}

        if requested_source:
            if requested_source in self.workers:
                target_workers[requested_source] = self.workers[requested_source]
        elif requested_sources:
            for s in requested_sources:
                if s in self.workers:
                    target_workers[s] = self.workers[s]

        if not target_workers and query:
            for key, worker in self.workers.items():
                if worker.can_handle(query):
                    target_workers[key] = worker

        if not target_workers and not requested_source:
            target_workers = dict(self.workers)

        # Execute searches concurrently
        worker_tasks = []
        worker_keys = list(target_workers.keys())
        for key in worker_keys:
            worker_tasks.append(
                target_workers[key].execute(
                    {"query": query} if query else task
                )
            )

        results_list = await asyncio.gather(*worker_tasks, return_exceptions=True)

        worker_results = {}
        total_items = 0
        platform_breakdown = {}

        for key, res in zip(worker_keys, results_list):
            if isinstance(res, Exception):
                logger.error(f"Worker {key} failed with exception: {res}")
                worker_results[key] = {"status": "error", "error": str(res)}
                platform_breakdown[key] = 0
            else:
                worker_results[key] = res
                items = res.get("data", []) if isinstance(res, dict) else []
                item_count = len(items) if isinstance(items, list) else 0
                total_items += item_count
                platform_breakdown[key] = item_count

        report = {
            "title": f"Research Synthesis: {query if query else 'General Technical Scope'}",
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources_queried": worker_keys,
            "summary": {
                "total_results": total_items,
                "platform_breakdown": platform_breakdown,
                "overall_sentiment": "positive" if total_items > 0 else "neutral",
                "key_findings": [
                    f"Queried {len(worker_keys)} platforms ({', '.join(worker_keys)})",
                    f"Aggregated {total_items} data points across target channels",
                ],
            },
            "platform_data": worker_results,
        }

        if self.kernel and hasattr(self.kernel, "send_event"):
            try:
                mem_event = Event(
                    source=f"research.manager.{self.id}",
                    destination="memory_engine",
                    event_type="memory.store_knowledge",
                    payload={
                        "knowledge": {
                            "observation": f"Completed research synthesis for query: {query[:50]}",
                            "source": f"research_manager_{self.id}",
                            "confidence": 1.0,
                            "category": "research_report",
                            "importance": 4,
                        }
                    },
                )
                await self.kernel.send_event(mem_event)
            except Exception as exc:
                logger.debug(f"Memory store event bypassed or failed: {exc}")

        return {
            "status": "delegated",
            "task": task,
            "query": query,
            "report": report,
            "results": worker_results,
            "summary": report["summary"],
        }

    def validate(self, result: Any) -> bool:
        if not isinstance(result, dict):
            return False
        return "status" in result and ("report" in result or "task" in result)

    def report(self) -> Dict[str, Any]:
        return {
            "status": "active",
            "department": self.department,
            "workers_available": list(self.workers.keys()),
        }

    def remember(self, knowledge: Any) -> None:
        pass
