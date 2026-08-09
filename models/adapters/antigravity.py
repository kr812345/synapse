import os
import shutil
import asyncio
import logging
from typing import Any, Dict, Optional

from models.adapters.base import (
    ModelAdapter,
    ModelAdapterError,
    RateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class AntigravityAdapter(ModelAdapter):
    """Tier 3 Adapter: Antigravity CLI for deep reasoning, complex design, and architecture."""

    def __init__(self, binary_path: Optional[str] = None):
        self._binary_path = binary_path or shutil.which("agy")

    @property
    def name(self) -> str:
        return "Antigravity CLI"

    @property
    def model_id(self) -> str:
        return "antigravity-cli"

    @property
    def tier(self) -> str:
        return "tier3"

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.0050

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.0250

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Generate response via Antigravity CLI process execution or deterministic local engine."""
        binary = kwargs.get("binary_path") or self._binary_path
        use_cli = kwargs.get("use_cli") or (os.environ.get("USE_ANTIGRAVITY_CLI", "").lower() in ("true", "1"))

        if use_cli and binary and os.path.exists(binary):
            try:
                full_prompt = f"System: {system}\nPrompt: {prompt}" if system else prompt
                proc = await asyncio.create_subprocess_exec(
                    binary,
                    "--prompt",
                    full_prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    raise ProviderUnavailableError("Antigravity CLI execution timed out")

                if proc.returncode != 0:
                    err_msg = stderr.decode("utf-8", errors="replace").strip()
                    if "rate limit" in err_msg.lower():
                        raise RateLimitError(f"Antigravity CLI rate limit exceeded: {err_msg}")
                    raise ModelAdapterError(f"Antigravity CLI failed with code {proc.returncode}: {err_msg}")

                output_text = stdout.decode("utf-8", errors="replace").strip()
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
                    "raw_response": {"provider": "antigravity", "mode": "cli", "returncode": proc.returncode},
                }
            except (RateLimitError, ProviderUnavailableError, ModelAdapterError):
                raise
            except Exception as e:
                logger.warning(f"Antigravity CLI execution failed ({e}), using fallback simulation engine.")

        # Local deterministic execution engine
        sys_prefix = f"[{system}] " if system else ""
        output_text = f"Antigravity CLI deep architecture response for: {sys_prefix}{prompt}"

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
            "raw_response": {"provider": "antigravity", "mode": "simulation", "model": self.model_id},
        }
