"""
Synapse AI OS — Tier 5 Adversarial Stress & Hardening Test Suite.

Focuses on:
1. Boundary race conditions (concurrent queue pushes/pops, rapid registration/unregistration, high-concurrency bus loads, shutdown races, topic churn).
2. Malformed event cascades (circular event cascades, invalid schemas, missing payload keys, unroutable destination handling, DLQ corruption, exception storm isolation).
"""

import pytest
import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from shared.interfaces import Module
from shared.models import Event
from kernel.kernel import Kernel
from events.event_bus import EventBus
from models.model_router import ModelRouter
from departments.base import BaseDepartmentModule
from registry.sdk.base_agent import BaseAgent
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import create_test_event, assert_valid_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper Classes for Adversarial Testing
# ---------------------------------------------------------------------------

class StrictSchema(BaseModel):
    task_id: str
    command: str
    priority: int = Field(gt=0)


class CascadingRingSubscriber(Module):
    """Ring node that forwards events to next node in circular cascade."""
    def __init__(self, name: str, next_node_name: str, max_hops: int = 20):
        self._name = name
        self.next_node_name = next_node_name
        self.max_hops = max_hops
        self.kernel = None
        self.hops_processed = 0

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type == "cascade.ring":
            current_hop = event.payload.get("hop", 0)
            self.hops_processed += 1
            if current_hop < self.max_hops and self.kernel:
                next_evt = Event(
                    source=self.name,
                    destination=self.next_node_name,
                    event_type="cascade.ring",
                    payload={
                        "hop": current_hop + 1,
                        "history": event.payload.get("history", []) + [self.name]
                    }
                )
                await self.kernel.send_event(next_evt)


class MalformedDummyAgent(BaseAgent):
    def __init__(self, name: str = "malformed_agent", department: str = "test"):
        super().__init__(id="dummy_1", name=name, department=department, role="test_worker")

    def allowed_tools(self) -> List[str]:
        return ["*"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "read_write"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task_data: Any) -> Dict[str, Any]:
        if isinstance(task_data, dict) and task_data.get("trigger_raise"):
            raise ValueError("Intentional agent execution crash")
        return {"status": "ok", "processed": task_data}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {}

    def remember(self, knowledge: Any) -> None:
        pass


class ExceptionStormSubscriber(Module):
    def __init__(self, name: str, exception_cls=RuntimeError):
        self._name = name
        self.exception_cls = exception_cls
        self.events_seen = 0

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.events_seen += 1
        raise self.exception_cls(f"Exception storm burst in module '{self.name}'!")


