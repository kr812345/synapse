import pytest
import asyncio
from kernel.kernel import Kernel
from shared.models import Event, AgentContract
from agents.registry import AgentRegistry
from shared.interfaces import Module

class MockDepartment(Module):
    def __init__(self):
        self.kernel = None
        self.received_events = []
        
    @property
    def name(self) -> str:
        return "mock_department"
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_agent_registry():
    kernel = Kernel()
    registry = AgentRegistry()
    mock_dept = MockDepartment()
    
    kernel.register_module(registry)
    kernel.register_module(mock_dept)
    
    # 1. Register an agent via event
    contract = AgentContract(
        identity="research_worker_1",
        department="research",
        goal="Find startup ideas",
        responsibilities=["search web", "read news"],
        forbidden_actions=["delete files"],
        allowed_tools=["browser"],
        memory_access="read-write",
        output_schema={"type": "object"}
    )
    
    register_event = Event(
        source=mock_dept.name,
        destination=registry.name,
        event_type="registry.register_agent",
        payload={"contract": contract.model_dump()}
    )
    
    await kernel.send_event(register_event)
    await asyncio.sleep(0.1)
    
    # Verify registration response
    assert len(mock_dept.received_events) >= 1
    resp = mock_dept.received_events[0]
    assert resp.event_type == "registry.agent_registered"
    assert resp.payload["identity"] == "research_worker_1"
    
    # 2. Find the agent via event
    find_event = Event(
        source=mock_dept.name,
        destination=registry.name,
        event_type="registry.find_agent",
        payload={"task_description": "I need some startup ideas"}
    )
    
    await kernel.send_event(find_event)
    await asyncio.sleep(0.1)
    
    # Verify find response
    resp = mock_dept.received_events[-1]
    assert resp.event_type == "registry.agent_found"
    assert resp.payload["contract"] is not None
    assert resp.payload["contract"]["identity"] == "research_worker_1"
