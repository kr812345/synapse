"""Built-in model list, switch, and install tools."""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Optional

from models.installers import INSTALLERS
from models.selection import read_default, write_default
from tools.tool_registry import ToolInterface
from vault.approvals import ApprovalGate
from vault.store import VaultStore, runtime_secret


def _cli_installed(binary: str) -> bool:
    return shutil.which(binary) is not None


def describe_models() -> list[dict]:
    rows = [
        {
            "id": "gemini-2.5-flash",
            "label": "Gemini Flash",
            "installed": True,
            "kind": "api",
        },
        {
            "id": "openrouter/auto",
            "label": "OpenRouter",
            "installed": bool(runtime_secret("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")),
            "kind": "api",
        },
        {
            "id": "anthropic-api",
            "label": "Anthropic API",
            "installed": bool(runtime_secret("ANTHROPIC_API_KEY")),
            "kind": "api",
        },
        {
            "id": "openai-api",
            "label": "OpenAI API",
            "installed": bool(runtime_secret("OPENAI_API_KEY")),
            "kind": "api",
        },
    ]
    installer_ids = {
        "claude-code": "claude-code",
        "cursor-cli": "cursor-cli",
        "antigravity": "antigravity-cli",
    }
    for key, spec in INSTALLERS.items():
        binary = spec["binary"]
        rows.append(
            {
                "id": installer_ids.get(key, key),
                "label": spec["label"],
                "installed": _cli_installed(binary),
                "kind": "cli",
                "installer": key,
            }
        )
    current = read_default()
    for row in rows:
        row["selected"] = row["id"] == current
    return rows


class ModelsList(ToolInterface):
    name = "models_list"
    description = "List models and CLIs Pip can use, and which one is the saved default."
    parameters = {"type": "object", "properties": {}}
    required_permissions = ["models"]

    async def execute(self, **kwargs) -> Any:
        return {"status": "ok", "default": read_default(), "models": describe_models()}


class ModelsUse(ToolInterface):
    name = "models_use"
    description = "Switch the saved default model. The router reads it on the next call."
    parameters = {"type": "object", "properties": {"model": {"type": "string"}}, "required": ["model"]}
    required_permissions = ["models"]

    async def execute(self, model: str = "", **kwargs) -> Any:
        wanted = (model or "").strip()
        if not wanted:
            return {"status": "error", "message": "model is required"}
        known = {row["id"]: row for row in describe_models()}
        # Also accept display labels and installer keys already in the id map.
        match = known.get(wanted) or next((row for row in known.values() if row["label"].lower() == wanted.lower()), None)
        if not match:
            return {"status": "error", "message": f"unknown model {wanted}"}
        if not match["installed"]:
            return {"status": "error", "message": f"{match['label']} is not installed"}
        write_default(match["id"])
        return {"status": "ok", "default": match["id"], "announced": f"Pip will use {match['label']} next."}


class ModelsInstall(ToolInterface):
    name = "models_install"
    description = "Install an allowlisted CLI after approval."
    parameters = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    required_permissions = ["models"]

    def __init__(self, runner=None, store: Optional[VaultStore] = None):
        self.runner = runner or _run_argv
        self.store = store or VaultStore()
        self.gate = ApprovalGate(self.store)

    async def execute(self, name: str = "", **kwargs) -> Any:
        aliases = {"antigravity-cli": "antigravity"}
        spec = INSTALLERS.get(aliases.get(name, name))
        if not spec:
            return {"status": "error", "message": "that CLI is not on the allowlist"}
        if spec.get("argv") is None:
            return {"status": "error", "message": spec.get("note", "install is not available")}
        record = self.gate.request("install-cli", name, f"install {spec['label']}")
        allowed = await self.gate.wait(record["id"], timeout=float(os.environ.get("PIP_APPROVAL_TIMEOUT", "120")))
        if not allowed:
            return {"status": "refused", "approval_id": record["id"], "name": name}
        code, output = await self.runner(spec["argv"])
        return {
            "status": "ok" if code == 0 else "error",
            "approval_id": record["id"],
            "name": name,
            "exit_code": code,
            "output": output[-500:],
        }


async def _run_argv(argv: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _stderr = await proc.communicate()
    text = stdout.decode("utf-8", errors="replace") if stdout else ""
    return proc.returncode or 0, text
