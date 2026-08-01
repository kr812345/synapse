import pytest
import asyncio
from kernel.kernel import Kernel
from shared.models import Event, Task, AgentContract
from agents.registry import AgentRegistry
from scheduler.scheduler import Scheduler
from shared.interfaces import Module

class MockModelRouter(Module):
    def __init__(self):
        self.kernel = None
        
    @property
    def name(self) -> str:
        return "model_router"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        if event.event_type == "model.request_execution":
            task_id = event.payload["task_id"]
            # Simulate processing and complete
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="model.execution_complete",
                    payload={"task_id": task_id, "result": {"status": "success", "data": "output data"}}
                )
                await self.kernel.send_event(resp)

class MockRequester(Module):
    def __init__(self):
        self.kernel = None
        self.completed_tasks = []
        
    @property
    def name(self) -> str:
        return "mock_requester"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        if event.event_type == "task.complete":
            self.completed_tasks.append(event)

@pytest.mark.asyncio
async def test_scheduler_workflow():
    kernel = Kernel()
    registry = AgentRegistry()
    scheduler = Scheduler()
    model_router = MockModelRouter()
    requester = MockRequester()
    
    kernel.register_module(registry)
    kernel.register_module(scheduler)
    kernel.register_module(model_router)
    kernel.register_module(requester)
    
    # Pre-register an agent
    contract = AgentContract(
        identity="research_worker_1",
        department="research",
        goal="Find startup ideas",
        responsibilities=["search web"],
        forbidden_actions=[],
        allowed_tools=[],
        memory_access="none",
        output_schema={}
    )
    
    await kernel.send_event(Event(
        source="setup", destination="agent_registry", event_type="registry.register_agent",
        payload={"contract": contract.model_dump()}
    ))
    
    # Create a task
    task = Task(description="Find ideas", requester=requester.name)
    
    # Submit task to scheduler
    await kernel.send_event(Event(
        source=requester.name,
        destination=scheduler.name,
        event_type="task.create",
        payload={"task": task.model_dump()}
    ))
    
    # Allow async cascade: Scheduler -> Registry -> Scheduler -> ModelRouter -> Scheduler -> Requester
    await asyncio.sleep(0.5)
    
    # Verify task went through full lifecycle
    assert task.id in scheduler.tasks
    assert scheduler.tasks[task.id].status == "completed"
    
    assert len(requester.completed_tasks) == 1
    assert requester.completed_tasks[0].payload["result"]["data"] == "output data"
