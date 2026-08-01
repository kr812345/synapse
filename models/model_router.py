from shared.interfaces import Module
from shared.models import Event
import logging

logger = logging.getLogger(__name__)

class ModelRouter(Module):
    def __init__(self):
        self.kernel = None

    @property
    def name(self) -> str:
        return "model_router"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    def decide_model(self, task_description: str) -> str:
        # Dummy logic to determine complexity
        words = len(task_description.split())
        if words < 10:
            return "Gemini Flash"
        elif words < 50:
            return "OpenRouter"
        else:
            return "Antigravity CLI"

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "model.request_execution":
            task_id = event.payload.get("task_id")
            task_description = event.payload.get("task_description", "")
            agent = event.payload.get("agent", {})
            
            model = self.decide_model(task_description)
            logger.info(f"Model Router chose {model} for task {task_id}")
            
            # Simulate execution...
            result = {
                "status": "success",
                "executed_by": model,
                "agent": agent.get("identity"),
                "output": f"Simulated output from {model} for task {task_id}"
            }
            
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="model.execution_complete",
                    payload={"task_id": task_id, "result": result}
                )
                await self.kernel.send_event(resp)
