import pytest
import asyncio
from typing import List, Any
from shared.models import Event
from shared.interfaces import Module
from kernel.kernel import Kernel
from departments.echo.echo_manager import EchoDepartment

class MockClient(Module):
    def __init__(self, name: str = "mock_client"):
        self._name = name
        self.kernel = None
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)

@pytest.mark.asyncio
async def test_echo_department_module_interface():
    """Verify EchoDepartment implements Module interface properties and set_kernel."""
    echo_dept = EchoDepartment()
    assert isinstance(echo_dept, Module)
    assert echo_dept.name == "echo_department"
    kernel = Kernel()
    echo_dept.set_kernel(kernel)
    assert echo_dept.kernel is kernel

@pytest.mark.asyncio
async def test_echo_department_ping_pong_roundtrip():
    """Verify EchoDepartment receives ping event and responds with pong event."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    client = MockClient("ping_client")

    kernel.register_module(echo_dept)
    kernel.register_module(client)

    ping_evt = Event(
        source=client.name,
        destination="echo_department",
        event_type="ping",
        payload={"message": "hello_echo_test"}
    )

    await kernel.send_event(ping_evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    pong_evt = client.received_events[0]
    assert pong_evt.source == "echo_department"
    assert pong_evt.destination == client.name
    assert pong_evt.event_type == "pong"
    assert pong_evt.payload["original_payload"]["message"] == "hello_echo_test"

@pytest.mark.asyncio
async def test_echo_department_payload_preservation():
    """Verify EchoDepartment preserves complex nested payloads without mutation or truncation."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    client = MockClient("payload_client")

    kernel.register_module(echo_dept)
    kernel.register_module(client)

    complex_payload = {
        "string": "test_str",
        "int": 42,
        "float": 3.14159,
        "bool": True,
        "none": None,
        "list": [1, "two", {"nested_in_list": True}],
        "dict": {"a": {"b": {"c": "deep_val"}}}
    }

    ping_evt = Event(
        source=client.name,
        destination="echo_department",
        event_type="ping",
        payload=complex_payload
    )

    await kernel.send_event(ping_evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 1
    pong_evt = client.received_events[0]
    assert pong_evt.payload["original_payload"] == complex_payload

@pytest.mark.asyncio
async def test_echo_department_source_routing():
    """Verify EchoDepartment dynamically sets pong event destination to incoming ping source."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    custom_client = MockClient("custom_sender_99")

    kernel.register_module(echo_dept)
    kernel.register_module(custom_sender_99 := custom_client)

    ping_evt = Event(
        source="custom_sender_99",
        destination="echo_department",
        event_type="ping",
        payload={"status": "routing_check"}
    )

    await kernel.send_event(ping_evt)
    await asyncio.sleep(0.05)

    assert len(custom_client.received_events) == 1
    pong_evt = custom_client.received_events[0]
    assert pong_evt.destination == "custom_sender_99"
    assert pong_evt.source == "echo_department"

@pytest.mark.asyncio
async def test_echo_department_ignores_non_ping_events():
    """Verify EchoDepartment ignores events with event_type != 'ping'."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    client = MockClient("ignore_client")

    kernel.register_module(echo_dept)
    kernel.register_module(client)

    info_evt = Event(
        source=client.name,
        destination="echo_department",
        event_type="info",
        payload={"msg": "should_be_ignored"}
    )

    await kernel.send_event(info_evt)
    await asyncio.sleep(0.05)

    assert len(client.received_events) == 0

@pytest.mark.asyncio
async def test_echo_department_multiple_consecutive_pings():
    """Verify EchoDepartment correctly responds to sequential ping events."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    client = MockClient("multi_ping_client")

    kernel.register_module(echo_dept)
    kernel.register_module(client)

    for i in range(5):
        ping_evt = Event(
            source=client.name,
            destination="echo_department",
            event_type="ping",
            payload={"seq": i}
        )
        await kernel.send_event(ping_evt)

    await asyncio.sleep(0.1)

    assert len(client.received_events) == 5
    for i, event in enumerate(client.received_events):
        assert event.event_type == "pong"
        assert event.payload["original_payload"]["seq"] == i

@pytest.mark.asyncio
async def test_echo_department_kernel_health_integration():
    """Verify EchoDepartment is tracked in Kernel health status and module listing."""
    kernel = Kernel()
    echo_dept = EchoDepartment()
    kernel.register_module(echo_dept)

    assert "echo_department" in kernel.list_modules()
    health = kernel.get_health_status()
    assert health["status"] == "healthy"
    assert "echo_department" in health["modules"]
