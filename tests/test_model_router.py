import pytest
import asyncio
from typing import Any, Dict, Optional

from kernel.kernel import Kernel
from shared.models import Event
from shared.interfaces import Module
from models.model_router import ModelRouter
from models.cost_tracker import CostTracker
from models.adapters.base import (
    ModelAdapter,
    ModelAdapterError,
    RateLimitError,
    ProviderUnavailableError,
)
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from models.adapters.antigravity import AntigravityAdapter


class MockScheduler(Module):
    def __init__(self):
        self.kernel = None
        self.received_events = []

    @property
    def name(self) -> str:
        return "mock_scheduler"

    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class FailingAdapter(ModelAdapter):
    def __init__(self, name: str = "Failing Tier 1", tier: str = "tier1", fail_with: Exception = RateLimitError("Quota exceeded")):
        self._name = name
        self._tier = tier
        self._fail_with = fail_with

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_id(self) -> str:
        return "failing-model"

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.001

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.002

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        raise self._fail_with


@pytest.mark.asyncio
async def test_model_router_e2e_event_flow():
    """Verify standard kernel event dispatch contract and execution result schema."""
    kernel = Kernel()
    router = ModelRouter()
    scheduler = MockScheduler()

    kernel.register_module(router)
    kernel.register_module(scheduler)

    # 1. Simple task -> Gemini Flash
    await kernel.send_event(Event(
        source=scheduler.name,
        destination=router.name,
        event_type="model.request_execution",
        payload={
            "task_id": "task_1",
            "task_description": "Short task",
            "agent": {"identity": "backend_worker"}
        }
    ))

    await asyncio.sleep(0.05)

    # 2. Hard task -> Antigravity CLI
    long_desc = "This is a very long and complex task that requires deep reasoning " * 10
    await kernel.send_event(Event(
        source=scheduler.name,
        destination=router.name,
        event_type="model.request_execution",
        payload={
            "task_id": "task_2",
            "task_description": long_desc,
            "agent": {"identity": "architecture_worker"}
        }
    ))

    await asyncio.sleep(0.05)

    assert len(scheduler.received_events) == 2

    resp1 = scheduler.received_events[0]
    assert resp1.payload["task_id"] == "task_1"
    res1 = resp1.payload["result"]
    assert res1["status"] == "success"
    assert res1["executed_by"] == "Gemini Flash"
    assert res1["agent"] == "backend_worker"
    assert "output" in res1
    assert res1["tokens"]["prompt_tokens"] > 0
    assert res1["tokens"]["completion_tokens"] > 0
    assert res1["cost"] >= 0.0

    resp2 = scheduler.received_events[1]
    assert resp2.payload["task_id"] == "task_2"
    res2 = resp2.payload["result"]
    assert res2["status"] == "success"
    assert res2["executed_by"] == "Antigravity CLI"
    assert res2["agent"] == "architecture_worker"
    assert res2["tokens"]["total_tokens"] > 0
    assert res2["cost"] >= 0.0


@pytest.mark.asyncio
async def test_model_adapters_direct():
    """Verify direct generate API for GeminiFlashAdapter, OpenRouterAdapter, and AntigravityAdapter."""
    gemini = GeminiFlashAdapter()
    openrouter = OpenRouterAdapter()
    antigravity = AntigravityAdapter()

    assert gemini.name == "Gemini Flash"
    assert gemini.tier == "tier1"
    assert gemini.model_id == "gemini-2.5-flash"
    res1 = await gemini.generate("Summarize logs", system="System rule")
    assert "output" in res1
    assert res1["model_name"] == "Gemini Flash"
    assert res1["tier"] == "tier1"
    assert res1["prompt_tokens"] > 0
    assert res1["cost_usd"] >= 0.0

    assert openrouter.name == "OpenRouter"
    assert openrouter.tier == "tier2"
    assert openrouter.model_id == "openrouter/auto"
    res2 = await openrouter.generate("Implement sort function")
    assert "output" in res2
    assert res2["model_name"] == "OpenRouter"
    assert res2["tier"] == "tier2"
    assert res2["total_tokens"] > 0

    assert antigravity.name == "Antigravity CLI"
    assert antigravity.tier == "tier3"
    assert antigravity.model_id == "antigravity-cli"
    res3 = await antigravity.generate("Design system architecture")
    assert "output" in res3
    assert res3["model_name"] == "Antigravity CLI"
    assert res3["tier"] == "tier3"


