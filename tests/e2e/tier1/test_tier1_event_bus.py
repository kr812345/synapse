import pytest
import asyncio
from events.event_bus import EventBus
from shared.interfaces import Module
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


class MockEventReceiver(Module):
    """Mock module for receiving and tracking events in EventBus tests."""
    def __init__(self, name: str = "mock_receiver"):
        self._name = name
        self.received = []

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.received.append(event)


class ExceptionModule(Module):
    """Mock module that raises an exception on event handling to test error isolation."""
    @property
    def name(self) -> str:
        return "exception_module"

    async def handle_event(self, event: Event) -> None:
        raise ValueError("Simulated handler crash")


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_event_bus_unicast_routing(fresh_kernel, harness_client):
    """Test direct unicast event routing to a targeted destination module."""
    unicast_event = create_test_event(
        source="sender_module",
        destination=harness_client.name,
        event_type="unicast.direct_msg",
        payload={"message": "hello unicast"}
    )

    await fresh_kernel.send_event(unicast_event)

    received = await harness_client.wait_for_event(
        event_type="unicast.direct_msg",
        source="sender_module",
        timeout=2.0
    )
    assert_event_matches(
        received,
        source="sender_module",
        destination=harness_client.name,
        event_type="unicast.direct_msg",
        payload_subset={"message": "hello unicast"}
    )


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_event_bus_broadcast_routing(fresh_kernel, harness_client):
    """Test pub/sub broadcast event routing to all registered modules using destination='*'."""
    extra_receiver = MockEventReceiver("extra_receiver")
    fresh_kernel.register_module(extra_receiver)

    broadcast_event = create_test_event(
        source="broadcast_source",
        destination="*",
        event_type="system.notice",
        payload={"notice": "global broadcast"}
    )

    await fresh_kernel.send_event(broadcast_event)

    # Harness client intercept via wait_for_event
    received_harness = await harness_client.wait_for_event(
        event_type="system.notice",
        source="broadcast_source",
        timeout=2.0
    )
    assert_event_matches(received_harness, source="broadcast_source", destination="*")

    # Wait briefly to confirm extra_receiver also got it
    await asyncio.sleep(0.05)
    assert len(extra_receiver.received) == 1
    assert extra_receiver.received[0].event_type == "system.notice"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_event_bus_wildcard_topics(fresh_kernel, harness_client):
    """Test wildcard topic subscription and unsubscription on EventBus."""
    bus = fresh_kernel.event_bus

    # Subscribe harness to wildcard topic pattern
    bus.subscribe_topic(harness_client, "order.*")

    # Topic event matching pattern
    event_matching = create_test_event(
        source="order_service",
        destination="other_mod",
        event_type="order.created",
        payload={"order_id": "ORD-123"}
    )
    await fresh_kernel.send_event(event_matching)

    received = await harness_client.wait_for_event(
        event_type="order.created",
        source="order_service",
        timeout=2.0
    )
    assert received.payload["order_id"] == "ORD-123"

    # Unsubscribe from wildcard topic
    bus.unsubscribe_topic(harness_client, "order.*")
    harness_client.clear()

    event_ignored = create_test_event(
        source="order_service",
        destination="other_mod",
        event_type="order.cancelled",
        payload={"order_id": "ORD-123"}
    )
    await fresh_kernel.send_event(event_ignored)

    await asyncio.sleep(0.05)
    assert len(harness_client.received_events) == 0


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_event_bus_async_queue_handling():
    """Test EventBus decoupled asynchronous queue handling with start, publish, and shutdown."""
    bus = EventBus()
    receiver = MockEventReceiver("queue_receiver")
    bus.register_subscriber(receiver)

    await bus.start()

    e1 = create_test_event(source="src", destination="queue_receiver", event_type="queue.item1", payload={"val": 1})
    e2 = create_test_event(source="src", destination="queue_receiver", event_type="queue.item2", payload={"val": 2})

    await bus.publish(e1)
    await bus.publish(e2)

    await asyncio.sleep(0.1)

    assert len(receiver.received) == 2
    assert receiver.received[0].event_type == "queue.item1"
    assert receiver.received[1].event_type == "queue.item2"

    await bus.shutdown()


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_event_bus_error_isolation(fresh_kernel, harness_client):
    """Test error isolation: a failing module handler does not crash the bus or block other subscribers."""
    failing = ExceptionModule()
    fresh_kernel.register_module(failing)

    broadcast_event = create_test_event(
        source="sender",
        destination="*",
        event_type="test.resilience",
        payload={"test": True}
    )

    await fresh_kernel.send_event(broadcast_event)

    # Harness should still receive the broadcast successfully
    received = await harness_client.wait_for_event(
        event_type="test.resilience",
        source="sender",
        timeout=2.0
    )
    assert received.event_type == "test.resilience"

    # Dead-letter queue should record the handler error
    dlq = fresh_kernel.event_bus.get_dead_letters()
    assert len(dlq) == 1
    assert "Simulated handler crash" in dlq[0]["reason"]
    assert dlq[0]["event"]["event_type"] == "test.resilience"
