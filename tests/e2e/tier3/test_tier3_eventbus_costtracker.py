import pytest
import asyncio
from typing import Any

from shared.models import Event
from models.model_router import ModelRouter
from models.cost_tracker import CostTracker

from tests.e2e.helpers import (
    assert_valid_event,
    assert_valid_cost_tracker_payload,
    create_test_event,
)


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_eventbus_event_cascade_token_tracking_multi_department(full_os_kernel, harness_client):
    """
    Test EventBus event cascade tracking token usage across multi-department execution.
    Sends model execution requests across multiple departments via EventBus,
    verifying cumulative token usage and agent-level metric aggregation in CostTracker.
    """
    model_router = full_os_kernel.get_module("model_router")
    assert isinstance(model_router, ModelRouter)
    model_router.cost_tracker.reset()

    # 1. Dispatch 3 model execution events from 3 different department identities
    task_requests = [
        {
            "task_id": "task-res-cascade-01",
            "task_description": "Summarize latest research findings on distributed ledger scaling",
            "agent": {"identity": "research_mgr"},
        },
        {
            "task_id": "task-eng-cascade-02",
            "task_description": "Refactor database query optimization module in python code",
            "agent": {"identity": "eng_mgr"},
        },
        {
            "task_id": "task-mkt-cascade-03",
            "task_description": "Draft product launch blog post and social media announcement",
            "agent": {"identity": "mkt_mgr"},
        },
    ]

    for req in task_requests:
        event = Event(
            source=harness_client.name,
            destination="model_router",
            event_type="model.request_execution",
            payload=req,
        )
        await full_os_kernel.send_event(event)

    # 2. Collect all 3 completion events using harness_client matching each task_id
    completed_task_ids = set()
    for req in task_requests:
        tid = req["task_id"]
        evt = await harness_client.wait_for_event(
            event_type="model.execution_complete",
            source="model_router",
            predicate=lambda e: e.payload.get("task_id") == tid,
            timeout=3.0,
        )
        assert_valid_event(evt)
        assert_valid_cost_tracker_payload(evt.payload)
        completed_task_ids.add(evt.payload["task_id"])

    assert len(completed_task_ids) == 3
    assert completed_task_ids == {req["task_id"] for req in task_requests}

    # 3. Verify aggregate metrics in CostTracker
    summary = model_router.cost_tracker.get_summary()
    assert summary["request_count"] == 3
    assert summary["total_tokens"] > 0
    assert summary["total_prompt_tokens"] > 0
    assert summary["total_completion_tokens"] > 0
    assert summary["total_cost_usd"] >= 0.0

    agent_breakdown = model_router.cost_tracker.get_agent_breakdown()
    assert "research_mgr" in agent_breakdown
    assert "eng_mgr" in agent_breakdown
    assert "mkt_mgr" in agent_breakdown

    for agent_id in ("research_mgr", "eng_mgr", "mkt_mgr"):
        info = agent_breakdown[agent_id]
        assert info["request_count"] == 1
        assert info["total_tokens"] > 0
        assert info["cost_usd"] >= 0.0


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_costtracker_cumulative_financial_calculation_broadcast_events(full_os_kernel, harness_client):
    """
    Test CostTracker cumulative financial calculation during broadcast events.
    Verifies that multi-tier execution costs strictly sum up to total cost,
    and tier breakdowns match individual request allocations.
    """
    model_router = full_os_kernel.get_module("model_router")
    assert isinstance(model_router, ModelRouter)
    model_router.cost_tracker.reset()

    # Dispatch tasks designed to trigger different model adapter tiers
    multi_tier_prompts = [
        ("t1-summary", "Simple summary of status ping log", "tier1"),
        ("t2-code", "Implement unit test for API endpoint in code", "tier2"),
        ("t3-arch", "Deep architecture refactor and security audit", "tier3"),
    ]

    for task_id, desc, tier_hint in multi_tier_prompts:
        event = Event(
            source=harness_client.name,
            destination="model_router",
            event_type="model.request_execution",
            payload={
                "task_id": task_id,
                "task_description": desc,
                "preferred_tier": tier_hint,
                "agent": {"identity": f"agent_{tier_hint}"},
            },
        )
        await full_os_kernel.send_event(event)

    for task_id, desc, tier_hint in multi_tier_prompts:
        tid = task_id
        evt = await harness_client.wait_for_event(
            event_type="model.execution_complete",
            source="model_router",
            predicate=lambda e: e.payload.get("task_id") == tid,
            timeout=3.0,
        )
        assert_valid_event(evt)
        assert_valid_cost_tracker_payload(evt.payload)

    summary = model_router.cost_tracker.get_summary()
    tier_breakdown = model_router.cost_tracker.get_tier_breakdown()

    # Sum of tier costs must match total cumulative cost
    summed_tier_cost = round(sum(t["cost_usd"] for t in tier_breakdown.values()), 6)
    assert summary["total_cost_usd"] == summed_tier_cost

    # Sum of tier tokens must match total tokens
    summed_tokens = sum(t["total_tokens"] for t in tier_breakdown.values())
    assert summary["total_tokens"] == summed_tokens
    assert summary["request_count"] == len(multi_tier_prompts)


@pytest.mark.tier3
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_costtracker_audit_logging(fresh_kernel):
    """
    Test CostTracker audit logging capabilities.
    Verifies detailed record logging format, field types, timestamp ISO formats,
    and clean state reset.
    """
    tracker = CostTracker()

    rec1 = tracker.record_usage(
        task_id="audit-101",
        agent="audit_agent_1",
        model_name="gemini-1.5-flash",
        tier="tier1",
        prompt_tokens=150,
        completion_tokens=50,
        cost_usd=0.00015,
    )
    rec2 = tracker.record_usage(
        task_id="audit-102",
        agent="audit_agent_2",
        model_name="anthropic/claude-3.5-sonnet",
        tier="tier2",
        prompt_tokens=400,
        completion_tokens=200,
        cost_usd=0.00300,
    )

    assert len(tracker._records) == 2
    assert rec1["task_id"] == "audit-101"
    assert rec1["agent"] == "audit_agent_1"
    assert rec1["total_tokens"] == 200
    assert isinstance(rec1["timestamp"], str)

    assert rec2["task_id"] == "audit-102"
    assert rec2["agent"] == "audit_agent_2"
    assert rec2["total_tokens"] == 600
    assert rec2["cost_usd"] == 0.00300

    summary = tracker.get_summary()
    assert summary["request_count"] == 2
    assert summary["total_prompt_tokens"] == 550
    assert summary["total_completion_tokens"] == 250
    assert summary["total_tokens"] == 800
    assert summary["total_cost_usd"] == round(0.00015 + 0.00300, 6)

    # Test reset behavior
    tracker.reset()
    assert len(tracker._records) == 0
    empty_summary = tracker.get_summary()
    assert empty_summary["request_count"] == 0
    assert empty_summary["total_tokens"] == 0
    assert empty_summary["total_cost_usd"] == 0.0
