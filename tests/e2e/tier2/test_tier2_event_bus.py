import pytest
import asyncio
from typing import List
from pydantic import BaseModel, Field
from shared.interfaces import Module
from shared.models import Event
from events.event_bus import EventBus
from kernel.kernel import Kernel
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event


class StrictPayloadSchema(BaseModel):
    user_id: int
    action: str
    metadata: dict = Field(default_factory=dict)


class ExceptionSubscriber(Module):
    def __init__(self, name: str = "exception_sub"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        raise RuntimeError("Fatal exception inside subscriber event handler!")


class CircularEventSubscriber(Module):
    def __init__(self, name: str = "circular_sub", max_bounces: int = 3):
        self._name = name
        self.kernel = None
        self.bounces = 0
        self.max_bounces = max_bounces

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "test.cycle" and self.bounces < self.max_bounces:
            self.bounces += 1
            if self.kernel:
                bounce_evt = Event(
                    source=self.name,
                    destination=self.name,
                    event_type="test.cycle",
                    payload={"bounce_count": self.bounces}
                )
                await self.kernel.send_event(bounce_evt)


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_dead_letter_queue_routing_on_unknown_destination(fresh_kernel: Kernel):
    """Verify dead-letter queue routing when event destination is unknown and reprocessing capability."""
    bus = fresh_kernel.event_bus

    evt = create_test_event(
        source="client",
        destination="nonexistent_target",
        event_type="domain.unknown",
        payload={"key": "val"}
    )
    await fresh_kernel.send_event(evt)

    dead_letters = bus.get_dead_letters()
    assert len(dead_letters) == 1
    assert "nonexistent_target" in dead_letters[0]["reason"]
    assert dead_letters[0]["event"]["event_type"] == "domain.unknown"

    # Register missing target module and reprocess DLQ
    harness = OpaqueTestHarness("nonexistent_target")
    fresh_kernel.register_module(harness)

    reprocessed = await bus.reprocess_dead_letters()
    assert len(reprocessed) == 1
    assert len(bus.get_dead_letters()) == 0

    reprocessed_evt = await harness.wait_for_event(event_type="domain.unknown")
    assert_valid_event(reprocessed_evt)
    assert reprocessed_evt.payload["key"] == "val"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_malformed_event_schema_validation_errors(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify payload validation failures route malformed events to DLQ without delivery."""
    bus = fresh_kernel.event_bus
    bus.register_payload_schema("user.action", StrictPayloadSchema)

    # 1. Invalid payload: missing user_id and invalid type
    invalid_evt = Event(
        source="api",
        destination=harness_client.name,
        event_type="user.action",
        payload={"action": "click"}  # missing required user_id
    )

    await fresh_kernel.send_event(invalid_evt)
    await asyncio.sleep(0.05)

    assert len(harness_client.received_events) == 0
    dead_letters = bus.get_dead_letters()
    assert len(dead_letters) == 1
    assert "Payload validation failed" in dead_letters[0]["reason"]

    bus.clear_dead_letters()

    # 2. Valid payload passes schema validation and reaches harness
    valid_evt = Event(
        source="api",
        destination=harness_client.name,
        event_type="user.action",
        payload={"user_id": 42, "action": "click", "metadata": {"browser": "chrome"}}
    )

    await fresh_kernel.send_event(valid_evt)
    received = await harness_client.wait_for_event(event_type="user.action")
    assert received.payload["user_id"] == 42


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_exception_handling_in_subscriber_without_blocking_others(
    fresh_kernel: Kernel,
    harness_client: OpaqueTestHarness
):
    """Verify exception isolation ensuring subscriber failure doesn't block other listeners."""
    failing_sub = ExceptionSubscriber("failing_sub")
    fresh_kernel.register_module(failing_sub)

    broadcast_evt = Event(
        source="system",
        destination="*",
        event_type="system.alert",
        payload={"msg": "broadcast_alert"}
    )

    await fresh_kernel.send_event(broadcast_evt)

    # Working harness module receives the broadcast despite failing_sub raising exception
    received = await harness_client.wait_for_event(event_type="system.alert")
    assert received.payload["msg"] == "broadcast_alert"

    # DLQ records the subscriber exception
    dlq = fresh_kernel.event_bus.get_dead_letters()
    assert len(dlq) == 1
    assert "Handler exception in module 'failing_sub'" in dlq[0]["reason"]


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_circular_event_prevention(fresh_kernel: Kernel):
    """Verify bounded circular event cascading without infinite recursion or stack overflow."""
    circular_mod = CircularEventSubscriber("circular_sub", max_bounces=3)
    fresh_kernel.register_module(circular_mod)

    initial_evt = Event(
        source="trigger",
        destination="circular_sub",
        event_type="test.cycle",
        payload={"start": True}
    )

    await fresh_kernel.send_event(initial_evt)
    await asyncio.sleep(0.1)

    assert circular_mod.bounces == 3  # Hit maximum recursion safety boundary cleanly


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_high_volume_async_queue_overflow_handling(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify high-volume async queue execution and stats tracking under load."""
    bus = fresh_kernel.event_bus
    await bus.start()

    events_to_send = 300
    for i in range(events_to_send):
        evt = Event(
            source="producer",
            destination=harness_client.name,
            event_type="high_volume.sample",
            payload={"seq": i}
        )
        await bus.publish(evt)

    # Wait for queue worker to finish processing all published events
    await asyncio.sleep(0.2)

    stats = bus.get_stats()
    assert stats["events_processed"] >= events_to_send
    assert len(harness_client.received_events) == events_to_send

    await bus.shutdown()
