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

    async def decide_model(self, task_description: str) -> str:
        # For this prototype we'll default to using litellm with a predefined model.
        # But this could be dynamic depending on complexity.
        return "gemini/gemini-1.5-pro"

    def _get_agent_tools(self, agent: dict) -> list:
        # In a real system we'd format the tools from tool_registry to OpenAI function calling format.
        # Here we just return None for simplicity.
        return None

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "model.request_execution":
            task_id = event.payload.get("task_id")
            task_description = event.payload.get("task_description", "")
            agent = event.payload.get("agent", {})
            
            model = await self.decide_model(task_description)
            logger.info(f"Model Router chose {model} for task {task_id}")
            
            import litellm
            try:
                # Real implementation
                response = await litellm.acompletion(
                    model=model,
                    messages=[{"role": "user", "content": f"You are agent {agent.get('identity')}. Task: {task_description}"}],
                    tools=self._get_agent_tools(agent)
                )
                output = response.choices[0].message.content
                status = "success"
            except Exception as e:
                output = f"Error executing task: {str(e)}"
                status = "error"
            
            result = {
                "status": status,
                "executed_by": model,
                "agent": agent.get("identity"),
                "output": output
            }
            
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="model.execution_complete",
                    payload={"task_id": task_id, "result": result}
                )
                await self.kernel.send_event(resp)
