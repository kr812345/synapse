import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

logger = logging.getLogger(__name__)


class ModelAdapterError(Exception):
    """Base exception for model adapter errors."""
    pass


class RateLimitError(ModelAdapterError):
    """Exception raised when API rate limit or quota is exceeded."""
    pass


class ProviderUnavailableError(ModelAdapterError):
    """Exception raised when model provider API is unavailable (5xx, network failure)."""
    pass


class AuthenticationError(ModelAdapterError):
    """Exception raised when authentication fails (missing/invalid API key)."""
    pass


class BaseModelAdapter(ABC):
    """Base interface for all LLM Adapters (Gemini, OpenRouter, Antigravity Bridge)."""

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Any:
        """Generate a response from the model."""
        pass

    async def stream_generate(
        self, prompt: str, system: Optional[str] = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Stream response tokens from the model.
        Default implementation chunks the full response from `generate()`.
        Subclasses with native SSE streaming should override this method.
        """
        result = await self.generate(prompt, system=system, **kwargs)
        full_text = result.get("output", "") if isinstance(result, dict) else str(result)
        words = full_text.split(" ")
        for idx, word in enumerate(words):
            token = word if idx == len(words) - 1 else word + " "
            if token:
                await asyncio.sleep(0.02)
                yield token


class ModelAdapter(BaseModelAdapter):
    """Abstract Base Class for model execution adapters with cost/token metadata."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the model adapter (e.g., 'Gemini Flash')."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Provider model identifier string (e.g., 'gemini-2.5-flash')."""
        pass

    @property
    @abstractmethod
    def tier(self) -> str:
        """Tier string identifier ('tier1', 'tier2', 'tier3')."""
        pass

    @property
    @abstractmethod
    def cost_per_1k_prompt(self) -> float:
        """Cost in USD per 1,000 prompt tokens."""
        pass

    @property
    @abstractmethod
    def cost_per_1k_completion(self) -> float:
        """Cost in USD per 1,000 completion tokens."""
        pass

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate total cost in USD for given prompt and completion token counts."""
        prompt_cost = (prompt_tokens / 1000.0) * self.cost_per_1k_prompt
        completion_cost = (completion_tokens / 1000.0) * self.cost_per_1k_completion
        return round(prompt_cost + completion_cost, 6)

    def estimate_tokens(self, text: Optional[str]) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' model_id='{self.model_id}' tier='{self.tier}'>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other in (self.name, self.model_id, self.tier)
        if isinstance(other, ModelAdapter):
            return self.model_id == other.model_id and self.tier == other.tier
        return False
