from typing import List, Any, Optional
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .backend_worker import BackendWorker
from .qa_worker import QAWorker
from .devops_worker import DevOpsWorker
import logging

logger = logging.getLogger(__name__)


class EngineeringManager(Module, BaseAgent):
    """
    Engineering Department Manager.
    Inherits Module (for direct Kernel registration and event handling) and BaseAgent.
    Delegates tasks to BackendWorker, QAWorker, and DevOpsWorker, or handles architecture tasks directly.
    """

    def __init__(self, id: str = "eng_mgr_1", name: str = "Engineering Manager"):
        BaseAgent.__init__(self, id=id, name=name, department="engineering", role="manager")
        self._agent_name = name
        self.kernel: Optional[KernelInterface] = None

        self.backend_worker = BackendWorker(f"{id}_backend", "Backend Worker")
        self.qa_worker = QAWorker(f"{id}_qa", "QA Worker")
        self.devops_worker = DevOpsWorker(f"{id}_devops", "DevOps Worker")
        self.workers = [self.backend_worker, self.qa_worker, self.devops_worker]

    @property
    def name(self) -> str:
        return "department.engineering"

    @name.setter
    def name(self, value: str) -> None:
        self._agent_name = value

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel
        for worker in self.workers:
            if hasattr(worker, "set_kernel") and callable(worker.set_kernel):
                worker.set_kernel(kernel)

    async def handle_event(self, event: Event) -> None:
        """
        Processes incoming department task events:
        - Listens for 'department.execute_task', 'engineering.task', 'task.assigned' or direct routing.
        - Executes task via self.execute(task_data).
        - Emits corresponding response event back to Kernel.
        """
        if event and (event.event_type in ("department.execute_task", "engineering.task", "task.assigned") or event.destination == self.name):
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
                    if event.event_type == "engineering.task":
                        out_event_type = "engineering.result"
                    elif event.event_type == "task.assigned":
                        out_event_type = "task.complete"
                    else:
                        out_event_type = "department.task_completed"

                    response_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type=out_event_type,
                        payload={
                            "task_id": task_id,
                            "status": "success",
                            "result": result
                        }
                    )
                    await self.kernel.send_event(response_event)
            except Exception as exc:
                logger.error(f"Execution error in EngineeringManager for task {task_id}: {exc}", exc_info=True)
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

    def allowed_tools(self) -> List[str]:
        return ["jira", "github", "architecture_designer", "terminal"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_repo", "drop_production_db"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        if not task_description or not isinstance(task_description, str):
            return False
        desc_lower = task_description.lower()
        return any(k in desc_lower for k in [
            "engineering", "code", "backend", "api", "qa", "test", "devops", "deploy", "architecture", "infra"
        ])

    async def execute(self, task: Any) -> Any:
        if task is None:
            task_desc = ""
            task_id = None
        elif isinstance(task, dict):
            raw_desc = task.get("description")
            if raw_desc is None:
                raw_desc = task.get("task_description")
            task_desc = raw_desc if raw_desc is not None else str(task)
            task_id = task.get("id") or task.get("task_id")
        elif hasattr(task, "description"):
            raw_desc = getattr(task, "description", "")
            task_desc = raw_desc if raw_desc is not None else ""
            task_id = getattr(task, "id", None)
        else:
            task_desc = str(task)
            task_id = None

        if not isinstance(task_desc, str):
            task_desc = str(task_desc)

        desc_lower = task_desc.lower()

        if any(k in desc_lower for k in ["qa", "test", "coverage", "validation", "code review", "unit test"]):
            worker_result = await self.qa_worker.execute(task)
            handled_by = self.qa_worker.role
        elif any(k in desc_lower for k in ["devops", "deploy", "ci", "cd", "docker", "k8s", "kubernetes", "infra", "pipeline"]):
            worker_result = await self.devops_worker.execute(task)
            handled_by = self.devops_worker.role
        elif any(k in desc_lower for k in ["backend", "api", "code", "database", "service", "endpoint", "crud"]):
            worker_result = await self.backend_worker.execute(task)
            handled_by = self.backend_worker.role
        else:
            handled_by = self.role
            worker_result = {
                "action": "architecture_design",
                "architecture_spec": f"Architectural specification for: '{task_desc}'. High-availability service architecture.",
                "components": ["API Gateway", "Backend Microservice", "PostgreSQL Database", "Event Bus"]
            }

        if self.kernel and hasattr(self.kernel, "send_event"):
            try:
                mem_event = Event(
                    source=f"engineering.manager.{self.id}",
                    destination="memory_engine",
                    event_type="memory.store_knowledge",
                    payload={
                        "knowledge": {
                            "observation": f"Engineering task processed by {handled_by}: {task_desc[:50]}",
                            "source": f"engineering_manager_{self.id}",
                            "confidence": 1.0,
                            "category": "engineering_management",
                            "importance": 4
                        }
                    }
                )
                await self.kernel.send_event(mem_event)
            except Exception as exc:
                logger.debug(f"Memory store event bypassed or failed: {exc}")

        return {
            "status": "success",
            "department": "engineering",
            "handled_by": handled_by,
            "task": task,
            "result": worker_result
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing", "workers": len(self.workers), "department": self.department}

    def remember(self, knowledge: Any) -> None:
        pass
