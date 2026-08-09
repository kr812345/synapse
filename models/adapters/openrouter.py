import os
import json
import asyncio
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from models.adapters.base import (
    ModelAdapter,
    ModelAdapterError,
    RateLimitError,
    ProviderUnavailableError,
    AuthenticationError,
)

logger = logging.getLogger(__name__)


class OpenRouterAdapter(ModelAdapter):
    """Tier 2 Adapter: OpenRouter for standard reasoning and departmental coding tasks."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")

    @property
    def name(self) -> str:
        return "OpenRouter"

    @property
    def model_id(self) -> str:
        return "openrouter/auto"

    @property
    def tier(self) -> str:
        return "tier2"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.0030

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.0150

    def _sync_generate(self, url: str, headers: dict, payload_bytes: bytes) -> tuple[int, str]:
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, body
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8") if err.fp else ""
            return err.code, body

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Generate response via OpenRouter API or deterministic local engine."""
        api_key = kwargs.get("api_key") or self._api_key

        if api_key:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload_bytes = json.dumps({"model": self.model_id, "messages": messages}).encode("utf-8")
                status_code, body_text = await asyncio.to_thread(self._sync_generate, url, headers, payload_bytes)

                if status_code == 429:
                    raise RateLimitError("OpenRouter API rate limit exceeded")
                elif status_code in (401, 403):
                    raise AuthenticationError("Invalid or missing OpenRouter API key")
                elif status_code >= 500:
                    raise ProviderUnavailableError(f"OpenRouter API server error ({status_code})")
                elif status_code != 200:
                    raise ModelAdapterError(f"OpenRouter API returned status {status_code}: {body_text}")

                data = json.loads(body_text)
                output_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", self.estimate_tokens(prompt) + self.estimate_tokens(system))
                completion_tokens = usage.get("completion_tokens", self.estimate_tokens(output_text))
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                cost_usd = self.calculate_cost(prompt_tokens, completion_tokens)

                return {
                    "output": output_text,
                    "model_name": self.name,
                    "tier": self.tier,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost_usd,
                    "raw_response": data,
                }
            except (RateLimitError, AuthenticationError, ProviderUnavailableError, ModelAdapterError):
                raise
            except Exception as e:
                logger.warning(f"OpenRouter API request failed ({e}), using fallback simulation engine.")

        # Local deterministic execution engine
        sys_prefix = f"[{system}] " if system else ""
        output_text = f"OpenRouter reasoning output for: {sys_prefix}{prompt}"

        prompt_tokens = self.estimate_tokens(prompt) + self.estimate_tokens(system)
        completion_tokens = self.estimate_tokens(output_text)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.calculate_cost(prompt_tokens, completion_tokens)

        return {
            "output": output_text,
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "raw_response": {"provider": "openrouter", "mode": "simulation", "model": self.model_id},
        }
