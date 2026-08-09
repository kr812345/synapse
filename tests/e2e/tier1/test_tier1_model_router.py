import pytest
import asyncio
from models.model_router import ModelRouter
from models.cost_tracker import CostTracker
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from models.adapters.antigravity import AntigravityAdapter
from shared.models import Event
from tests.e2e.helpers import assert_valid_cost_tracker_payload, create_test_event


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_gemini_flash_adapter_execution():
    """Test Tier 1 GeminiFlashAdapter directly: properties, token estimation, cost calculation, generation."""
    adapter = GeminiFlashAdapter()

    assert adapter.name == "Gemini Flash"
    assert adapter.model_id == "gemini-2.5-flash"
    assert adapter.tier == "tier1"
    assert adapter.cost_per_1k_prompt > 0.0
    assert adapter.cost_per_1k_completion > 0.0

    result = await adapter.generate("Ping message summary", system="Summarizer system prompt")

    assert result["model_name"] == "Gemini Flash"
    assert result["tier"] == "tier1"
    assert isinstance(result["output"], str) and len(result["output"]) > 0
    assert result["prompt_tokens"] > 0
    assert result["completion_tokens"] > 0
    assert result["total_tokens"] == result["prompt_tokens"] + result["completion_tokens"]
    assert result["cost_usd"] >= 0.0


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openrouter_adapter_execution():
    """Test Tier 2 OpenRouterAdapter directly: properties, token estimation, cost calculation, generation."""
    adapter = OpenRouterAdapter()

    assert adapter.name == "OpenRouter"
    assert adapter.model_id == "openrouter/auto"
    assert adapter.tier == "tier2"
    assert adapter.cost_per_1k_prompt > 0.0
    assert adapter.cost_per_1k_completion > 0.0

    result = await adapter.generate("Implement user auth route", system="Coding assistant")

    assert result["model_name"] == "OpenRouter"
    assert result["tier"] == "tier2"
    assert isinstance(result["output"], str) and len(result["output"]) > 0
    assert result["prompt_tokens"] > 0
    assert result["completion_tokens"] > 0
    assert result["total_tokens"] == result["prompt_tokens"] + result["completion_tokens"]
    assert result["cost_usd"] >= 0.0


@pytest.mark.tier1
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_antigravity_adapter_execution():
    """Test Tier 3 AntigravityAdapter directly: properties, token estimation, cost calculation, generation."""
    adapter = AntigravityAdapter()

    assert adapter.name == "Antigravity CLI"
    assert adapter.model_id == "antigravity-cli"
    assert adapter.tier == "tier3"
    assert adapter.cost_per_1k_prompt > 0.0
    assert adapter.cost_per_1k_completion > 0.0

    result = await adapter.generate("Design distributed event architecture", system="Architect assistant")

    assert result["model_name"] == "Antigravity CLI"
    assert result["tier"] == "tier3"
    assert isinstance(result["output"], str) and len(result["output"]) > 0
    assert result["prompt_tokens"] > 0
    assert result["completion_tokens"] > 0
    assert result["total_tokens"] == result["prompt_tokens"] + result["completion_tokens"]
    assert result["cost_usd"] >= 0.0


@pytest.mark.tier1
@pytest.mark.e2e
def test_heuristic_decide_model():
    """Test ModelRouter decide_model heuristics: explicit hints, keywords, and word count fallbacks."""
    router = ModelRouter()

    # 1. Explicit tier hints
    a1 = router.decide_model("arbitrary prompt", payload={"tier": "tier1"})
    assert a1.tier == "tier1"

    a2 = router.decide_model("arbitrary prompt", payload={"tier": "tier2"})
    assert a2.tier == "tier2"

    a3 = router.decide_model("arbitrary prompt", payload={"tier": "tier3"})
    assert a3.tier == "tier3"

    # 2. Keyword heuristics
    ak_arch = router.decide_model("Perform system architecture and design review")
    assert ak_arch.tier == "tier3"

    ak_code = router.decide_model("Write unit test and implement feature module")
    assert ak_code.tier == "tier2"

    ak_ping = router.decide_model("simple ping summary log format")
    assert ak_ping.tier == "tier1"

    # 3. Word count fallbacks
    short_prompt = "hello world"
    assert router.decide_model(short_prompt).tier == "tier1"


@pytest.mark.tier1
@pytest.mark.e2e
def test_cost_tracker_metrics():
    """Test CostTracker recording, aggregation, tier breakdown, agent breakdown, and reset."""
    tracker = CostTracker()

    # Record entries across different tiers and agents
    r1 = tracker.record_usage(
        task_id="t-1",
        agent="eng_agent",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.0001
    )
    assert r1["total_tokens"] == 150

    r2 = tracker.record_usage(
        task_id="t-2",
        agent="eng_agent",
        model_name="OpenRouter",
        tier="tier2",
        prompt_tokens=200,
        completion_tokens=100,
        cost_usd=0.0020
    )
    assert r2["total_tokens"] == 300

    r3 = tracker.record_usage(
        task_id="t-3",
        agent="res_agent",
        model_name="Antigravity CLI",
        tier="tier3",
        prompt_tokens=500,
        completion_tokens=250,
        cost_usd=0.0100
    )
    assert r3["total_tokens"] == 750

    # Summary
    summary = tracker.get_summary()
    assert summary["request_count"] == 3
    assert summary["total_prompt_tokens"] == 800
    assert summary["total_completion_tokens"] == 400
    assert summary["total_tokens"] == 1200
    assert summary["total_cost_usd"] == 0.0121

    # Tier breakdown
    tier_bd = tracker.get_tier_breakdown()
    assert "tier1" in tier_bd
    assert "tier2" in tier_bd
    assert "tier3" in tier_bd
    assert tier_bd["tier1"]["request_count"] == 1
    assert tier_bd["tier2"]["total_tokens"] == 300

    # Agent breakdown
    agent_bd = tracker.get_agent_breakdown()
    assert "eng_agent" in agent_bd
    assert "res_agent" in agent_bd
    assert agent_bd["eng_agent"]["request_count"] == 2
    assert agent_bd["res_agent"]["request_count"] == 1

    # Reset
    tracker.reset()
    assert tracker.get_summary()["request_count"] == 0
