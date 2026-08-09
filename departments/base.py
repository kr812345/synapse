from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

class BaseDepartmentModule(Module):
    """
    Adapter class bridging a BaseAgent department manager/worker to the Kernel Module interface.
    Allows department agents to register with Kernel, listen for task execution events,
    execute tasks using the underlying BaseAgent, and return completion/failure events via Kernel.
    """
    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.kernel: Optional[KernelInterface] = None

    @property
    def name(self) -> str:
        dept = self.agent.department
        if dept.startswith("department."):
            return dept
        return f"department.{dept}"

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        """
        Processes incoming department task events:
        - Listens for 'department.execute_task' and 'task.assigned' event types (or direct routing).
        - Executes the underlying agent.execute(task_data).
        - Emits 'department.task_completed' or 'department.task_failed' response event back to Kernel.
        """
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            
            if isinstance(task_data, dict):
                task_desc = task_data.get("description", "")
                task_id = task_data.get("id")
            elif hasattr(task_data, "description"):
                task_desc = getattr(task_data, "description", "")
                task_id = getattr(task_data, "id", None)
            else:
                task_desc = str(task_data)
                task_id = None

            # Verify if agent can handle the task description if method is provided
            if hasattr(self.agent, "can_handle") and callable(self.agent.can_handle):
                if not self.agent.can_handle(task_desc) and event.event_type not in ("department.execute_task",):
                    logger.debug(f"Agent {self.agent.name} cannot handle task description: {task_desc}")
                    return

            try:
                result = await self.agent.execute(task_data)
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
                logger.error(f"Execution error in agent {self.agent.name} for task {task_id}: {exc}", exc_info=True)
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
