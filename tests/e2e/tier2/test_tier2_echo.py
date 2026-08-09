import pytest
import asyncio
from shared.models import Event
from kernel.kernel import Kernel
from departments.echo.echo_manager import EchoDepartment
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_event, create_test_event


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_ping_payload(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify EchoDepartment ping handling with empty dictionary payload."""
    echo = EchoDepartment()
    fresh_kernel.register_module(echo)

    ping_evt = Event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload={}
    )

    await fresh_kernel.send_event(ping_evt)

    pong_evt = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department"
    )

    assert_valid_event(pong_evt)
    assert pong_evt.payload == {"original_payload": {}}


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_nested_dictionary_ping_payload(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify EchoDepartment ping handling with deeply nested dictionary structure."""
    echo = EchoDepartment()
    fresh_kernel.register_module(echo)

    nested_payload = {
        "level1": {
            "level2": {
                "key": "value",
                "list_data": [10, 20, 30],
                "active": True
            }
        }
    }

    ping_evt = Event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload=nested_payload
    )

    await fresh_kernel.send_event(ping_evt)

    pong_evt = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department"
    )

    assert_valid_event(pong_evt)
    assert pong_evt.payload["original_payload"] == nested_payload


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_rapid_succession_pings(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify EchoDepartment processes rapid succession ping bursts deterministically."""
    echo = EchoDepartment()
    fresh_kernel.register_module(echo)

    ping_count = 30
    for i in range(ping_count):
        ping = Event(
            source=harness_client.name,
            destination="echo_department",
            event_type="ping",
            payload={"seq": i}
        )
        await fresh_kernel.send_event(ping)

    await asyncio.sleep(0.1)

    pongs = [e for e in harness_client.received_events if e.event_type == "pong"]
    assert len(pongs) == ping_count
    received_seqs = [e.payload["original_payload"]["seq"] for e in pongs]
    assert received_seqs == list(range(ping_count))


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_broadcast_ping_rejection(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify EchoDepartment handling of broadcast pings (destination="*")."""
    echo = EchoDepartment()
    fresh_kernel.register_module(echo)

    broadcast_ping = Event(
        source="system_admin",
        destination="*",
        event_type="ping",
        payload={"msg": "broadcast_ping"}
    )

    await fresh_kernel.send_event(broadcast_ping)

    # Echo department responds with pong targeted back to system_admin
    # Harness client receives broadcast_ping from system_admin directly
    b_received = await harness_client.wait_for_event(event_type="ping", source="system_admin")
    assert b_received.payload["msg"] == "broadcast_ping"


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_invalid_destination_ping(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify EchoDepartment ignores pings explicitly addressed to other module destinations."""
    echo = EchoDepartment()
    fresh_kernel.register_module(echo)

    misaddressed_ping = Event(
        source=harness_client.name,
        destination="wrong_department_xyz",
        event_type="ping",
        payload={"msg": "wrong_dest"}
    )

    await fresh_kernel.send_event(misaddressed_ping)
    await asyncio.sleep(0.05)

    # Echo department does NOT issue pong response to event meant for another destination
    pongs = [e for e in harness_client.received_events if e.event_type == "pong"]
    assert len(pongs) == 0

    # Misaddressed event is captured in dead-letter queue
    dlq = fresh_kernel.event_bus.get_dead_letters()
    assert len(dlq) == 1
    assert "wrong_department_xyz" in dlq[0]["reason"]