# ---------------------------------------------------------------------------
# Tier 5 Adversarial Stress & Race Condition Tests
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_concurrent_push_pop_queue_saturation(fresh_kernel: Kernel):
    """
    Stress test high-concurrency event bus loads:
    Spawns 20 parallel producer coroutines pushing 50 events each (1000 total) into EventBus queue,
    while 5 subscriber harnesses receive and process events concurrently.
    """
    bus = fresh_kernel.event_bus
    await bus.start()

    subscribers = [OpaqueTestHarness(f"sub_worker_{i}") for i in range(5)]
    for sub in subscribers:
        fresh_kernel.register_module(sub)

    total_producers = 20
    events_per_producer = 50
    expected_total = total_producers * events_per_producer

    async def producer_task(producer_id: int):
        for seq in range(events_per_producer):
            dest = subscribers[seq % len(subscribers)].name
            evt = Event(
                source=f"producer_{producer_id}",
                destination=dest,
                event_type="stress.high_volume",
                payload={"producer": producer_id, "seq": seq}
            )
            await bus.publish(evt)

    producers = [asyncio.create_task(producer_task(p)) for p in range(total_producers)]
    await asyncio.gather(*producers)

    # Allow queue worker task to drain all items
    await asyncio.sleep(0.3)

    stats = bus.get_stats()
    assert stats["events_processed"] >= expected_total

    total_received = sum(len(sub.received_events) for sub in subscribers)
    assert total_received == expected_total

    await bus.shutdown()


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_rapid_module_registration_unregistration_race(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Race Test:
    Simultaneously sends continuous broadcast events while rapidly registering and unregistering
    modules to stress-test subscriber dict concurrency in EventBus.
    """
    bus = fresh_kernel.event_bus
    stop_signal = False

    async def broadcast_emitter():
        seq = 0
        while not stop_signal:
            evt = Event(
                source="emitter",
                destination="*",
                event_type="race.broadcast",
                payload={"seq": seq}
            )
            try:
                await fresh_kernel.send_event(evt)
            except Exception as exc:
                logger.warning(f"Caught exception during broadcast under dynamic reg: {exc}")
            seq += 1
            await asyncio.sleep(0.001)

    async def module_churner(churn_id: int):
        for i in range(30):
            mod_name = f"churn_mod_{churn_id}_{i}"
            mod = OpaqueTestHarness(mod_name)
            fresh_kernel.register_module(mod)
            await asyncio.sleep(0.002)
            fresh_kernel.unregister_module(mod_name)

    emitter_task = asyncio.create_task(broadcast_emitter())
    churners = [asyncio.create_task(module_churner(c)) for c in range(4)]

    await asyncio.gather(*churners)
    stop_signal = True
    await emitter_task

    # Verify kernel state integrity after rapid churn
    assert harness_client.name in fresh_kernel.modules
    assert fresh_kernel.has_module(harness_client.name)


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_concurrent_event_bus_shutdown_race(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Race Test:
    Stress-test calling EventBus.shutdown() while active producers are concurrently publishing events.
    """
    bus = fresh_kernel.event_bus
    await bus.start()

    publish_errors = 0

    async def continuous_publisher():
        nonlocal publish_errors
        for i in range(200):
            evt = Event(
                source="shutdown_race_prod",
                destination=harness_client.name,
                event_type="race.shutdown",
                payload={"index": i}
            )
            try:
                await bus.publish(evt)
            except Exception as exc:
                publish_errors += 1
            await asyncio.sleep(0.0005)

    pub_task = asyncio.create_task(continuous_publisher())
    await asyncio.sleep(0.01)

    # Initiate shutdown concurrently while pub_task is actively publishing
    await bus.shutdown()

    # Wait for pub_task to finish or handle shutdown
    await pub_task

    stats = bus.get_stats()
    assert stats["events_processed"] > 0
    assert not bus._running
    assert bus._worker_task is None


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_high_concurrency_topic_subscription_churn_race(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Topic Churn Test:
    Rapidly registers and unregisters topic subscribers across 10 concurrent coroutines
    while publishing matching wildcard topic events.
    """
    bus = fresh_kernel.event_bus
    patterns = ["telemetry.*", "*.alert", "logs.#", "system.cpu.*"]

    async def subscriber_churner(sub_id: int):
        harness = OpaqueTestHarness(f"churn_topic_sub_{sub_id}")
        fresh_kernel.register_module(harness)
        for i in range(20):
            pattern = patterns[i % len(patterns)]
            bus.subscribe_topic(harness, pattern)
            await asyncio.sleep(0.001)
            bus.unsubscribe_topic(harness, pattern)

    async def topic_publisher():
        for i in range(50):
            evt = Event(
                source="topic_pub",
                destination="*",
                event_type=f"telemetry.metric_{i}",
                payload={"seq": i}
            )
            await fresh_kernel.send_event(evt)
            await asyncio.sleep(0.001)

    churners = [subscriber_churner(i) for i in range(10)]
    pub_task = topic_publisher()

    await asyncio.gather(*churners, pub_task)
    stats = bus.get_stats()
    assert stats["events_processed"] >= 50


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_concurrent_kernel_module_lookup_and_health_checks(fresh_kernel: Kernel):
    """
    Adversarial Kernel Concurrency Test:
    Performs rapid concurrent list_modules(), get_module(), has_module(), and get_health_status()
    calls while modules are being registered and unregistered in parallel.
    """
    async def registration_worker():
        for i in range(25):
            h = OpaqueTestHarness(f"temp_mod_{i}")
            fresh_kernel.register_module(h)
            await asyncio.sleep(0.001)
            fresh_kernel.unregister_module(h.name)

    async def query_worker():
        for _ in range(50):
            _ = fresh_kernel.list_modules()
            _ = fresh_kernel.get_health_status()
            _ = fresh_kernel.has_module("temp_mod_5")
            _ = fresh_kernel.get_module("temp_mod_5")
            await asyncio.sleep(0.0005)

    reg_task = asyncio.create_task(registration_worker())
    query_tasks = [asyncio.create_task(query_worker()) for _ in range(5)]

    await asyncio.gather(reg_task, *query_tasks)
    health = fresh_kernel.get_health_status()
    assert health["status"] == "healthy"


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_circular_event_cascade_deep_recursion_safety(fresh_kernel: Kernel):
    """
    Adversarial Cascade Test:
    Constructs a multi-module ring (Node A -> Node B -> Node C -> Node D -> Node A)
    and verifies that cascading events terminate cleanly at the max hop limit without stack overflow or loop lockup.
    """
    node_names = ["ring_a", "ring_b", "ring_c", "ring_d"]
    nodes = []

    for i in range(len(node_names)):
        curr_name = node_names[i]
        next_name = node_names[(i + 1) % len(node_names)]
        node = CascadingRingSubscriber(curr_name, next_name, max_hops=12)
        nodes.append(node)
        fresh_kernel.register_module(node)

    start_event = Event(
        source="tester",
        destination="ring_a",
        event_type="cascade.ring",
        payload={"hop": 0, "history": []}
    )

    await fresh_kernel.send_event(start_event)
    await asyncio.sleep(0.1)

    total_hops = sum(node.hops_processed for node in nodes)
    # 0 to 12 inclusive = 13 total hops processed across the ring
    assert total_hops == 13
    assert nodes[0].hops_processed >= 3


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_invalid_event_schema_missing_payload_keys(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Schema Test:
    Tests malformed, missing, and non-dict payloads across EventBus, ModelRouter, and BaseDepartmentModule.
    """
    bus = fresh_kernel.event_bus
    bus.register_payload_schema("strict.event", StrictSchema)

    # 1. Missing required 'task_id' and 'priority' in payload schema
    malformed_schema_evt = Event(
        source=harness_client.name,
        destination=harness_client.name,
        event_type="strict.event",
        payload={"command": "do_work"}
    )
    await fresh_kernel.send_event(malformed_schema_evt)
    await asyncio.sleep(0.02)

    dlq = bus.get_dead_letters()
    assert len(dlq) == 1
    assert "Payload validation failed" in dlq[0]["reason"]

    # 2. BaseDepartmentModule handling scalar task payload inside dict
    dummy_agent = MalformedDummyAgent("dummy_dept", "test_dept")
    dept_module = BaseDepartmentModule(dummy_agent)
    fresh_kernel.register_module(dept_module)

    scalar_task_evt = Event(
        source=harness_client.name,
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": 12345}
    )
    await fresh_kernel.send_event(scalar_task_evt)

    # Harness receives completion response event from department module
    response = await harness_client.wait_for_event(event_type="department.task_completed")
    assert response.payload["status"] == "success"

    # 3. Direct Event model validation error when payload is non-dict
    with pytest.raises(ValidationError):
        Event(
            source="client",
            destination="dummy_dept",
            event_type="department.execute_task",
            payload=12345  # type: ignore
        )

    # 4. ModelRouter handling execution request with empty payload
    router = ModelRouter()
    fresh_kernel.register_module(router)

    empty_model_evt = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={}
    )
    await fresh_kernel.send_event(empty_model_evt)

    complete_evt = await harness_client.wait_for_event(event_type="model.execution_complete")
    assert complete_evt.payload["result"]["status"] == "success"


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_unroutable_destination_and_tricky_wildcard_patterns(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Routing Test:
    Tests unroutable destinations, empty destination strings, and edge case fnmatch wildcard topic subscriptions.
    """
    bus = fresh_kernel.event_bus

    # 1. Unroutable destination with empty string
    empty_dest_evt = Event(
        source="client",
        destination="",
        event_type="test.unroutable",
        payload={"data": "test"}
    )
    await fresh_kernel.send_event(empty_dest_evt)

    dlq = bus.get_dead_letters()
    assert len(dlq) == 1
    assert "No target subscriber found" in dlq[0]["reason"]

    # 2. Complex wildcard topic subscription (fnmatch pattern matching)
    bus.subscribe_topic(harness_client, "system.*.alert")
    bus.subscribe_topic(harness_client, "*.[0-9]")

    # Event matching system.*.alert pattern
    evt1 = Event(
        source="sensor",
        destination="unknown_dest",
        event_type="system.hardware.alert",
        payload={"alert_id": 101}
    )
    await fresh_kernel.send_event(evt1)

    rec1 = await harness_client.wait_for_event(event_type="system.hardware.alert")
    assert rec1.payload["alert_id"] == 101

    # Event matching numeric wildcard pattern *.[0-9]
    evt2 = Event(
        source="sensor",
        destination="unknown_dest",
        event_type="metric.tier.5",
        payload={"val": 99}
    )
    await fresh_kernel.send_event(evt2)

    rec2 = await harness_client.wait_for_event(event_type="metric.tier.5")
    assert rec2.payload["val"] == 99


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_dlq_overflow_and_corrupted_record_reprocessing(fresh_kernel: Kernel):
    """
    Adversarial DLQ Test:
    Populates DLQ with invalid messages and manually inserts corrupted non-dict / missing key records,
    then verifies reprocess_dead_letters() handles corruption without throwing unhandled exceptions.
    """
    bus = fresh_kernel.event_bus

    # Push 5 unroutable events to generate DLQ entries
    for i in range(5):
        evt = Event(
            source="client",
            destination=f"nonexistent_{i}",
            event_type="unroutable.type",
            payload={"id": i}
        )
        await fresh_kernel.send_event(evt)

    assert len(bus.get_dead_letters()) == 5

    # Inject corrupted / malformed entries into DLQ
    bus.dead_letter_queue.append({"event": None, "reason": "corrupted record 1"})
    bus.dead_letter_queue.append({"event": 12345, "reason": "corrupted record 2"})
    bus.dead_letter_queue.append({"invalid_key": "no_event_field"})

    assert len(bus.get_dead_letters()) == 8

    # Reprocess DLQ - should safely skip the 3 corrupted entries without crashing
    reprocessed = await bus.reprocess_dead_letters()

    # The 5 unroutable events are retried (and returned to DLQ if still unroutable)
    assert len(reprocessed) == 5
    assert len(bus.get_dead_letters()) == 5


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_department_cascade_exception_storm_isolation(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Exception Storm Test:
    Registers 5 failing subscriber modules throwing different exceptions (KeyError, ValueError, TypeError, ZeroDivisionError, MemoryError)
    alongside 1 healthy harness module.
    Verifies broadcast event is delivered to healthy harness while all 5 exceptions are captured in DLQ.
    """
    bus = fresh_kernel.event_bus

    exceptions = [KeyError, ValueError, TypeError, ZeroDivisionError, MemoryError]
    failing_mods = [ExceptionStormSubscriber(f"storm_fail_{i}", exc) for i, exc in enumerate(exceptions)]

    for mod in failing_mods:
        fresh_kernel.register_module(mod)

    broadcast_evt = Event(
        source="system_admin",
        destination="*",
        event_type="system.emergency_broadcast",
        payload={"alert": "storm_test"}
    )

    await fresh_kernel.send_event(broadcast_evt)

    # Verify healthy module received event
    rec = await harness_client.wait_for_event(event_type="system.emergency_broadcast")
    assert rec.payload["alert"] == "storm_test"

    # Verify DLQ received all 5 isolated subscriber exceptions
    dlq = bus.get_dead_letters()
    assert len(dlq) == 5
    for record in dlq:
        assert "Handler exception in module 'storm_fail_" in record["reason"]


@pytest.mark.e2e
@pytest.mark.tier5
@pytest.mark.asyncio
async def test_cascading_department_task_delegation_failure_recovery(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """
    Adversarial Task Cascade Failure Test:
    Simulates a multi-stage department cascade where a manager delegates to a crasher agent.
    Verifies department.task_failed is emitted and captured properly without system panic.
    """
    crasher = MalformedDummyAgent("crashing_subordinate")
    crasher_mod = BaseDepartmentModule(crasher)
    fresh_kernel.register_module(crasher_mod)

    # Dispatch task with trigger_raise=True to induce execution failure
    task_evt = Event(
        source=harness_client.name,
        destination=crasher_mod.name,
        event_type="department.execute_task",
        payload={
            "task": {
                "id": "cascade_task_fail_1",
                "description": "Failing cascade task",
                "trigger_raise": True
            }
        }
    )

    await fresh_kernel.send_event(task_evt)

    fail_resp = await harness_client.wait_for_event(event_type="department.task_failed")
    assert fail_resp.payload["task_id"] == "cascade_task_fail_1"
    assert fail_resp.payload["status"] == "failed"
    assert "Intentional agent execution crash" in fail_resp.payload["error"]
