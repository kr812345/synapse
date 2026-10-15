import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from shared.interfaces import Module
from shared.models import Event
from models.cost_tracker import CostTracker
from models.adapters.base import BaseModelAdapter, ModelAdapter, ModelAdapterError
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from models.adapters.antigravity import AntigravityAdapter

logger = logging.getLogger(__name__)


class ModelRouter(Module):
    """Multi-tier LLM Model Router with heuristic selection, automatic fallback, SSE streaming, and cost tracking."""

    def __init__(self, adapters: Optional[List[ModelAdapter]] = None):
        self.kernel = None
        self.cost_tracker = CostTracker()

        if adapters:
            self._adapter_list = adapters
        else:
            self._adapter_list = [
                GeminiFlashAdapter(),
                OpenRouterAdapter(),
                AntigravityAdapter(),
            ]

        self._tier_map: Dict[str, ModelAdapter] = {}
        self._name_map: Dict[str, ModelAdapter] = {}
        for adapter in self._adapter_list:
            self._tier_map[adapter.tier] = adapter
            self._name_map[adapter.name.lower()] = adapter
            self._name_map[adapter.model_id.lower()] = adapter

    @property
    def name(self) -> str:
        return "model_router"

    def set_kernel(self, kernel: Any) -> None:
        self.kernel = kernel

    def register_adapter(self, name: str, adapter: BaseModelAdapter) -> None:
        """Register or override an adapter by name."""
        self._name_map[name.lower()] = adapter  # type: ignore[assignment]
        if hasattr(adapter, "tier"):
            self._tier_map[getattr(adapter, "tier")] = adapter  # type: ignore[assignment]
        if adapter not in self._adapter_list:
            self._adapter_list.append(adapter)  # type: ignore[arg-type]

    def decide_model(self, task_description: Optional[str], payload: Optional[Dict[str, Any]] = None) -> ModelAdapter:
        """Determine appropriate ModelAdapter based on explicit hints, keyword heuristics, or prompt length."""
        payload = payload or {}
        if task_description is None or not isinstance(task_description, str):
            task_description = ""

        # 1. Check explicit hints in payload
        explicit_hint = (
            payload.get("tier")
            or payload.get("model_hint")
            or payload.get("model")
            or payload.get("preferred_tier")
        )
        if explicit_hint and isinstance(explicit_hint, str):
            hint_lower = explicit_hint.lower()
            if hint_lower in self._tier_map:
                return self._tier_map[hint_lower]
            if hint_lower in self._name_map:
                return self._name_map[hint_lower]
            if "gemini" in hint_lower or "tier1" in hint_lower:
                return self._tier_map.get("tier1", self._adapter_list[0])
            if "openrouter" in hint_lower or "tier2" in hint_lower:
                return self._tier_map.get("tier2", self._adapter_list[1])
            if "antigravity" in hint_lower or "tier3" in hint_lower:
                return self._tier_map.get("tier3", self._adapter_list[-1])

        # 2. Check keyword heuristics in task description
        desc_lower = task_description.lower()
        tier3_keywords = [
            "architecture", "design", "refactor", "security audit",
            "optimization", "deep research", "root cause", "complex task",
        ]
        tier2_keywords = [
            "code", "feature", "implement", "unit test",
            "data model", "department", "search",
        ]
        tier1_keywords = [
            "summary", "format", "ping", "echo", "log", "simple", "classify",
        ]

        if any(kw in desc_lower for kw in tier3_keywords) and "tier3" in self._tier_map:
            return self._tier_map["tier3"]
        if any(kw in desc_lower for kw in tier1_keywords) and "tier1" in self._tier_map:
            return self._tier_map["tier1"]
        if any(kw in desc_lower for kw in tier2_keywords) and "tier2" in self._tier_map:
            return self._tier_map["tier2"]

        # 3. Prompt word count fallback heuristics
        words = len(task_description.split())
        if words < 10 and "tier1" in self._tier_map:
            return self._tier_map["tier1"]
        elif words < 50 and "tier2" in self._tier_map:
            return self._tier_map["tier2"]
        elif "tier3" in self._tier_map:
            return self._tier_map["tier3"]

        return self._adapter_list[0]

    def _resolve_primary(
        self,
        prompt: str,
        preferred_adapter: Optional[Union[BaseModelAdapter, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> BaseModelAdapter:
        if isinstance(preferred_adapter, BaseModelAdapter):
            return preferred_adapter
        if isinstance(preferred_adapter, str):
            pref_lower = preferred_adapter.lower()
            found = self._tier_map.get(pref_lower) or self._name_map.get(pref_lower)
            if found:
                return found
        return self.decide_model(prompt, payload)

    def _get_fallback_chain(self, primary: BaseModelAdapter) -> List[BaseModelAdapter]:
        """Construct ordered fallback chain starting with primary adapter."""
        chain: List[BaseModelAdapter] = [primary]
        for adapter in self._adapter_list:
            if adapter not in chain:
                chain.append(adapter)
        return chain

    async def generate_with_fallback(
        self,
        prompt: str,
        system: Optional[str] = None,
        preferred_adapter: Optional[Union[BaseModelAdapter, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute model generation with automatic multi-tier fallback redundancy."""
        primary = self._resolve_primary(prompt, preferred_adapter, kwargs.get("payload"))
        fallback_chain = self._get_fallback_chain(primary)
        last_exception: Optional[Exception] = None

        for adapter in fallback_chain:
            try:
                adapter_name = getattr(adapter, "name", adapter.__class__.__name__)
                adapter_tier = getattr(adapter, "tier", "custom")
                logger.info(f"Attempting model execution via {adapter_name} ({adapter_tier})")
                res = await adapter.generate(prompt, system=system, **kwargs)
                if isinstance(res, dict):
                    return res
                return {
                    "output": str(res),
                    "model_name": adapter_name,
                    "tier": adapter_tier,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                    "raw_response": None,
                }
            except Exception as exc:
                adapter_name = getattr(adapter, "name", adapter.__class__.__name__)
                logger.warning(f"Model adapter {adapter_name} failed ({exc}). Cascading to next fallback adapter...")
                last_exception = exc

        logger.error("All model adapters in fallback chain failed.")
        raise RuntimeError(f"All model adapters failed to execute prompt. Last error: {last_exception}") from last_exception

    async def stream_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        preferred_adapter: Optional[Union[BaseModelAdapter, str]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream tokens from the preferred adapter, cascading through fallbacks on error."""
        primary = self._resolve_primary(prompt, preferred_adapter, kwargs.get("payload"))
        fallback_chain = self._get_fallback_chain(primary)
        last_exception: Optional[Exception] = None

        for adapter in fallback_chain:
            try:
                adapter_name = getattr(adapter, "name", adapter.__class__.__name__)
                logger.info(f"Streaming model execution via {adapter_name}")
                async for token in adapter.stream_generate(prompt, system=system, **kwargs):
                    yield token
                return
            except Exception as exc:
                adapter_name = getattr(adapter, "name", adapter.__class__.__name__)
                logger.warning(f"Streaming adapter {adapter_name} failed ({exc}). Trying next fallback...")
                last_exception = exc

        logger.error("All streaming model adapters in fallback chain failed.")
        raise RuntimeError(f"All streaming model adapters failed. Last error: {last_exception}") from last_exception

    async def handle_event(self, event: Event) -> None:
        """Handle incoming Event Bus events for model execution requests."""
        if event.event_type == "model.request_execution":
            task_id = event.payload.get("task_id")
            task_description = event.payload.get("task_description") or ""
            system = (
                event.payload.get("system")
                or "You are an autonomous AI Agent in Synapse OS. If you lack specific web search tools, use your vast internal knowledge base to write high-quality research articles and fulfill requests. Always use your available tool integrations (like PDF generator or Email) when the user asks for a document or an email delivery."
            )
            agent = event.payload.get("agent", {})
            agent_id = agent.get("identity") if isinstance(agent, dict) else (str(agent) if agent else "unknown")

            primary_adapter = self.decide_model(task_description, event.payload)
            logger.info(f"Model Router selected {primary_adapter.name} for task {task_id}")

            try:
                exec_output = await self.generate_with_fallback(
                    prompt=task_description,
                    system=system,
                    preferred_adapter=primary_adapter,
                    payload=event.payload,
                )

                self.cost_tracker.record_usage(
                    task_id=task_id,
                    agent=agent_id,
                    model_name=exec_output["model_name"],
                    tier=exec_output["tier"],
                    prompt_tokens=exec_output["prompt_tokens"],
                    completion_tokens=exec_output["completion_tokens"],
                    cost_usd=exec_output["cost_usd"],
                )

                result = {
                    "status": "success",
                    "executed_by": exec_output["model_name"],
                    "agent": agent_id,
                    "output": exec_output["output"],
                    "tokens": {
                        "prompt_tokens": exec_output["prompt_tokens"],
                        "completion_tokens": exec_output["completion_tokens"],
                        "total_tokens": exec_output["total_tokens"],
                    },
                    "cost": exec_output["cost_usd"],
                }

            except Exception as err:
                logger.error(f"Model router execution failed for task {task_id}: {err}")
                result = {
                    "status": "error",
                    "executed_by": primary_adapter.name,
                    "agent": agent_id,
                    "output": f"Execution failed: {err}",
                    "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "cost": 0.0,
                }

            if self.kernel:
                resp = Event(
                    source=self.name,
                    destination=event.source,
                    event_type="model.execution_complete",
                    payload={"task_id": task_id, "result": result},
                )
                await self.kernel.send_event(resp)
