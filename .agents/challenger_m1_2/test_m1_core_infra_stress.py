import pytest
import asyncio
import random
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from kernel.kernel import Kernel
from events.event_bus import EventBus
from shared.models import Event
from shared.interfaces import Module, KernelInterface
from departments.base import BaseDepartmentModule
from registry.sdk.base_agent import BaseAgent
from tools.tool_registry import ToolRegistry, ToolInterface, PermissionDenied

# --- Helpers and Mocks for Stress Testing ---

class StressReceiver(Module):
    def __init__(self, name: str, delay: float = 0.0):
        self._name = name
        self.delay = delay
        self.received_events: List[Event] = []
        self.lock = asyncio.Lock()
        self.kernel: Optional[KernelInterface] = None

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        async with self.lock:
            self.received_events.append(event)


class ExplosiveModule(Module):
    """Module designed to throw different exceptions on purpose."""
    def __init__(self, name: str = "explosive_module"):
        self._name = name
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        self.call_count += 1
        if event.payload.get("fail_type") == "value_error":
            raise ValueError("Explosive ValueError")
        elif event.payload.get("fail_type") == "zero_division":
            _ = 1 / 0
        elif event.payload.get("fail_type") == "runtime_error":
            raise RuntimeError("Explosive RuntimeError")
        else:
            raise Exception("Generic explosive exception")


