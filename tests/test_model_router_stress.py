import pytest
import asyncio
import io
import urllib.error
from unittest.mock import patch, MagicMock
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
    AuthenticationError,
)
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from models.adapters.antigravity import AntigravityAdapter


class MockEventReceiver(Module):
    def __init__(self, name: str = "mock_receiver"):
        self._name = name
        self.kernel = None
        self.received_events = []

    @property
    def name(self) -> str:
        return self._name

    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        self.received_events.append(event)


class ControlledAdapter(ModelAdapter):
    def __init__(
        self,
        name: str = "Controlled Adapter",
        model_id: str = "controlled-model",
        tier: str = "tier1",
        cost_prompt: float = 0.001,
        cost_completion: float = 0.002,
        fail_exception: Optional[Exception] = None,
        delay_seconds: float = 0.0,
    ):
        self._name = name
        self._model_id = model_id
        self._tier = tier
        self._cost_prompt = cost_prompt
        self._cost_completion = cost_completion
        self._fail_exception = fail_exception
        self._delay_seconds = delay_seconds
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_per_1k_prompt(self) -> float:
        return self._cost_prompt

    @property
    def cost_per_1k_completion(self) -> float:
        return self._cost_completion

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        self.call_count += 1
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        if self._fail_exception:
            raise self._fail_exception
        
        prompt_tokens = self.estimate_tokens(prompt) + self.estimate_tokens(system)
        completion_tokens = self.estimate_tokens("Controlled output response")
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.calculate_cost(prompt_tokens, completion_tokens)
        return {
            "output": f"Output from {self._name}",
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "raw_response": {"provider": "controlled"},
        }


# ============================================================================
# STRESS TEST SUITE 1: Routing Heuristics & Boundary Conditions (MR-05)
# ============================================================================

def test_decide_model_edge_cases():
    """Stress test decision logic with obscure, conflicting, or malformed inputs."""
    router = ModelRouter()

    # Case 1: Payload hints take priority over task description keywords
    res = router.decide_model(
        task_description="Perform deep system architecture review and refactor code",
        payload={"tier": "tier1"}
    )
    assert res.tier == "tier1", "Payload tier hint must override description keywords"

    # Case 2: Model hint by adapter model_id
    res = router.decide_model("Simple prompt", payload={"model_hint": "antigravity-cli"})
    assert res.tier == "tier3"

    res = router.decide_model("Simple prompt", payload={"model_hint": "gemini-2.5-flash"})
    assert res.tier == "tier1"

    # Case 3: Empty string description with no payload
    res = router.decide_model("")
    assert res.tier == "tier1", "Empty string (0 words) should default to tier1"

    # Case 4: Non-string payload hint (e.g. integer)
    res = router.decide_model("Code feature implementation", payload={"tier": 123})
    assert res.tier == "tier2", "Non-string payload hint should be ignored and fall through to keywords"

    # Case 5: Word count exact boundaries: 9 words -> tier1, 10 words -> tier2, 49 words -> tier2, 50 words -> tier3
    words_9 = " ".join([f"w{i}" for i in range(9)])
    words_10 = " ".join([f"w{i}" for i in range(10)])
    words_49 = " ".join([f"w{i}" for i in range(49)])
    words_50 = " ".join([f"w{i}" for i in range(50)])

    assert router.decide_model(words_9).tier == "tier1"
    assert router.decide_model(words_10).tier == "tier2"
    assert router.decide_model(words_49).tier == "tier2"
    assert router.decide_model(words_50).tier == "tier3"


def test_adapter_equality_and_repr():
    """Test model adapter equality comparison and string representations."""
    g1 = GeminiFlashAdapter()
    g2 = GeminiFlashAdapter()
    o1 = OpenRouterAdapter()

    assert g1 == g2
    assert g1 == "Gemini Flash"
    assert g1 == "gemini-2.5-flash"
    assert g1 == "tier1"
    assert g1 != o1
    assert g1 != 12345

    assert repr(g1) == "<GeminiFlashAdapter name='Gemini Flash' model_id='gemini-2.5-flash' tier='tier1'>"
    assert str(g1) == "Gemini Flash"


# ============================================================================
# STRESS TEST SUITE 2: Multi-Tier Fallback Redundancy Cascading (MR-06)
# ============================================================================

