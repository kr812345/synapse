import pytest
import asyncio
from kernel.kernel import Kernel
from shared.models import Event
from models.model_router import ModelRouter
from shared.interfaces import Module

class MockScheduler(Module):
    def __init__(self):
        self.kernel = None
        self.received_events = []
        
    @property
    def name(self) -> str:
        return "mock_scheduler"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_model_router():
    kernel = Kernel()
    router = ModelRouter()
    scheduler = MockScheduler()
    
    kernel.register_module(router)
    kernel.register_module(scheduler)
    
    # Simple task -> Gemini Flash
    await kernel.send_event(Event(
        source=scheduler.name,
        destination=router.name,
        event_type="model.request_execution",
        payload={"task_id": "task_1", "task_description": "Short task"}
    ))
    
    await asyncio.sleep(0.1)
    
    # Hard task -> Antigravity CLI
    long_desc = "This is a very long and complex task that requires deep reasoning " * 10
    await kernel.send_event(Event(
        source=scheduler.name,
        destination=router.name,
        event_type="model.request_execution",
        payload={"task_id": "task_2", "task_description": long_desc}
    ))
    
    await asyncio.sleep(0.1)
    
    assert len(scheduler.received_events) == 2
    
    resp1 = scheduler.received_events[0]
    assert resp1.payload["task_id"] == "task_1"
    assert resp1.payload["result"]["executed_by"] == "Gemini Flash"
    
    resp2 = scheduler.received_events[1]
    assert resp2.payload["task_id"] == "task_2"
    assert resp2.payload["result"]["executed_by"] == "Antigravity CLI"
