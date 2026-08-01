import pytest
import asyncio
from kernel.kernel import Kernel
from shared.models import Event, Knowledge
from memory.memory_engine import MemoryEngine
from shared.interfaces import Module
from datetime import datetime, timedelta

class MockClient(Module):
    def __init__(self):
        self.kernel = None
        self.received_events = []
        
    @property
    def name(self) -> str:
        return "mock_client"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_memory_engine():
    kernel = Kernel()
    memory = MemoryEngine()
    client = MockClient()
    
    kernel.register_module(memory)
    kernel.register_module(client)
    
    # Store knowledge
    knowledge = Knowledge(
        observation="The sky is blue",
        source="vision",
        confidence=0.99,
        category="fact",
        importance=5
    )
    
    await kernel.send_event(Event(
        source=client.name,
        destination=memory.name,
        event_type="memory.store_knowledge",
        payload={"knowledge": knowledge.model_dump()}
    ))
    
    await asyncio.sleep(0.1)
    
    assert len(client.received_events) == 1
    assert client.received_events[0].event_type == "memory.knowledge_stored"
    
    # Query knowledge
    await kernel.send_event(Event(
        source=client.name,
        destination=memory.name,
        event_type="memory.query_knowledge",
        payload={"query": "sky"}
    ))
    
    await asyncio.sleep(0.1)
    
    assert len(client.received_events) == 2
    query_resp = client.received_events[1]
    assert query_resp.event_type == "memory.query_results"
    assert len(query_resp.payload["results"]) == 1
    assert query_resp.payload["results"][0]["observation"] == "The sky is blue"
