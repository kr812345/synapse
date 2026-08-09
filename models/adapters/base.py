from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

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


class ModelAdapter(ABC):
    """Abstract Base Class for model execution adapters."""

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

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Generate output from the model provider given a prompt and optional system context.

        Returns:
            dict with structure:
            {
                "output": str,
                "model_name": str,
                "tier": str,
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
                "cost_usd": float,
                "raw_response": dict | None
            }
        """
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
