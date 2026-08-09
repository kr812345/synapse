import pytest
import asyncio
from typing import List, Any
from pydantic import BaseModel

from kernel.kernel import Kernel
from events.event_bus import EventBus
from shared.models import Event
from departments.echo.echo_manager import EchoDepartment
from shared.interfaces import Module
from departments.base import BaseDepartmentModule
from registry.sdk.base_agent import BaseAgent
from tools.tool_registry import ToolRegistry, ToolInterface

class MockKernelClient(Module):
    __test__ = False

    def __init__(self, name_override: str = "test_client"):
        self.kernel = None
        self.received_events = []
        self._name = name_override
        
    @property
    def name(self) -> str:
        return self._name
        
    def set_kernel(self, kernel):
        self.kernel = kernel
        
    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

class FailingClient(Module):
    __test__ = False

    @property
    def name(self) -> str:
        return "failing_client"

    async def handle_event(self, event: Event) -> None:
        raise RuntimeError("Simulated module failure")

class DummyAgentForDept(BaseAgent):
    def __init__(self):
        super().__init__(id="dept_1", name="TestManager", department="engineering", role="manager")

    def allowed_tools(self) -> List[str]:
        return ["test_tool"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "full"

    def can_handle(self, task_description: str) -> bool:
        return "build" in task_description or "test" in task_description or "run" in task_description

    async def execute(self, task: Any) -> Any:
        return {"status": "completed", "output": "engineering execution success"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {}

    def remember(self, knowledge: Any) -> None:
        pass

class DummyToolImpl(ToolInterface):
    name = "test_tool"
    description = "A test tool"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return {"executed": True, "kwargs": kwargs}

class MockPayloadSchema(BaseModel):
    required_field: str

@pytest.mark.asyncio
async def test_kernel_routing():
    kernel = Kernel()
    
    echo_dept = EchoDepartment()
    client = MockKernelClient()
    
    kernel.register_module(echo_dept)
    kernel.register_module(client)
    
    ping_event = Event(
        source=client.name,
        destination=echo_dept.name,
        event_type="ping",
        payload={"message": "hello"}
    )
    
    await kernel.send_event(ping_event)
    await asyncio.sleep(0.05)
    
    assert len(client.received_events) == 1
    pong_event = client.received_events[0]
    
    assert pong_event.source == "echo_department"
    assert pong_event.destination == "test_client"
    assert pong_event.event_type == "pong"
    assert pong_event.payload["original_payload"]["message"] == "hello"

@pytest.mark.asyncio
async def test_kernel_broadcast():
    kernel = Kernel()
    
    c1 = MockKernelClient("client1")
    c2 = MockKernelClient("client2")
    
    kernel.register_module(c1)
    kernel.register_module(c2)
    
    broadcast = Event(
        source="system",
        destination="*",
        event_type="update",
        payload={}
    )
    
    await kernel.send_event(broadcast)
    await asyncio.sleep(0.05)
    
    assert len(c1.received_events) == 1
    assert len(c2.received_events) == 1

@pytest.mark.asyncio
async def test_kernel_dynamic_registration_and_unregistration():
    kernel = Kernel()
    client = MockKernelClient("dynamic_mod")

    kernel.register_module(client)
    assert kernel.has_module("dynamic_mod")
    assert kernel.get_module("dynamic_mod") is client
    assert "dynamic_mod" in kernel.list_modules()
    assert client.kernel is kernel

    kernel.unregister_module("dynamic_mod")
    assert not kernel.has_module("dynamic_mod")
    assert kernel.get_module("dynamic_mod") is None
    assert "dynamic_mod" not in kernel.list_modules()

@pytest.mark.asyncio
async def test_kernel_interface_enforcement():
    kernel = Kernel()

    # Non-Module object
    class InvalidModule:
        name = "invalid"

    with pytest.raises(TypeError):
        kernel.register_module(InvalidModule())

    # Module with invalid empty name
    class EmptyNameModule(Module):
        @property
        def name(self) -> str:
            return ""

        async def handle_event(self, event: Event) -> None:
            pass

    with pytest.raises(ValueError):
        kernel.register_module(EmptyNameModule())

@pytest.mark.asyncio
async def test_kernel_shutdown_and_health():
    kernel = Kernel()
    client = MockKernelClient("monitor_client")
    kernel.register_module(client)

    health = kernel.get_health_status()
    assert health["status"] == "healthy"
    assert health["module_count"] == 1
    assert "monitor_client" in health["modules"]
    assert health["uptime_seconds"] >= 0.0

    await kernel.shutdown()
    assert len(client.received_events) == 1
    shutdown_evt = client.received_events[0]
    assert shutdown_evt.event_type == "system.shutdown"

@pytest.mark.asyncio
async def test_event_bus_topic_subscription():
    kernel = Kernel()
    bus = kernel.event_bus

    client = MockKernelClient("topic_client")
    kernel.register_module(client)
    bus.subscribe_topic(client, "system.*")

    # Send topic event
    evt = Event(source="admin", destination="other", event_type="system.alert", payload={"msg": "warning"})
    await kernel.send_event(evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    assert client.received_events[0].event_type == "system.alert"

    # Unsubscribe
    bus.unsubscribe_topic(client, "system.*")
    evt2 = Event(source="admin", destination="other", event_type="system.critical", payload={})
    await kernel.send_event(evt2)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1  # count remains 1

@pytest.mark.asyncio
async def test_event_bus_dead_letter_queue():
    kernel = Kernel()
    bus = kernel.event_bus

    unroutable_evt = Event(source="tester", destination="nonexistent_module", event_type="test.ping", payload={})
    await kernel.send_event(unroutable_evt)

    dead_letters = bus.get_dead_letters()
    assert len(dead_letters) == 1
    assert "nonexistent_module" in dead_letters[0]["reason"]

    # Register destination and reprocess
    client = MockKernelClient("nonexistent_module")
    kernel.register_module(client)

    reprocessed = await bus.reprocess_dead_letters()
    assert len(reprocessed) == 1
    assert len(bus.get_dead_letters()) == 0

    await asyncio.sleep(0.05)
    assert len(client.received_events) == 1

@pytest.mark.asyncio
async def test_event_bus_payload_validation():
    kernel = Kernel()
    bus = kernel.event_bus
    client = MockKernelClient("validated_mod")
    kernel.register_module(client)

    bus.register_payload_schema("user.create", MockPayloadSchema)

    # Invalid payload (missing required_field)
    invalid_evt = Event(source="api", destination="validated_mod", event_type="user.create", payload={})
    await kernel.send_event(invalid_evt)
    assert len(client.received_events) == 0
    assert len(bus.get_dead_letters()) == 1

    bus.clear_dead_letters()

    # Valid payload
    valid_evt = Event(source="api", destination="validated_mod", event_type="user.create", payload={"required_field": "John"})
    await kernel.send_event(valid_evt)
    await asyncio.sleep(0.05)
    assert len(client.received_events) == 1

@pytest.mark.asyncio
async def test_event_bus_error_isolation():
    kernel = Kernel()
    failing = FailingClient()
    working = MockKernelClient("working_mod")

    kernel.register_module(failing)
    kernel.register_module(working)

    broadcast = Event(source="system", destination="*", event_type="alert", payload={})
    await kernel.send_event(broadcast)
    await asyncio.sleep(0.05)

    # Working client still receives broadcast even though failing client raised an error
    assert len(working.received_events) == 1
    dlq = kernel.event_bus.get_dead_letters()
    assert len(dlq) == 1
    assert "Simulated module failure" in dlq[0]["reason"]

@pytest.mark.asyncio
async def test_event_bus_async_queue():
    bus = EventBus()
    client = MockKernelClient("queued_client")
    bus.register_subscriber(client)

    await bus.start()
    evt = Event(source="sensor", destination="queued_client", event_type="data", payload={"temp": 98.6})
    await bus.publish(evt)

    await asyncio.sleep(0.1)
    assert len(client.received_events) == 1
    await bus.shutdown()

@pytest.mark.asyncio
async def test_department_base_module():
    kernel = Kernel()
    agent = DummyAgentForDept()
    dept_module = BaseDepartmentModule(agent)

    kernel.register_module(dept_module)
    assert dept_module.name == "department.engineering"

    client = MockKernelClient("task_requester")
    kernel.register_module(client)

    exec_evt = Event(
        source="task_requester",
        destination="department.engineering",
        event_type="department.execute_task",
        payload={"task": {"id": "t-100", "description": "build core module"}}
    )

    await kernel.send_event(exec_evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    resp = client.received_events[0]
    assert resp.event_type == "department.task_completed"
    assert resp.payload["status"] == "success"
    assert resp.payload["task_id"] == "t-100"

@pytest.mark.asyncio
async def test_tool_registry_module():
    kernel = Kernel()
    registry = ToolRegistry()
    tool = DummyToolImpl()
    registry.register(tool)

    kernel.register_module(registry)
    assert registry.name == "tool_registry"

    client = MockKernelClient("tool_user")
    kernel.register_module(client)

    exec_evt = Event(
        source="tool_user",
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "test_tool",
            "agent": {"id": "agent_1", "allowed_tools": ["test_tool"]},
            "kwargs": {"param": 42}
        }
    )

    await kernel.send_event(exec_evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    resp = client.received_events[0]
    assert resp.event_type == "tool.execution_result"
    assert resp.payload["status"] == "success"
    assert resp.payload["result"]["executed"] is True


