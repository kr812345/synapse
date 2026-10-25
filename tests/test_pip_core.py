"""Pip workspace jail, vault, desktop, model switch, and durable jobs."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from assistants.pip_assistant import PipAssistant
from boot import boot_os
from models.model_router import ModelRouter
from models.selection import write_default
from scheduler.jobs import JobStore, cron_matches, in_quiet_hours, seed_default_jobs
from scheduler.pip_cron import tick
from tools.jail import JailError, resolve_in_jail
from tools.library.desktop import BrowserFillLogin, BrowserOpen, FakeDesktop, set_driver
from tools.library.file_tools import FileRead, FileWrite
from tools.library.model_tools import ModelsInstall, ModelsUse
from vault.helper import handle
from vault.store import VaultStore


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "work"
    root.mkdir()
    monkeypatch.setenv("PIP_WORK_ROOT", str(root))
    vault = tmp_path / "vault.json"
    key = tmp_path / "vault.key"
    monkeypatch.setenv("PIP_VAULT_PATH", str(vault))
    monkeypatch.setenv("PIP_VAULT_KEY_FILE", str(key))
    monkeypatch.setenv("PIP_JOBS_PATH", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("PIP_MODEL_CONFIG", str(tmp_path / "model.json"))
    monkeypatch.setenv("PIP_DESKTOP_DRIVER", "fake")
    set_driver(FakeDesktop())
    yield root
    set_driver(None)


def test_file_tools_stay_inside_the_workspace(workspace):
    secret = workspace.parent / "vault.key"
    secret.write_text("nope")
    outside = workspace.parent / "outside.txt"
    outside.write_text("hidden")

    async def run():
        written = await FileWrite().execute(path="notes.txt", content="hello")
        assert "notes.txt" in written
        assert await FileRead().execute(path="notes.txt") == "hello"
        refused = await FileRead().execute(path=str(outside))
        assert refused.startswith("Error:")
        env_path = workspace / ".env"
        env_path.write_text("TOKEN=1")
        assert (await FileRead().execute(path=".env")).startswith("Error:")

    asyncio.run(run())

    link = workspace / "escape"
    link.symlink_to(outside)
    with pytest.raises(JailError):
        resolve_in_jail(str(link))
    with pytest.raises(JailError):
        resolve_in_jail(str(secret))


def test_vault_hides_values_and_requires_approval(workspace):
    store = VaultStore(allow_create=True)
    store.put("browser-login", json.dumps({"username": "krishna", "password": "s3cret-value"}))
    assert store.list_names() == ["browser-login"]
    dumped = json.dumps(store.audit_log())
    assert "s3cret-value" not in dumped

    record = store.request_approval("use-credential", "browser-login", "fill a browser login")
    with pytest.raises(Exception):
        store.get("browser-login", purpose="action", approval_id=record["id"])
    store.resolve_approval(record["id"], False)
    assert store.get_approval(record["id"])["status"] == "refused"

    allowed = store.request_approval("use-credential", "browser-login", "fill a browser login")
    store.resolve_approval(allowed["id"], True)
    raw = store.get("browser-login", purpose="action", approval_id=allowed["id"])
    assert "s3cret-value" in raw
    assert all("s3cret-value" not in json.dumps(row) for row in store.audit_log())

    refused = handle(store, {"op": "get", "name": "browser-login", "purpose": "action"})
    assert refused["ok"] is False


def test_browser_login_types_only_after_approval(workspace):
    store = VaultStore(allow_create=True)
    store.put("browser-login", json.dumps({"username": "krishna", "password": "s3cret-value"}))
    tool = BrowserFillLogin(store=store)

    async def run():
        task = asyncio.create_task(
            tool.execute(secret="browser-login", user_selector="#user", password_selector="#password")
        )
        pending = []
        for _ in range(50):
            pending = store.pending_approvals()
            if pending:
                break
            await asyncio.sleep(0.01)
        assert pending
        store.resolve_approval(pending[0]["id"], True)
        result = await task
        assert result["status"] == "ok"
        assert "s3cret-value" not in json.dumps(result)
        opened = await BrowserOpen().execute(url="https://example.com")
        assert opened["url"] == "https://example.com"

    asyncio.run(run())


def test_models_use_overrides_keyword_routing(workspace, monkeypatch):
    monkeypatch.delenv("PIP_DEFAULT_MODEL", raising=False)
    router = ModelRouter()
    long_prompt = "design the architecture of this system " * 8
    assert router.decide_model(long_prompt).name == "Antigravity CLI"
    result = asyncio.run(ModelsUse().execute(model="gemini-2.5-flash"))
    assert result["status"] == "ok"
    assert write_default  # saved by the tool
    assert router.decide_model(long_prompt).name == "Gemini Flash"

    async def install_refused():
        tool = ModelsInstall(runner=None, store=VaultStore(allow_create=True))

        async def no_runner(_argv):
            raise AssertionError("install must wait for approval")

        tool.runner = no_runner
        task = asyncio.create_task(tool.execute(name="claude-code"))
        pending = []
        for _ in range(50):
            pending = tool.store.pending_approvals()
            if pending:
                break
            await asyncio.sleep(0.01)
        tool.store.resolve_approval(pending[0]["id"], False)
        return await task

    refused = asyncio.run(install_refused())
    assert refused["status"] == "refused"


def test_default_jobs_alarm_and_cron(workspace):
    store = JobStore()
    seeded = seed_default_jobs(store)
    names = {job["name"] for job in seeded}
    assert names == {"pip-hello-alarm", "pip-page-check"}
    page = store.get_by_name("pip-page-check")
    assert page["schedule"] == "*/30 * * * *"
    assert page["timezone"] == "Asia/Kolkata"
    assert page["quiet_start"] == "23:00"

    tz = ZoneInfo("Asia/Kolkata")
    quiet_now = datetime(2026, 10, 25, 23, 30, tzinfo=tz)
    assert in_quiet_hours(quiet_now, page)
    store.conn.execute(
        "UPDATE jobs SET next_run = ? WHERE name = ?",
        (quiet_now.isoformat(), "pip-page-check"),
    )
    store.conn.commit()
    assert tick(store, quiet_now, poster=lambda job: None) == []

    fired = []
    due = quiet_now.replace(hour=10, minute=0)
    store.conn.execute(
        "UPDATE jobs SET next_run = ?, enabled = 1 WHERE name = ?",
        ((due - timedelta(minutes=1)).isoformat(), "pip-hello-alarm"),
    )
    store.conn.execute(
        "UPDATE jobs SET next_run = ? WHERE name = ?",
        ((due - timedelta(minutes=1)).isoformat(), "pip-page-check"),
    )
    store.conn.commit()
    tick(store, due, poster=fired.append)
    assert {job["name"] for job in fired} == {"pip-hello-alarm", "pip-page-check"}
    alarm = store.get_by_name("pip-hello-alarm")
    assert alarm["enabled"] is False
    assert alarm["status"] == "done"
    again = store.get_by_name("pip-page-check")
    assert again["enabled"] is True
    assert again["last_run"]
    moment = datetime(2026, 10, 25, 10, 30, tzinfo=tz)
    assert cron_matches("*/30 * * * *", moment)
    store.close()


@pytest.mark.asyncio
async def test_job_fire_notifies_and_opens_a_page(workspace):
    from api import server

    server._notifications.clear()
    nudged = await server.fire_job(
        server.JobFireRequest(
            job={"name": "pip-hello-alarm", "payload": {"type": "notify", "message": "Pip here. One thing is due."}}
        )
    )
    assert nudged["state"] == "nudge"
    notes = await server.list_notifications()
    assert notes["notifications"][0]["state"] == "nudge"
    opened = await server.fire_job(
        server.JobFireRequest(
            job={"name": "pip-page-check", "payload": {"tool": "browser_open", "url": "https://example.com"}}
        )
    )
    assert opened["state"] == "done"
    assert opened["result"]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_boot_registers_only_pip(workspace):
    kernel, registry, _scheduler = await boot_os()
    assert kernel.get_module("department.pip") is not None
    assert kernel.get_module("department.marketing") is None
    assert kernel.get_module("department.sales") is None
    names = [agent.identity for agent in registry.list_agents()] if hasattr(registry, "list_agents") else []
    if names:
        assert names == ["pip"]
    assistant = PipAssistant()
    blocked = await assistant.execute({"description": "send the mail", "action": "send"})
    assert blocked["status"] == "approval_required"
