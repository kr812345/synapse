import unittest
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

class TestMemoryEngine(unittest.IsolatedAsyncioTestCase):
    async def test_memory_engine(self):
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
            payload={"knowledge": knowledge.dict()}
        ))
        
        await asyncio.sleep(0.1)
        
        self.assertEqual(len(client.received_events), 1)
        self.assertEqual(client.received_events[0].event_type, "memory.knowledge_stored")
        
        # Query knowledge
        await kernel.send_event(Event(
            source=client.name,
            destination=memory.name,
            event_type="memory.query_knowledge",
            payload={"query": "sky"}
        ))
        
        await asyncio.sleep(0.1)
        
        self.assertEqual(len(client.received_events), 2)
        query_resp = client.received_events[1]
        self.assertEqual(query_resp.event_type, "memory.query_results")
        self.assertEqual(len(query_resp.payload["results"]), 1)
        self.assertEqual(query_resp.payload["results"][0]["observation"], "The sky is blue")

if __name__ == "__main__":
    unittest.main()
