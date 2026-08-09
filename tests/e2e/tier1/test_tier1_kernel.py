import pytest
import asyncio
from kernel.kernel import Kernel
from shared.interfaces import Module
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


class MockModule(Module):
    """Simple mock module for testing Kernel dynamic registration."""
    def __init__(self, mod_name: str = "mock_mod"):
        self._name = mod_name
        self.kernel = None
        self.received_events = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


@pytest.mark.tier1
@pytest.mark.e2e
def test_kernel_dynamic_registration(fresh_kernel):
    """Test dynamic runtime module registration, kernel reference injection, and unregistration."""
    mod = MockModule("dynamic_module_1")

    # Verify registration
    fresh_kernel.register_module(mod)
    assert fresh_kernel.has_module("dynamic_module_1")
    assert fresh_kernel.get_module("dynamic_module_1") is mod
    assert mod.kernel is fresh_kernel
    assert "dynamic_module_1" in fresh_kernel.list_modules()

    # Verify unregistration
    fresh_kernel.unregister_module("dynamic_module_1")
    assert not fresh_kernel.has_module("dynamic_module_1")
    assert fresh_kernel.get_module("dynamic_module_1") is None
    assert "dynamic_module_1" not in fresh_kernel.list_modules()


@pytest.mark.tier1
@pytest.mark.e2e
def test_kernel_interface_enforcement(fresh_kernel):
    """Test Kernel interface enforcement: rejecting invalid modules and empty names."""
    # 1. Non-Module object
    class NotAModule:
        name = "invalid"

    with pytest.raises(TypeError):
        fresh_kernel.register_module(NotAModule())

    # 2. Module with empty name
    class EmptyNameModule(Module):
        @property
        def name(self) -> str:
            return ""

        async def handle_event(self, event: Event) -> None:
            pass

    with pytest.raises(ValueError):
        fresh_kernel.register_module(EmptyNameModule())

    # 3. Module with non-string name
    class NoneNameModule(Module):
        @property
        def name(self) -> str:
            return None

        async def handle_event(self, event: Event) -> None:
            pass

    with pytest.raises(ValueError):
        fresh_kernel.register_module(NoneNameModule())


@pytest.mark.tier1
@pytest.mark.e2e
def test_kernel_health_monitoring(fresh_kernel, harness_client):
    """Test Kernel health status monitoring and metrics reporting."""
    health = fresh_kernel.get_health_status()
    
    assert health["status"] == "healthy"
    assert isinstance(health["uptime_seconds"], (int, float))
    assert health["uptime_seconds"] >= 0.0
    assert isinstance(health["modules"], list)
    assert "harness_client" in health["modules"]
    assert health["module_count"] == len(health["modules"])
    assert isinstance(health["event_bus"], dict)
    assert "subscribers" in health["event_bus"]


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_kernel_shutdown_broadcast(fresh_kernel, harness_client):
    """Test Kernel shutdown broadcasting system.shutdown event to all registered modules."""
    await fresh_kernel.shutdown()

    shutdown_event = await harness_client.wait_for_event(
        event_type="system.shutdown",
        source="kernel",
        timeout=2.0
    )
    assert_event_matches(
        shutdown_event,
        source="kernel",
        destination="*",
        event_type="system.shutdown"
    )


@pytest.mark.tier1
@pytest.mark.e2e
def test_kernel_module_tracking(fresh_kernel):
    """Test Kernel module tracking functions: has_module, get_module, and list_modules."""
    m1 = MockModule("mod_alpha")
    m2 = MockModule("mod_beta")

    assert fresh_kernel.list_modules() == []

    fresh_kernel.register_module(m1)
    fresh_kernel.register_module(m2)

    assert len(fresh_kernel.list_modules()) == 2
    assert fresh_kernel.has_module("mod_alpha") is True
    assert fresh_kernel.has_module("mod_beta") is True
    assert fresh_kernel.has_module("mod_gamma") is False

    assert fresh_kernel.get_module("mod_alpha") is m1
    assert fresh_kernel.get_module("mod_beta") is m2
    assert fresh_kernel.get_module("mod_gamma") is None

    fresh_kernel.unregister_module("mod_alpha")
    assert fresh_kernel.has_module("mod_alpha") is False
    assert len(fresh_kernel.list_modules()) == 1