@pytest.mark.asyncio
async def test_fallback_cascading_chain():
    """Verify fallback chain calls adapters sequentially until success."""
    fail1 = ControlledAdapter("Fail 1", "m1", "tier1", fail_exception=RateLimitError("429"))
    fail2 = ControlledAdapter("Fail 2", "m2", "tier2", fail_exception=ProviderUnavailableError("503"))
    succ3 = ControlledAdapter("Success 3", "m3", "tier3")

    router = ModelRouter(adapters=[fail1, fail2, succ3])

    res = await router.generate_with_fallback("Do task", preferred_adapter=fail1)

    assert fail1.call_count == 1
    assert fail2.call_count == 1
    assert succ3.call_count == 1
    assert res["model_name"] == "Success 3"
    assert res["tier"] == "tier3"


@pytest.mark.asyncio
async def test_fallback_all_fail_raises_runtime_error():
    """Verify RuntimeError with last exception context when all adapters fail."""
    fail1 = ControlledAdapter("Fail 1", "m1", "tier1", fail_exception=RateLimitError("429"))
    fail2 = ControlledAdapter("Fail 2", "m2", "tier2", fail_exception=AuthenticationError("401"))

    router = ModelRouter(adapters=[fail1, fail2])

    with pytest.raises(RuntimeError) as exc_info:
        await router.generate_with_fallback("Do task", preferred_adapter=fail1)

    assert "All model adapters failed to execute prompt" in str(exc_info.value)
    assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_concurrent_fallback_executions():
    """Stress test concurrent async calls to generate_with_fallback."""
    fail1 = ControlledAdapter("Fail 1", "m1", "tier1", fail_exception=RateLimitError("429"))
    succ2 = ControlledAdapter("Succ 2", "m2", "tier2", delay_seconds=0.01)

    router = ModelRouter(adapters=[fail1, succ2])

    tasks = [
        router.generate_with_fallback(f"Prompt {i}", preferred_adapter=fail1)
        for i in range(50)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    assert all(r["model_name"] == "Succ 2" for r in results)
    assert succ2.call_count == 50


# ============================================================================
# STRESS TEST SUITE 3: Cost Tracker Precision & Aggregation (MR-07)
# ============================================================================

def test_cost_tracker_precision_and_aggregation():
    """Stress test floating point precision, zero/negative inputs, and agent breakdowns."""
    tracker = CostTracker()

    # 1. Micro-cost tracking with 6 decimal places
    tracker.record_usage(
        task_id="t1",
        agent="agent_a",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.000075,
    )
    tracker.record_usage(
        task_id="t2",
        agent="agent_a",
        model_name="Gemini Flash",
        tier="tier1",
        prompt_tokens=200,
        completion_tokens=100,
        cost_usd=0.000150,
    )
    tracker.record_usage(
        task_id="t3",
        agent="agent_b",
        model_name="OpenRouter",
        tier="tier2",
        prompt_tokens=1000,
        completion_tokens=500,
        cost_usd=0.010500,
    )

    summary = tracker.get_summary()
    assert summary["request_count"] == 3
    assert summary["total_prompt_tokens"] == 1300
    assert summary["total_completion_tokens"] == 650
    assert summary["total_tokens"] == 1950
    assert summary["total_cost_usd"] == 0.010725

    # Tier breakdown check
    tier_bd = tracker.get_tier_breakdown()
    assert tier_bd["tier1"]["cost_usd"] == 0.000225
    assert tier_bd["tier2"]["cost_usd"] == 0.010500
    assert tier_bd["tier1"]["total_tokens"] == 450
    assert tier_bd["tier2"]["total_tokens"] == 1500

    # Agent breakdown check
    agent_bd = tracker.get_agent_breakdown()
    assert agent_bd["agent_a"]["cost_usd"] == 0.000225
    assert agent_bd["agent_a"]["request_count"] == 2
    assert agent_bd["agent_b"]["cost_usd"] == 0.010500
    assert agent_bd["agent_b"]["request_count"] == 1

    # 2. Stress test zero/negative token/cost guard
    rec_neg = tracker.record_usage(
        task_id=None,
        agent=None,
        model_name="TestModel",
        tier="tier1",
        prompt_tokens=-50,
        completion_tokens=-20,
        cost_usd=-0.05,
    )
    assert rec_neg["prompt_tokens"] == 0
    assert rec_neg["completion_tokens"] == 0
    assert rec_neg["total_tokens"] == 0
    assert rec_neg["cost_usd"] == 0.0
    assert rec_neg["task_id"] == "unknown"
    assert rec_neg["agent"] == "unknown"


# ============================================================================
# STRESS TEST SUITE 4: Provider Adapter Exception Handling (MR-02..MR-04)
# ============================================================================

def make_http_error(code: int, msg: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example.com", code, msg, {}, io.BytesIO(msg.encode("utf-8")))


@pytest.mark.asyncio
async def test_gemini_adapter_error_mapping():
    """Verify HTTP status codes map to specific ModelAdapterError subclasses."""
    adapter = GeminiFlashAdapter(api_key="fake_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        # Test 429 Rate Limit
        mock_urlopen.side_effect = make_http_error(429, "Rate limit exceeded")
        with pytest.raises(RateLimitError):
            await adapter.generate("Test prompt")

        # Test 401 Authentication
        mock_urlopen.side_effect = make_http_error(401, "Unauthorized")
        with pytest.raises(AuthenticationError):
            await adapter.generate("Test prompt")

        # Test 503 Provider Unavailable
        mock_urlopen.side_effect = make_http_error(503, "Service Unavailable")
        with pytest.raises(ProviderUnavailableError):
            await adapter.generate("Test prompt")


@pytest.mark.asyncio
async def test_openrouter_adapter_error_mapping():
    """Verify OpenRouter HTTP status code exception mapping."""
    adapter = OpenRouterAdapter(api_key="fake_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = make_http_error(429, "Quota exceeded")
        with pytest.raises(RateLimitError):
            await adapter.generate("Test prompt")


@pytest.mark.asyncio
async def test_antigravity_adapter_subprocess_error():
    """Verify Antigravity CLI process error handling."""
    adapter = AntigravityAdapter(binary_path="/bin/fake_agy")

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec") as mock_exec:
        
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        
        async def mock_communicate():
            return (b"", b"Rate limit exceeded on CLI")

        mock_proc.communicate = mock_communicate
        mock_exec.return_value = mock_proc

        with pytest.raises(RateLimitError):
            await adapter.generate("Architect prompt", use_cli=True)


@pytest.mark.asyncio
async def test_adapter_simulation_fallback_when_unconfigured():
    """Verify adapters fall back seamlessly to simulation mode when no API keys/binary configured."""
    gemini = GeminiFlashAdapter(api_key=None)
    openrouter = OpenRouterAdapter(api_key=None)
    antigravity = AntigravityAdapter(binary_path=None)

    # Gemini
    res_g = await gemini.generate("Summary task", system="sys")
    assert "Gemini Flash processed task" in res_g["output"]
    assert res_g["raw_response"]["mode"] == "simulation"

    # OpenRouter
    res_o = await openrouter.generate("Coding task", system="sys")
    assert "OpenRouter reasoning output" in res_o["output"]
    assert res_o["raw_response"]["mode"] == "simulation"

    # Antigravity
    res_a = await antigravity.generate("Design task", system="sys")
    assert "Antigravity CLI deep architecture response" in res_a["output"]
    assert res_a["raw_response"]["mode"] == "simulation"


# ============================================================================
# STRESS TEST SUITE 5: Event Bus Integration & Concurrency Contract (MR-08, MR-09)
# ============================================================================

@pytest.mark.asyncio
async def test_model_router_event_contract_stress():
    """Stress test ModelRouter with 100 concurrent execution requests over Kernel EventBus."""
    kernel = Kernel()
    router = ModelRouter()
    receiver = MockEventReceiver("test_scheduler")

    kernel.register_module(router)
    kernel.register_module(receiver)

    req_count = 100
    events = [
        Event(
            source=receiver.name,
            destination=router.name,
            event_type="model.request_execution",
            payload={
                "task_id": f"stress_task_{i}",
                "task_description": f"Task description number {i} with code feature kw",
                "agent": {"identity": f"worker_{i % 5}"},
            },
        )
        for i in range(req_count)
    ]

    # Send all 100 events concurrently
    await asyncio.gather(*(kernel.send_event(evt) for evt in events))

    # Wait briefly for async event bus queue processing
    await asyncio.sleep(0.5)

    assert len(receiver.received_events) == req_count, f"Expected {req_count} response events, got {len(receiver.received_events)}"

    for resp_evt in receiver.received_events:
        assert resp_evt.event_type == "model.execution_complete"
        assert resp_evt.source == "model_router"
        assert resp_evt.destination == "test_scheduler"
        payload = resp_evt.payload
        assert "task_id" in payload
        assert "result" in payload
        res = payload["result"]
        assert res["status"] == "success"
        assert res["executed_by"] in ("Gemini Flash", "OpenRouter", "Antigravity CLI")
        assert res["tokens"]["total_tokens"] > 0
        assert res["cost"] >= 0.0

    # Verify CostTracker accumulated all 100 requests
    summary = router.cost_tracker.get_summary()
    assert summary["request_count"] == req_count
