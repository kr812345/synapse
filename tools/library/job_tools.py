"""Tools Pip uses to list and add jobs."""

from __future__ import annotations

from typing import Any, Optional

from scheduler.jobs import DEFAULT_TZ, JobStore
from tools.tool_registry import ToolInterface


class JobsList(ToolInterface):
    name = "jobs_list"
    description = "List alarms, cron jobs, and other triggers."
    parameters = {"type": "object", "properties": {}}
    required_permissions = ["jobs"]

    def __init__(self, store: Optional[JobStore] = None):
        self.store = store

    def _store(self) -> JobStore:
        return self.store or JobStore()

    async def execute(self, **kwargs) -> Any:
        store = self._store()
        try:
            return {"status": "ok", "jobs": store.list_jobs()}
        finally:
            if self.store is None:
                store.close()


class JobsCreate(ToolInterface):
    name = "jobs_create"
    description = "Create an alarm or a cron job. Times use Asia/Kolkata unless timezone is set."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "kind": {"type": "string"},
            "schedule": {"type": "string"},
            "payload": {"type": "object"},
            "timezone": {"type": "string"},
            "quiet_start": {"type": "string"},
            "quiet_end": {"type": "string"},
        },
        "required": ["name", "kind"],
    }
    required_permissions = ["jobs"]

    def __init__(self, store: Optional[JobStore] = None):
        self.store = store

    async def execute(
        self,
        name: str = "",
        kind: str = "",
        schedule: str = "",
        payload: Optional[dict] = None,
        timezone: str = DEFAULT_TZ,
        quiet_start: str = "",
        quiet_end: str = "",
        **kwargs,
    ) -> Any:
        if kind not in {"alarm", "cron", "webhook", "file"}:
            return {"status": "error", "message": "kind must be alarm, cron, webhook, or file"}
        store = self.store or JobStore()
        try:
            job = store.upsert(
                name=name,
                kind=kind,
                schedule=schedule,
                payload=payload or {},
                timezone_name=timezone or DEFAULT_TZ,
                quiet_start=quiet_start or None,
                quiet_end=quiet_end or None,
            )
            return {"status": "ok", "job": job}
        finally:
            if self.store is None:
                store.close()
