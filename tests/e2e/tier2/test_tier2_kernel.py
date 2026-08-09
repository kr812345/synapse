import pytest
import asyncio
from typing import List, Any
from shared.interfaces import Module
from shared.models import Event
from kernel.kernel import Kernel
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event

class MockTestModule(Module):
    def __init__(self, name: str, version: int = 1):
        self._name = name
        self.version = version
        self.kernel = None
        self.received_events: List[Event] = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class FailingInjectionModule(Module):
    def __init__(self, name: str = "failing_injection"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        raise RuntimeError("Kernel injection failed simulated error")

    async def handle_event(self, event: Event) -> None:
        pass


class NonCallableInjectionModule(Module):
    def __init__(self, name: str = "non_callable_injection"):
        self._name = name
        self.set_kernel = "not_a_callable_method"  # Non-callable property

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        pass


class NoInjectionModule(Module):
    def __init__(self, name: str = "no_injection"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def handle_event(self, event: Event) -> None:
        pass


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_duplicate_module_registration(fresh_kernel: Kernel):
    """Verify kernel behavior when registering duplicate modules with the same name."""
    mod_v1 = MockTestModule("dup_mod", version=1)
    mod_v2 = MockTestModule("dup_mod", version=2)

    fresh_kernel.register_module(mod_v1)
    assert fresh_kernel.has_module("dup_mod")
    assert fresh_kernel.get_module("dup_mod") is mod_v1

    # Register second module with duplicate name
    fresh_kernel.register_module(mod_v2)
    assert fresh_kernel.has_module("dup_mod")
    assert fresh_kernel.get_module("dup_mod") is mod_v2
    assert len(fresh_kernel.modules) == 1

    # Send event and verify only latest registered instance receives it
    evt = create_test_event(source="harness", destination="dup_mod", event_type="test.ping")
    await fresh_kernel.send_event(evt)
    await asyncio.sleep(0.05)

    assert len(mod_v2.received_events) == 1
    assert len(mod_v1.received_events) == 0


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_unregistering_modules(fresh_kernel: Kernel):
    """Verify kernel dynamic module unregistration and unroutable DLQ behavior."""
    mod = MockTestModule("temp_mod")
    fresh_kernel.register_module(mod)
    assert fresh_kernel.has_module("temp_mod")
    assert "temp_mod" in fresh_kernel.list_modules()

    # Unregister module
    fresh_kernel.unregister_module("temp_mod")
    assert not fresh_kernel.has_module("temp_mod")
    assert fresh_kernel.get_module("temp_mod") is None
    assert "temp_mod" not in fresh_kernel.list_modules()

    # Send event to unregistered module -> must go to DLQ
    evt = create_test_event(source="sender", destination="temp_mod", event_type="test.unicast")
    await fresh_kernel.send_event(evt)

    dead_letters = fresh_kernel.event_bus.get_dead_letters()
    assert len(dead_letters) == 1
    assert "temp_mod" in dead_letters[0]["reason"]
    assert len(mod.received_events) == 0


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_payload_broadcasting(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify broadcast event routing with empty payloads and dict structures."""
    empty_broadcast = Event(
        source="system",
        destination="*",
        event_type="system.empty_payload_notice",
        payload={}
    )

    await fresh_kernel.send_event(empty_broadcast)

    received_event = await harness_client.wait_for_event(
        event_type="system.empty_payload_notice",
        timeout=2.0
    )

    assert_valid_event(received_event)
    assert received_event.payload == {}
    assert received_event.source == "system"
    assert received_event.destination == "*"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_concurrent_module_registrations(fresh_kernel: Kernel):
    """Verify high-concurrency dynamic module registration into Kernel."""
    modules = [MockTestModule(f"concurrent_mod_{i}") for i in range(20)]

    # Concurrently register 20 modules
    await asyncio.gather(*[asyncio.to_thread(fresh_kernel.register_module, m) for m in modules])

    health = fresh_kernel.get_health_status()
    assert health["module_count"] == 20
    assert len(fresh_kernel.list_modules()) == 20

    for m in modules:
        assert fresh_kernel.has_module(m.name)
        assert m.kernel is fresh_kernel

    # Verify broadcast reaches all 20 modules
    broadcast_evt = create_test_event(source="admin", destination="*", event_type="system.alert")
    await fresh_kernel.send_event(broadcast_evt)
    await asyncio.sleep(0.05)

    for m in modules:
        assert len(m.received_events) == 1


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_kernel_reference_injection_failure_edge_cases(fresh_kernel: Kernel):
    """Verify kernel edge cases during reference injection (non-callable, missing, failing set_kernel)."""
    # 1. Non-callable set_kernel property should not crash registration
    non_callable_mod = NonCallableInjectionModule()
    fresh_kernel.register_module(non_callable_mod)
    assert fresh_kernel.has_module(non_callable_mod.name)

    # 2. Module with no set_kernel method should register cleanly
    no_inj_mod = NoInjectionModule()
    fresh_kernel.register_module(no_inj_mod)
    assert fresh_kernel.has_module(no_inj_mod.name)

    # 3. Module set_kernel that raises an Exception propagates error cleanly
    failing_mod = FailingInjectionModule()
    with pytest.raises(RuntimeError, match="Kernel injection failed"):
        fresh_kernel.register_module(failing_mod)
