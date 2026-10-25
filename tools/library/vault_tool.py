"""Vault tools. They return names and statuses, never secret values."""

from __future__ import annotations

from typing import Any, Optional

from tools.tool_registry import ToolInterface
from vault.store import VaultError, VaultStore


class VaultPut(ToolInterface):
    name = "vault_put"
    description = "Store a secret by name. The value is not echoed back."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["name", "value"],
    }
    required_permissions = ["vault"]

    def __init__(self, store: Optional[VaultStore] = None):
        self.store = store or VaultStore()

    async def execute(self, name: str = "", value: str = "", **kwargs) -> Any:
        try:
            self.store.put(name, value)
        except VaultError as exc:
            return {"status": "error", "message": str(exc)}
        return {"status": "ok", "name": name}


class VaultList(ToolInterface):
    name = "vault_list"
    description = "List secret names stored in the vault."
    parameters = {"type": "object", "properties": {}}
    required_permissions = ["vault"]

    def __init__(self, store: Optional[VaultStore] = None):
        self.store = store or VaultStore()

    async def execute(self, **kwargs) -> Any:
        return {"status": "ok", "names": self.store.list_names()}
