from shared.interfaces import Module
from shared.models import Event, AgentContract
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AgentRegistry(Module):
    def __init__(self):
        # Maps department -> List of AgentContracts
        self.registry: Dict[str, List[AgentContract]] = {}
        self.kernel = None

    @property
    def name(self) -> str:
        return "agent_registry"
        
    def set_kernel(self, kernel):
        self.kernel = kernel

    def register_agent(self, contract: AgentContract):
        if contract.department not in self.registry:
            self.registry[contract.department] = []
        self.registry[contract.department].append(contract)
        logger.info(f"Registered agent {contract.identity} in department {contract.department}")

    def find_agent_for_task(self, task_description: str) -> Optional[AgentContract]:
        # Simple placeholder logic: return the first agent available
        # In a real system, this would use embeddings or an LLM to match task to agent responsibilities.
        for dept, agents in self.registry.items():
            if agents:
                return agents[0]
        return None

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "registry.register_agent":
            contract = AgentContract(**event.payload["contract"])
            self.register_agent(contract)
            
            if self.kernel:
                response = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="registry.agent_registered",
                    payload={"identity": contract.identity, "status": "success"}
                )
                await self.kernel.send_event(response)
                
        elif event.event_type == "registry.find_agent":
            task_desc = event.payload.get("task_description", "")
            task_id = event.payload.get("task_id")
            agent = self.find_agent_for_task(task_desc)
            
            if self.kernel:
                response = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="registry.agent_found",
                    payload={
                        "contract": agent.model_dump() if agent else None,
                        "task_id": task_id
                    }
                )
                await self.kernel.send_event(response)
