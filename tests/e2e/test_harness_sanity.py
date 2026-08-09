import pytest
import asyncio
from shared.models import Event
from tests.e2e.helpers import (
    assert_valid_event,
    assert_event_matches,
    assert_valid_task,
    assert_valid_dag,
    assert_valid_knowledge,
    assert_valid_cost_tracker_payload,
    create_test_event,
    create_test_task,
    create_test_dag,
    create_test_knowledge
)

@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_opaque_harness_wait_for_event(fresh_kernel, harness_client):
    """Verify OpaqueTestHarness receives events and wait_for_event resolves deterministically."""
    event = create_test_event(source="test_sender", destination="*", event_type="test.ping", payload={"key": "value"})
    await fresh_kernel.send_event(event)

    received = await harness_client.wait_for_event(event_type="test.ping", source="test_sender", timeout=1.0)
    assert_event_matches(received, source="test_sender", event_type="test.ping", payload_subset={"key": "value"})

@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_os_kernel_echo_department(full_os_kernel, harness_client):
    """Verify full_os_kernel routes ping to echo_department and harness intercepts pong response."""
    ping_event = create_test_event(source=harness_client.name, destination="echo_department", event_type="ping", payload={"hello": "world"})
    await full_os_kernel.send_event(ping_event)

    pong_event = await harness_client.wait_for_event(event_type="pong", source="echo_department", timeout=2.0)
    assert_event_matches(pong_event, source="echo_department", destination=harness_client.name, event_type="pong")
    assert pong_event.payload["original_payload"] == {"hello": "world"}

@pytest.mark.tier1
@pytest.mark.e2e
def test_schema_validators_helpers():
    """Verify schema validation assertion functions in tests/e2e/helpers.py."""
    task = create_test_task("Build feature X")
    assert_valid_task(task)

    dag = create_test_dag("Pipeline DAG", tasks=[task])
    assert_valid_dag(dag)

    knowledge = create_test_knowledge("Test observation")
    assert_valid_knowledge(knowledge)

    cost_payload = {
        "status": "success",
        "executed_by": "Gemini Flash",
        "tokens": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "cost": 0.00015
    }
    assert_valid_cost_tracker_payload(cost_payload)
