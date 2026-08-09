import pytest
import asyncio
from typing import Any, Dict, Optional
from shared.models import Event
from kernel.kernel import Kernel
from models.model_router import ModelRouter
from models.cost_tracker import CostTracker
from models.adapters.base import ModelAdapter, ProviderUnavailableError
from models.adapters.openrouter import OpenRouterAdapter
from tests.e2e.conftest import OpaqueTestHarness
from tests.e2e.helpers import assert_valid_cost_tracker_payload, create_test_event


class FailingMockAdapter(ModelAdapter):
    @property
    def name(self) -> str:
        return "Failing Primary Gemini"

    @property
    def model_id(self) -> str:
        return "gemini-failing-1"

    @property
    def tier(self) -> str:
        return "tier1"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.001

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.002

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        raise ProviderUnavailableError("Simulated 503 Provider API Unavailable")


class BackupMockAdapter(ModelAdapter):
    @property
    def name(self) -> str:
        return "Backup OpenRouter"

    @property
    def model_id(self) -> str:
        return "openrouter-backup-2"

    @property
    def tier(self) -> str:
        return "tier2"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.005

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.01

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        return {
            "output": f"Backup generated output for: {prompt}",
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "cost_usd": 0.00025,
            "raw_response": {}
        }


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_adapter_api_error_failover_to_backup_tier():
    """Verify automatic multi-tier fallback redundancy when primary adapter fails."""
    primary = FailingMockAdapter()
    backup = BackupMockAdapter()

    router = ModelRouter(adapters=[primary, backup])

    # Preferred adapter tier1 fails, should cascade to backup tier2 adapter
    result = await router.generate_with_fallback("Write python code", preferred_adapter="tier1")

    assert result["model_name"] == "Backup OpenRouter"
    assert result["tier"] == "tier2"
    assert "Backup generated output" in result["output"]

    # When all adapters fail, RuntimeError is raised
    all_failing_router = ModelRouter(adapters=[primary])
    with pytest.raises(RuntimeError, match="All model adapters failed"):
        await all_failing_router.generate_with_fallback("Write python code")


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_empty_prompt_handling():
    """Verify model router decision heuristics and token estimation for empty or whitespace prompts."""
    router = ModelRouter()

    # Empty prompt heuristic defaults to tier1 adapter
    adapter = router.decide_model("")
    assert adapter.tier == "tier1"

    # Whitespace prompt heuristic defaults to tier1 adapter
    adapter_ws = router.decide_model("    \n\t  ")
    assert adapter_ws.tier == "tier1"

    # Token estimation handles empty string cleanly
    assert adapter.estimate_tokens("") == 0
    assert adapter.estimate_tokens(None) == 0

    # Generation with empty prompt returns valid structure
    res = await router.generate_with_fallback("")
    assert "output" in res
    assert res["prompt_tokens"] >= 0


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_unknown_agent_contracts(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify event processing and cost tracking when execution request has missing/unrecognized agent contract."""
    router = ModelRouter()
    fresh_kernel.register_module(router)

    # Send model execution request with agent=None
    evt1 = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={
            "task_id": "task-unknown-1",
            "task_description": "Summarize log output",
            "agent": None
        }
    )
    await fresh_kernel.send_event(evt1)

    completed_evt1 = await harness_client.wait_for_event(event_type="model.execution_complete")
    res1 = completed_evt1.payload["result"]
    assert res1["status"] == "success"
    assert res1["agent"] == "unknown"

    # Verify agent breakdown records unknown agent usage cleanly
    agent_breakdown = router.cost_tracker.get_agent_breakdown()
    assert "unknown" in agent_breakdown
    assert agent_breakdown["unknown"]["request_count"] >= 1


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_zero_token_cost_calculation_edge_cases():
    """Verify CostTracker handling of 0 tokens, negative numbers, extreme values, and summary metrics."""
    tracker = CostTracker()

    # 1. Zero tokens and 0 cost
    r1 = tracker.record_usage(
        task_id="t1",
        agent="agent_a",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=0.0
    )
    assert r1["total_tokens"] == 0
    assert r1["cost_usd"] == 0.0

    # 2. Negative token inputs clamped to 0
    r2 = tracker.record_usage(
        task_id="t2",
        agent="agent_a",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=-10,
        completion_tokens=-5,
        cost_usd=-2.5
    )
    assert r2["prompt_tokens"] == 0
    assert r2["completion_tokens"] == 0
    assert r2["cost_usd"] == 0.0

    # 3. High volume token counts
    r3 = tracker.record_usage(
        task_id="t3",
        agent="agent_b",
        model_name="Antigravity",
        tier="tier3",
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        cost_usd=15.75
    )
    assert r3["total_tokens"] == 1_500_000

    summary = tracker.get_summary()
    assert summary["total_cost_usd"] == 15.75
    assert summary["request_count"] == 3

    # Validate model execution result wrapper schema helper
    exec_res = {
        "status": "success",
        "executed_by": r3["model_name"],
        "agent": r3["agent"],
        "output": "sample",
        "tokens": {"prompt_tokens": r3["prompt_tokens"], "completion_tokens": r3["completion_tokens"], "total_tokens": r3["total_tokens"]},
        "cost": r3["cost_usd"]
    }
    assert_valid_cost_tracker_payload(exec_res)


@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.asyncio
async def test_malformed_execution_request_schemas(fresh_kernel: Kernel, harness_client: OpaqueTestHarness):
    """Verify robustness of ModelRouter handle_event against malformed execution request schemas."""
    router = ModelRouter()
    fresh_kernel.register_module(router)

    # Payload with missing task_id and missing task_description
    evt_malformed = Event(
        source=harness_client.name,
        destination="model_router",
        event_type="model.request_execution",
        payload={}
    )

    await fresh_kernel.send_event(evt_malformed)

    response_evt = await harness_client.wait_for_event(event_type="model.execution_complete")
    res = response_evt.payload["result"]
    assert res["status"] == "success"
    assert res["agent"] is None or res["agent"] == "unknown"
    assert_valid_cost_tracker_payload(res)
