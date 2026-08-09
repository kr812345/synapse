"""Model adapters package for LLM provider integrations."""
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

__all__ = [
    "ModelAdapter",
    "ModelAdapterError",
    "RateLimitError",
    "ProviderUnavailableError",
    "AuthenticationError",
    "GeminiFlashAdapter",
    "OpenRouterAdapter",
    "AntigravityAdapter",
]
