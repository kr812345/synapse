from typing import List, Any, Optional, Dict
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .social_worker import SocialWorker
from .content_worker import ContentWorker
import logging

logger = logging.getLogger(__name__)

class MarketingManager(Module, BaseAgent):
    def __init__(self, id: str = "mkt_mgr", name: str = "Marketing Manager"):
        self._agent_name = name
        BaseAgent.__init__(self, id=id, name=name, department="marketing", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers: List[BaseAgent] = [
            SocialWorker(f"{id}_worker1", "Alice Social"),
            ContentWorker(f"{id}_worker2", "Carol Content")
        ]

    @property
    def name(self) -> str:
        return "department.marketing"

    @name.setter
    def name(self, value: str) -> None:
        self._agent_name = value

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["analytics", "campaign_manager"]

    def forbidden_actions(self) -> List[str]:
        return ["spend_over_budget"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "marketing" in desc or "campaign" in desc or "social" in desc or "content" in desc

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            desc = task_dict.get("description", "")
            budget = task_dict.get("budget", None)
            specs = task_dict.get("specs", {})
            template = task_dict.get("template")
            action = task_dict.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            budget = getattr(task, "budget", None)
            specs = getattr(task, "specs", {})
            template = getattr(task, "template", None)
            action = getattr(task, "action", "")
            task_dict = {"description": desc}
        else:
            desc = str(task)
            budget = None
            specs = {}
            template = None
            action = ""
            task_dict = {"description": desc}

        if budget is not None and budget < 0:
            raise ValueError("Invalid negative campaign budget")

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        worker_results = []
        for worker in self.workers:
            if worker.can_handle(desc):
                try:
                    res = await worker.execute(task)
                    worker_results.append(res)
                except Exception as e:
                    logger.warning(f"Worker {worker.name} execution warning: {e}")

        template_used = template if template else "default_marketing_template"

        return {
            "status": "success",
            "task": task,
            "budget": budget if budget is not None else 0,
            "specs": specs if isinstance(specs, dict) else {},
            "template": template_used,
            "worker_results": worker_results,
            "result": f"Marketing campaign executed successfully. Delegated tasks: {len(worker_results)}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing", "workers_active": len(self.workers)}

    def remember(self, knowledge: Any) -> None:
        pass

    async def handle_event(self, event: Event) -> None:
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            if isinstance(task_data, dict):
                task_id = task_data.get("id")
            elif hasattr(task_data, "id"):
                task_id = getattr(task_data, "id", None)
            else:
                task_id = None

            try:
                result = await self.execute(task_data)
                if self.kernel:
                    response_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_completed",
                        payload={
                            "task_id": task_id,
                            "status": "success",
                            "result": result
                        }
                    )
                    await self.kernel.send_event(response_event)
            except Exception as exc:
                logger.error(f"Execution error in {self.name} for task {task_id}: {exc}", exc_info=True)
                if self.kernel:
                    failure_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_failed",
                        payload={
                            "task_id": task_id,
                            "status": "failed",
                            "error": str(exc)
                        }
                    )
                    await self.kernel.send_event(failure_event)
