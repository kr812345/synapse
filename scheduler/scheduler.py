from shared.interfaces import Module
from shared.models import Event, Task
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class Scheduler(Module):
    def __init__(self):
        self.kernel = None
        # Maps task_id -> Task
        self.tasks: Dict[str, Task] = {}

    @property
    def name(self) -> str:
        return "scheduler"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "task.create":
            task = Task(**event.payload["task"])
            self.tasks[task.id] = task
            logger.info(f"Scheduler received task: {task.id} - {task.description}")
            
            # Request an agent from the registry
            if self.kernel:
                req_event = Event(
                    source=self.name,
                    destination="agent_registry",
                    event_type="registry.find_agent",
                    payload={"task_description": task.description, "task_id": task.id}
                )
                await self.kernel.send_event(req_event)
                
        elif event.event_type == "registry.agent_found":
            task_id = event.payload.get("task_id")
            contract_data = event.payload.get("contract")
            
            if task_id in self.tasks and contract_data:
                task = self.tasks[task_id]
                task.assigned_agent = contract_data["identity"]
                task.status = "agent_assigned"
                logger.info(f"Task {task.id} assigned to agent {task.assigned_agent}")
                
                # Now we would send this to the Model Router
                if self.kernel:
                    route_event = Event(
                        source=self.name,
                        destination="model_router",
                        event_type="model.request_execution",
                        payload={"task_id": task.id, "task_description": task.description, "agent": contract_data}
                    )
                    await self.kernel.send_event(route_event)
                    
        elif event.event_type == "model.execution_complete":
            task_id = event.payload.get("task_id")
            result = event.payload.get("result")
            
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.result = result
                task.status = "completed"
                logger.info(f"Task {task.id} completed successfully")
                
                if self.kernel:
                    # Send result back to original requester
                    resp_event = Event(
                        source=self.name,
                        destination=task.requester,
                        event_type="task.complete",
                        payload={"task_id": task.id, "result": result}
                    )
                    await self.kernel.send_event(resp_event)
