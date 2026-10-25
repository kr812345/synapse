"""Subscription CLIs and API-key adapters Pip can switch to."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from models.adapters.base import (
    AuthenticationError,
    ModelAdapter,
    ModelAdapterError,
    ProviderUnavailableError,
)
from vault.store import runtime_secret


class _CliAdapter(ModelAdapter):
    binary_name = ""
    display_name = ""
    id_name = ""
    tier_name = "cli"

    def __init__(self, binary_path: Optional[str] = None):
        self._binary_path = binary_path

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def model_id(self) -> str:
        return self.id_name

    @property
    def tier(self) -> str:
        return self.tier_name

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.0

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.0

    def binary(self) -> Optional[str]:
        if self._binary_path and os.path.exists(self._binary_path):
            return self._binary_path
        return shutil.which(self.binary_name)

    def installed(self) -> bool:
        return self.binary() is not None

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        binary = self.binary()
        if not binary:
            raise ProviderUnavailableError(f"{self.display_name} is not installed")
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--prompt",
            full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            raise ProviderUnavailableError(f"{self.display_name} timed out")
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise ModelAdapterError(f"{self.display_name} failed: {err}")
        output = stdout.decode("utf-8", errors="replace").strip()
        prompt_tokens = self.estimate_tokens(full_prompt)
        completion_tokens = self.estimate_tokens(output)
        return {
            "output": output,
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": 0.0,
            "raw_response": None,
        }


class ClaudeCodeAdapter(_CliAdapter):
    binary_name = "claude"
    display_name = "Claude Code"
    id_name = "claude-code"
    tier_name = "cli-claude"


class CursorCliAdapter(_CliAdapter):
    binary_name = "cursor-agent"
    display_name = "Cursor CLI"
    id_name = "cursor-cli"
    tier_name = "cli-cursor"


class _ApiKeyAdapter(ModelAdapter):
    secret_name = ""
    display_name = ""
    id_name = ""
    tier_name = "api"

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def model_id(self) -> str:
        return self.id_name

    @property
    def tier(self) -> str:
        return self.tier_name

    @property
    def cost_per_1k_prompt(self) -> float:
        return 0.003

    @property
    def cost_per_1k_completion(self) -> float:
        return 0.015

    def installed(self) -> bool:
        return bool(runtime_secret(self.secret_name))

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        key = runtime_secret(self.secret_name)
        if not key:
            raise AuthenticationError(f"{self.display_name} has no API key in the vault")
        try:
            output = await asyncio.to_thread(self._call, key, prompt, system)
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        prompt_tokens = self.estimate_tokens(prompt) + self.estimate_tokens(system)
        completion_tokens = self.estimate_tokens(output)
        return {
            "output": output,
            "model_name": self.name,
            "tier": self.tier,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": self.calculate_cost(prompt_tokens, completion_tokens),
            "raw_response": None,
        }

    def _call(self, key: str, prompt: str, system: Optional[str]) -> str:
        raise NotImplementedError


class AnthropicApiAdapter(_ApiKeyAdapter):
    secret_name = "ANTHROPIC_API_KEY"
    display_name = "Anthropic API"
    id_name = "anthropic-api"
    tier_name = "api-anthropic"

    def _call(self, key: str, prompt: str, system: Optional[str]) -> str:
        body: Dict[str, Any] = {
            "model": os.environ.get("PIP_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parts = payload.get("content") or []
        return "".join(part.get("text", "") for part in parts if isinstance(part, dict))


class OpenAIApiAdapter(_ApiKeyAdapter):
    secret_name = "OPENAI_API_KEY"
    display_name = "OpenAI API"
    id_name = "openai-api"
    tier_name = "api-openai"

    def _call(self, key: str, prompt: str, system: Optional[str]) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": os.environ.get("PIP_OPENAI_MODEL", "gpt-4o-mini"),
            "messages": messages,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {key}",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