def test_decide_model_heuristics():
    """Verify decide_model heuristic selection via hints, keywords, and word count."""
    router = ModelRouter()

    # 1. Payload explicit hints
    ad_tier1 = router.decide_model("Random long description string", payload={"tier": "tier1"})
    assert ad_tier1.tier == "tier1"

    ad_tier2 = router.decide_model("Short prompt", payload={"model_hint": "openrouter"})
    assert ad_tier2.tier == "tier2"

    ad_tier3 = router.decide_model("Short prompt", payload={"preferred_tier": "tier3"})
    assert ad_tier3.tier == "tier3"

    # 2. Keyword heuristics
    ad_kw3 = router.decide_model("Perform a security audit and architecture review")
    assert ad_kw3.tier == "tier3"

    ad_kw2 = router.decide_model("Write unit test for code feature")
    assert ad_kw2.tier == "tier2"

    ad_kw1 = router.decide_model("Format and log this simple summary")
    assert ad_kw1.tier == "tier1"

    # 3. Word count heuristics
    ad_wc_short = router.decide_model("Hello world")
    assert ad_wc_short.tier == "tier1"

    ad_wc_med = router.decide_model("word " * 25)
    assert ad_wc_med.tier == "tier2"

    ad_wc_long = router.decide_model("word " * 60)
    assert ad_wc_long.tier == "tier3"


@pytest.mark.asyncio
async def test_model_router_fallback():
    """Verify automatic fallback when primary adapter encounters error."""
    failing_tier1 = FailingAdapter("Failing Tier 1", "tier1", RateLimitError("Rate limit hit"))
    working_tier2 = OpenRouterAdapter()
    working_tier3 = AntigravityAdapter()

    router = ModelRouter(adapters=[failing_tier1, working_tier2, working_tier3])

    # Attempt execution with failing preferred adapter
    res = await router.generate_with_fallback("Simple query", preferred_adapter=failing_tier1)
    assert res["model_name"] == "OpenRouter"
    assert res["tier"] == "tier2"


@pytest.mark.asyncio
async def test_model_router_all_fallback_failed():
    """Verify RuntimeError is raised when all fallback adapters fail."""
    failing1 = FailingAdapter("Fail 1", "tier1", RateLimitError("429"))
    failing2 = FailingAdapter("Fail 2", "tier2", ProviderUnavailableError("503"))
    
    router = ModelRouter(adapters=[failing1, failing2])

    with pytest.raises(RuntimeError) as exc_info:
        await router.generate_with_fallback("Test prompt")
    assert "All model adapters failed" in str(exc_info.value)


def test_cost_tracker():
    """Verify CostTracker accumulation, summaries, breakdowns, and reset."""
    tracker = CostTracker()

    tracker.record_usage(
        task_id="t1",
        agent="eng_manager",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.0001,
    )

    tracker.record_usage(
        task_id="t2",
        agent="eng_manager",
        model_name="OpenRouter",
        tier="tier2",
        prompt_tokens=200,
        completion_tokens=100,
        cost_usd=0.0021,
    )

    tracker.record_usage(
        task_id="t3",
        agent="research_manager",
        model_name="Antigravity CLI",
        tier="tier3",
        prompt_tokens=500,
        completion_tokens=300,
        cost_usd=0.0100,
    )

    summary = tracker.get_summary()
    assert summary["request_count"] == 3
    assert summary["total_prompt_tokens"] == 800
    assert summary["total_completion_tokens"] == 450
    assert summary["total_tokens"] == 1250
    assert pytest.approx(summary["total_cost_usd"], rel=1e-4) == 0.0122

    tier_bd = tracker.get_tier_breakdown()
    assert "tier1" in tier_bd
    assert "tier2" in tier_bd
    assert "tier3" in tier_bd
    assert tier_bd["tier1"]["request_count"] == 1
    assert tier_bd["tier2"]["request_count"] == 1

    agent_bd = tracker.get_agent_breakdown()
    assert "eng_manager" in agent_bd
    assert "research_manager" in agent_bd
    assert agent_bd["eng_manager"]["request_count"] == 2
    assert agent_bd["research_manager"]["request_count"] == 1

    tracker.reset()
    reset_summary = tracker.get_summary()
    assert reset_summary["request_count"] == 0
    assert reset_summary["total_cost_usd"] == 0.0
