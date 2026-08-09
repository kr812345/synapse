import pytest
import asyncio
from departments.echo.echo_manager import EchoDepartment
from shared.models import Event
from tests.e2e.helpers import assert_valid_event, assert_event_matches, create_test_event


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_department_ping_pong(fresh_kernel, harness_client):
    """Test EchoDepartment receiving ping event and responding with pong event."""
    echo_dept = EchoDepartment()
    fresh_kernel.register_module(echo_dept)

    ping_event = create_test_event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload={"msg": "ping_test"}
    )

    await fresh_kernel.send_event(ping_event)

    pong_event = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department",
        timeout=2.0
    )

    assert_event_matches(
        pong_event,
        source="echo_department",
        destination=harness_client.name,
        event_type="pong"
    )
    assert pong_event.payload["original_payload"]["msg"] == "ping_test"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_department_payload_preservation(fresh_kernel, harness_client):
    """Test EchoDepartment payload preservation: verifying complex nested payloads in pong response."""
    echo_dept = EchoDepartment()
    fresh_kernel.register_module(echo_dept)

    complex_payload = {
        "string_key": "val1",
        "int_key": 42,
        "list_key": [1, 2, 3, "a"],
        "nested_dict": {"flag": True, "score": 98.6}
    }

    ping_event = create_test_event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload=complex_payload
    )

    await fresh_kernel.send_event(ping_event)

    pong_event = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department",
        timeout=2.0
    )

    assert pong_event.payload["original_payload"] == complex_payload


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_department_source_routing(fresh_kernel, harness_client):
    """Test EchoDepartment source routing: verifying pong response destination equals original event source."""
    echo_dept = EchoDepartment()
    fresh_kernel.register_module(echo_dept)

    ping_event = create_test_event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload={"request_id": "req-999"}
    )

    await fresh_kernel.send_event(ping_event)

    pong_event = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department",
        timeout=2.0
    )

    assert pong_event.destination == harness_client.name
    assert pong_event.source == "echo_department"


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_department_ignore_non_ping_events(fresh_kernel, harness_client):
    """Test EchoDepartment ignores non-ping event types and does not emit pong."""
    echo_dept = EchoDepartment()
    fresh_kernel.register_module(echo_dept)

    non_ping_event = create_test_event(
        source=harness_client.name,
        destination="echo_department",
        event_type="info",
        payload={"info": "do not echo"}
    )

    await fresh_kernel.send_event(non_ping_event)

    await asyncio.sleep(0.05)
    assert len(harness_client.received_events) == 0


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_echo_department_full_os_kernel_integration(full_os_kernel, harness_client):
    """Test EchoDepartment end-to-end integration within full_os_kernel environment."""
    ping_event = create_test_event(
        source=harness_client.name,
        destination="echo_department",
        event_type="ping",
        payload={"full_os": True}
    )

    await full_os_kernel.send_event(ping_event)

    pong_event = await harness_client.wait_for_event(
        event_type="pong",
        source="echo_department",
        timeout=2.0
    )

    assert_event_matches(
        pong_event,
        source="echo_department",
        destination=harness_client.name,
        event_type="pong"
    )
    assert pong_event.payload["original_payload"]["full_os"] is True
