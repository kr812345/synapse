"""In-process view over approvals stored in the vault file."""

from __future__ import annotations

import asyncio
from typing import Optional

from vault.store import VaultStore


class ApprovalGate:
    def __init__(self, store: Optional[VaultStore] = None):
        self.store = store or VaultStore()

    def request(self, action: str, secret: str, detail: str) -> dict:
        return self.store.request_approval(action, secret, detail)

    def resolve(self, approval_id: str, allow: bool) -> dict:
        return self.store.resolve_approval(approval_id, allow)

    def pending(self) -> list[dict]:
        return self.store.pending_approvals()

    async def wait(self, approval_id: str, timeout: float = 120.0) -> bool:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            record = self.store.get_approval(approval_id)
            if record and record.get("status") == "allowed":
                return True
            if record and record.get("status") == "refused":
                return False
            await asyncio.sleep(0.05)
        return False