class DummyAgent(BaseAgent):
    def __init__(self, identity: str, dept: str, fail: bool = False):
        super().__init__(id=identity, name=identity, department=dept, role="worker")
        self.fail = fail
        self.executed_tasks = []

    def allowed_tools(self) -> List[str]:
        return ["calc_tool"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "department_wide"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        if self.fail:
            raise RuntimeError(f"Agent {self.name} deliberate execution failure")
        self.executed_tasks.append(task)
        return {"executed_by": self.name, "task": task}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {}

    def remember(self, knowledge: Any) -> None:
        pass


class DummyCalcTool(ToolInterface):
    name = "calc_tool"
    description = "Performs simple math calculations"
    parameters = {"op": "string", "a": "number", "b": "number"}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        op = kwargs.get("op", "add")
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        if op == "add":
            return a + b
        elif op == "divide":
            if b == 0:
                raise ZeroDivisionError("Division by zero in tool")
            return a / b
        return 0


class StrictPayloadSchema(BaseModel):
    user_id: int
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- Stress Tests ---

@pytest.mark.asyncio
async def test_high_concurrency_burst_routing():
    """STRESS 1: Send 2,000 events concurrently to test EventBus high throughput & thread/task safety."""
    kernel = Kernel()
    receivers = [StressReceiver(f"receiver_{i}") for i in range(10)]
    for r in receivers:
        kernel.register_module(r)

    total_events = 2000
    events = []
    expected_counts = {f"receiver_{i}": 0 for i in range(10)}

    for i in range(total_events):
        if i % 4 == 0:
            dest = "*"
            for k in expected_counts:
                expected_counts[k] += 1
        else:
            dest = f"receiver_{i % 10}"
            expected_counts[dest] += 1

        events.append(Event(
            source="stress_generator",
            destination=dest,
            event_type="stress.load",
            payload={"seq": i}
        ))

    start_time = time.time()
    chunk_size = 50
    for i in range(0, total_events, chunk_size):
        chunk = events[i:i + chunk_size]
        await asyncio.gather(*[kernel.send_event(e) for e in chunk])

    elapsed = time.time() - start_time

    for r in receivers:
        expected = expected_counts[r.name]
        actual = len(r.received_events)
        assert actual == expected, f"Receiver {r.name} got {actual}, expected {expected}"

    total_received = sum(len(r.received_events) for r in receivers)
    print(f"\n[STRESS 1 PASSED] 2,000 sent / {total_received} total deliveries processed in {elapsed:.3f}s ({total_events/elapsed:.1f} events/sec)")


@pytest.mark.asyncio
async def test_dynamic_wildcard_topic_concurrency_race():
    """STRESS 2: Dynamically subscribe/unsubscribe topics while high-volume routing occurs to test dict modification race conditions."""
    kernel = Kernel()
    bus = kernel.event_bus

    r1 = StressReceiver("r1")
    r2 = StressReceiver("r2")
    r3 = StressReceiver("r3")
    kernel.register_module(r1)
    kernel.register_module(r2)
    kernel.register_module(r3)

    bus.subscribe_topic(r1, "metrics.*")
    bus.subscribe_topic(r2, "*.cpu")

    stop = False

    async def event_publisher():
        seq = 0
        while not stop:
            seq += 1
            evt_type = "metrics.cpu" if seq % 2 == 0 else "metrics.memory"
            evt = Event(source="publisher", destination="r1", event_type=evt_type, payload={"seq": seq})
            await kernel.send_event(evt)
            await asyncio.sleep(0.0001)

    async def topic_mutator():
        patterns = ["metrics.*", "*.cpu", "*", "metrics.memory", "alerts.*"]
        for _ in range(50):
            pat = random.choice(patterns)
            bus.subscribe_topic(r3, pat)
            await asyncio.sleep(0.001)
            bus.unsubscribe_topic(r3, pat)
            await asyncio.sleep(0.001)

    pub_task = asyncio.create_task(event_publisher())
    mut_task = asyncio.create_task(topic_mutator())

    await mut_task
    stop = True
    await pub_task

    print("\n[STRESS 2 PASSED] Dynamic topic mutation during event routing completed without RuntimeError.")


@pytest.mark.asyncio
async def test_dlq_routing_validation_and_reprocessing():
    """STRESS 3: DLQ routing for unroutable events, invalid payload schemas, handler errors, and reprocessing."""
    kernel = Kernel()
    bus = kernel.event_bus

    # 1. Unroutable event
    unroutable = Event(source="sender", destination="ghost_module", event_type="test.ping", payload={})
    await kernel.send_event(unroutable)
    dlq = bus.get_dead_letters()
    assert len(dlq) == 1
    assert "No target subscriber found" in dlq[0]["reason"]

    # 2. Payload schema validation failure
    bus.register_payload_schema("strict.event", StrictPayloadSchema)
    valid_mod = StressReceiver("valid_mod")
    kernel.register_module(valid_mod)

    invalid_payload_evt = Event(source="sender", destination="valid_mod", event_type="strict.event", payload={"user_id": "not_an_int"})
    await kernel.send_event(invalid_payload_evt)

    assert len(valid_mod.received_events) == 0
    dlq = bus.get_dead_letters()
    assert len(dlq) == 2
    assert "Payload validation failed" in dlq[1]["reason"]

    # 3. Reprocess unroutable event after module registration
    ghost = StressReceiver("ghost_module")
    kernel.register_module(ghost)

    reprocessed = await bus.reprocess_dead_letters()
    assert len(ghost.received_events) == 1
    dlq_after = bus.get_dead_letters()
    assert len(dlq_after) == 1  # invalid payload still in DLQ
    assert "Payload validation failed" in dlq_after[0]["reason"]

    print("\n[STRESS 3 PASSED] DLQ validation, isolation, and reprocessing verified.")


@pytest.mark.asyncio
async def test_exception_isolation_multi_subscriber():
    """STRESS 4: Explosive subscriber failing with various exceptions doesn't block other subscribers."""
    kernel = Kernel()
    explosive = ExplosiveModule()
    r1 = StressReceiver("r1")
    r2 = StressReceiver("r2")

    kernel.register_module(explosive)
    kernel.register_module(r1)
    kernel.register_module(r2)

    for fail_type in ["value_error", "zero_division", "runtime_error", "generic"]:
        evt = Event(source="sender", destination="*", event_type="test.explosion", payload={"fail_type": fail_type})
        await kernel.send_event(evt)

    assert len(r1.received_events) == 4
    assert len(r2.received_events) == 4
    assert explosive.call_count == 4

    dlq = kernel.event_bus.get_dead_letters()
    assert len(dlq) == 4
    for record in dlq:
        assert "Handler exception in module 'explosive_module'" in record["reason"]

    print("\n[STRESS 4 PASSED] Exception isolation verified across multiple exception types.")


@pytest.mark.asyncio
async def test_async_queue_publish_and_shutdown_draining():
    """STRESS 5: Async queue publish, processing worker, and shutdown behavior."""
    bus = EventBus()
    receiver = StressReceiver("queue_receiver")
    bus.register_subscriber(receiver)

    await bus.start()

    # Publish 100 events
    for i in range(100):
        evt = Event(source="src", destination="queue_receiver", event_type="queue.test", payload={"i": i})
        await bus.publish(evt)

    await asyncio.sleep(0.1)

    assert len(receiver.received_events) == 100

    # Test shutdown
    await bus.shutdown()
    assert bus._worker_task is None

    print("\n[STRESS 5 PASSED] Async queue processing and shutdown verified.")


@pytest.mark.asyncio
async def test_kernel_send_event_with_async_queue_active():
    """STRESS 5B: Check Kernel.send_event behavior when EventBus async queue is running vs not running."""
    kernel = Kernel()
    receiver = StressReceiver("k_receiver")
    kernel.register_module(receiver)

    await kernel.event_bus.start()

    evt1 = Event(source="src", destination="k_receiver", event_type="k.test", payload={"msg": 1})
    await kernel.send_event(evt1)

    assert len(receiver.received_events) == 1

    evt2 = Event(source="src", destination="k_receiver", event_type="k.test", payload={"msg": 2})
    await kernel.event_bus.publish(evt2)
    await asyncio.sleep(0.05)
    assert len(receiver.received_events) == 2

    await kernel.shutdown()
    print("\n[STRESS 5B PASSED] Kernel.send_event vs EventBus.publish verified.")


@pytest.mark.asyncio
async def test_department_module_and_tool_registry_integration():
    """STRESS 6: DepartmentModule adapter and ToolRegistry service module integration under event stress."""
    kernel = Kernel()

    # Setup ToolRegistry module
    tool_reg = ToolRegistry()
    calc_tool = DummyCalcTool()
    tool_reg.register(calc_tool)
    kernel.register_module(tool_reg)

    # Setup DepartmentModule adapter
    agent = DummyAgent(identity="eng_worker_1", dept="engineering")
    dept_module = BaseDepartmentModule(agent)
    kernel.register_module(dept_module)

    # Setup mock requester client
    client = StressReceiver("client_caller")
    kernel.register_module(client)

    # 1. Execute task via DepartmentModule
    task_evt = Event(
        source="client_caller",
        destination=dept_module.name,
        event_type="department.execute_task",
        payload={"task": {"id": "task-999", "description": "Run engineering task"}}
    )
    await kernel.send_event(task_evt)

    assert len(client.received_events) == 1
    completed_evt = client.received_events[0]
    assert completed_evt.event_type == "department.task_completed"
    assert completed_evt.payload["status"] == "success"
    assert completed_evt.payload["task_id"] == "task-999"

    # 2. Execute tool via ToolRegistry event
    tool_evt = Event(
        source="client_caller",
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "calc_tool",
            "agent": {"id": "eng_worker_1", "allowed_tools": ["calc_tool"]},
            "kwargs": {"op": "add", "a": 15, "b": 27}
        }
    )
    await kernel.send_event(tool_evt)

    assert len(client.received_events) == 2
    tool_resp = client.received_events[1]
    assert tool_resp.event_type == "tool.execution_result"
    assert tool_resp.payload["status"] == "success"
    assert tool_resp.payload["result"] == 42

    # 3. Tool execution permission denied
    tool_denied_evt = Event(
        source="client_caller",
        destination="tool_registry",
        event_type="tool.execute",
        payload={
            "tool_name": "calc_tool",
            "agent": {"id": "unauthorized_agent", "allowed_tools": []},
            "kwargs": {"op": "add", "a": 1, "b": 1}
        }
    )
    await kernel.send_event(tool_denied_evt)

    assert len(client.received_events) == 3
    denied_resp = client.received_events[2]
    assert denied_resp.event_type == "tool.execution_failed"
    assert "does not have permission" in denied_resp.payload["error"]

    # 4. Department task failure handling
    failing_agent = DummyAgent(identity="failing_worker", dept="sales", fail=True)
    failing_dept_mod = BaseDepartmentModule(failing_agent)
    kernel.register_module(failing_dept_mod)

    fail_task_evt = Event(
        source="client_caller",
        destination=failing_dept_mod.name,
        event_type="department.execute_task",
        payload={"task": {"id": "task-fail", "description": "Do doomed work"}}
    )
    await kernel.send_event(fail_task_evt)

    assert len(client.received_events) == 4
    failed_evt = client.received_events[3]
    assert failed_evt.event_type == "department.task_failed"
    assert failed_evt.payload["status"] == "failed"
    assert "deliberate execution failure" in failed_evt.payload["error"]

    print("\n[STRESS 6 PASSED] DepartmentModule and ToolRegistry event contracts verified.")


@pytest.mark.asyncio
async def test_kernel_shutdown_broadcasting_and_health_metrics():
    """STRESS 7: Kernel shutdown broadcasting system.shutdown and health metrics monitoring."""
    kernel = Kernel()

    m1 = StressReceiver("m1")
    m2 = StressReceiver("m2")
    kernel.register_module(m1)
    kernel.register_module(m2)

    health = kernel.get_health_status()
    assert health["status"] == "healthy"
    assert health["module_count"] == 2
    assert "m1" in health["modules"]
    assert "m2" in health["modules"]
    assert health["event_bus"]["subscribers"] == 2

    # Perform shutdown
    await kernel.shutdown()

    assert len(m1.received_events) == 1
    assert m1.received_events[0].event_type == "system.shutdown"
    assert len(m2.received_events) == 1
    assert m2.received_events[0].event_type == "system.shutdown"

    print("\n[STRESS 7 PASSED] Kernel health monitoring and system.shutdown broadcast verified.")
