from shared.interfaces import Module
from shared.models import Event, Knowledge
from typing import Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryEngine(Module):
    def __init__(self):
        self.kernel = None
        # Simple in-memory storage for MVP
        self.knowledge_base: Dict[str, Knowledge] = {}

    @property
    def name(self) -> str:
        return "memory_engine"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "memory.store_knowledge":
            knowledge_data = event.payload.get("knowledge", {})
            try:
                knowledge = Knowledge(**knowledge_data)
                self.knowledge_base[knowledge.id] = knowledge
                logger.info(f"Stored knowledge: {knowledge.id} - {knowledge.observation[:30]}...")
                
                if self.kernel:
                    resp = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="memory.knowledge_stored",
                        payload={"knowledge_id": knowledge.id, "status": "success"}
                    )
                    await self.kernel.send_event(resp)
            except Exception as e:
                logger.error(f"Failed to store knowledge: {e}")
                
        elif event.event_type == "memory.query_knowledge":
            query = event.payload.get("query", "")
            # Simple substring search for MVP instead of real embeddings
            results = []
            for k in self.knowledge_base.values():
                # Check expiration
                if k.expiration and k.expiration < datetime.utcnow():
                    continue
                if query.lower() in k.observation.lower() or query.lower() in k.category.lower():
                    results.append(k.model_dump())
                    
            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="memory.query_results",
                    payload={"query": query, "results": results}
                )
                await self.kernel.send_event(resp)
