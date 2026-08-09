from typing import List, Any, Optional, Dict
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .assistant_worker import AssistantWorker
import logging

logger = logging.getLogger(__name__)

class PersonalManager(Module, BaseAgent):
    def __init__(self, id: str = "prs_mgr", name: str = "Personal Manager"):
        self._agent_name = name
        BaseAgent.__init__(self, id=id, name=name, department="personal", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers: List[BaseAgent] = [
            AssistantWorker(f"{id}_worker1", "Charlie Assistant")
        ]

    @property
    def name(self) -> str:
        return "department.personal"

    @name.setter
    def name(self, value: str) -> None:
        self._agent_name = value

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["contacts", "finances"]

    def forbidden_actions(self) -> List[str]:
        return ["authorize_payments"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return any(k in desc for k in ["personal", "life", "schedule", "calendar", "finance", "contacts", "agenda", "email"])

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            desc = task_dict.get("description", str(task))
            action = task_dict.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            action = getattr(task, "action", "")
            task_dict = {"description": desc}
        else:
            desc = str(task)
            action = ""
            task_dict = {"description": desc}

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        desc_lower = desc.lower()

        # Delegate schedule/calendar/email tasks to AssistantWorker
        if any(k in desc_lower for k in ["schedule", "calendar", "email", "agenda", "meeting"]):
            assistant = self.workers[0]
            worker_result = await assistant.execute(task)
            return {
                "status": "success",
                "manager": self.name,
                "delegated_to": assistant.name,
                "task": task,
                "result": worker_result
            }

        # Handle finance or contacts oversight tasks
        if any(k in desc_lower for k in ["finance", "budget", "contact", "expense"]):
            return {
                "status": "success",
                "manager": self.name,
                "oversight_type": "finance_and_contacts",
                "allowed_tools_used": self.allowed_tools(),
                "forbidden_actions_enforced": self.forbidden_actions(),
                "task": task,
                "result": {
                    "oversight_summary": f"Oversight completed for personal finance and contacts task: '{desc}'",
                    "payments_authorized": False,
                    "policy_compliance": "authorize_payments prevented"
                }
            }

        # Default general personal task execution
        return {
            "status": "success",
            "manager": self.name,
            "task": task,
            "result": {
                "summary": f"Personal manager processed task: '{desc}'",
                "managed": True
            }
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
