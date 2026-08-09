import logging
from typing import Any, Dict, List, Optional, Union

from shared.interfaces import Module
from shared.models import Event
from models.cost_tracker import CostTracker
from models.adapters.base import ModelAdapter, ModelAdapterError
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from models.adapters.antigravity import AntigravityAdapter

logger = logging.getLogger(__name__)


class ModelRouter(Module):
    """Multi-tier LLM Model Router with heuristic selection, automatic fallback, and cost tracking."""

    def __init__(self, adapters: Optional[List[ModelAdapter]] = None):
        self.kernel = None
        self.cost_tracker = CostTracker()

        # Default adapter suite
        if adapters:
            self._adapter_list = adapters
        else:
            self._adapter_list = [
                GeminiFlashAdapter(),
                OpenRouterAdapter(),
                AntigravityAdapter(),
            ]

        # Index adapters by tier and display name / key
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
            "optimization", "deep research", "root cause", "complex task"
        ]
        tier2_keywords = [
            "code", "feature", "implement", "unit test",
            "data model", "department", "search"
        ]
        tier1_keywords = [
            "summary", "format", "ping", "echo", "log", "simple", "classify"
        ]

        if any(kw in desc_lower for kw in tier3_keywords) and "tier3" in self._tier_map:
            return self._tier_map["tier3"]
        if any(kw in desc_lower for kw in tier1_keywords) and "tier1" in self._tier_map:
            return self._tier_map["tier1"]
        if any(kw in desc_lower for kw in tier2_keywords) and "tier2" in self._tier_map:
            return self._tier_map["tier2"]

        # 3. Prompt word count fallback heuristics (backward compatibility)
        words = len(task_description.split())
        if words < 10 and "tier1" in self._tier_map:
            return self._tier_map["tier1"]
        elif words < 50 and "tier2" in self._tier_map:
            return self._tier_map["tier2"]
        elif "tier3" in self._tier_map:
            return self._tier_map["tier3"]

        return self._adapter_list[0]

    def _get_fallback_chain(self, primary: ModelAdapter) -> List[ModelAdapter]:
        """Construct ordered fallback chain starting with primary adapter."""
        chain = [primary]
        for adapter in self._adapter_list:
            if adapter not in chain:
                chain.append(adapter)
        return chain

    async def generate_with_fallback(
        self,
        prompt: str,
        system: Optional[str] = None,
        preferred_adapter: Optional[Union[ModelAdapter, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute model generation with automatic multi-tier fallback redundancy."""
        primary: Optional[ModelAdapter] = None

        if isinstance(preferred_adapter, ModelAdapter):
            primary = preferred_adapter
        elif isinstance(preferred_adapter, str):
            pref_lower = preferred_adapter.lower()
            primary = self._tier_map.get(pref_lower) or self._name_map.get(pref_lower)

        if not primary:
            primary = self.decide_model(prompt, kwargs.get("payload"))

        fallback_chain = self._get_fallback_chain(primary)
        last_exception: Optional[Exception] = None

        for adapter in fallback_chain:
            try:
                logger.info(f"Attempting model execution via {adapter.name} ({adapter.tier})")
                res = await adapter.generate(prompt, system=system, **kwargs)
                return res
            except Exception as exc:
                logger.warning(f"Model adapter {adapter.name} failed ({exc}). Cascading to next fallback adapter...")
                last_exception = exc

        logger.error("All model adapters in fallback chain failed.")
        raise RuntimeError(f"All model adapters failed to execute prompt. Last error: {last_exception}") from last_exception

    async def handle_event(self, event: Event) -> None:
        """Handle incoming Event Bus events for model execution requests."""
        if event.event_type == "model.request_execution":
            task_id = event.payload.get("task_id")
            task_description = event.payload.get("task_description") or ""
            system = event.payload.get("system")
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

                # Record metrics in cost tracker
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
