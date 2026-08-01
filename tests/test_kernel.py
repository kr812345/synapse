import pytest
import asyncio
from kernel.kernel import Kernel
from shared.models import Event
from departments.echo.echo_manager import EchoDepartment
from shared.interfaces import Module

class TestClient(Module):
    def __init__(self):
        self.kernel = None
        self.received_events = []
        
    @property
    def name(self) -> str:
        return "test_client"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_kernel_routing():
    kernel = Kernel()
    
    echo_dept = EchoDepartment()
    client = TestClient()
    
    kernel.register_module(echo_dept)
    kernel.register_module(client)
    
    # Send a ping from client to echo_dept
    ping_event = Event(
        source=client.name,
        destination=echo_dept.name,
        event_type="ping",
        payload={"message": "hello"}
    )
    
    await kernel.send_event(ping_event)
    
    # Allow event loop to process the async response
    await asyncio.sleep(0.1)
    
    assert len(client.received_events) == 1
    pong_event = client.received_events[0]
    
    assert pong_event.source == "echo_department"
    assert pong_event.destination == "test_client"
    assert pong_event.event_type == "pong"
    assert pong_event.payload["original_payload"]["message"] == "hello"

@pytest.mark.asyncio
async def test_kernel_broadcast():
    kernel = Kernel()
    
    class NamedClient(TestClient):
        def __init__(self, name):
            super().__init__()
            self._name = name
        @property
        def name(self) -> str:
            return self._name
            
    c1 = NamedClient("client1")
    c2 = NamedClient("client2")
    
    kernel.register_module(c1)
    kernel.register_module(c2)
    
    broadcast = Event(
        source="system",
        destination="*",
        event_type="update",
        payload={}
    )
    
    await kernel.send_event(broadcast)
    await asyncio.sleep(0.1)
    
    assert len(c1.received_events) == 1
    assert len(c2.received_events) == 1
