"""Brain HTTP paths used by the gateway. No live port and no model key."""

import pytest
from httpx import ASGITransport, AsyncClient

from tools.library.desktop import FakeDesktop, set_driver


@pytest.fixture(autouse=True)
def isolate_pip_files(monkeypatch, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("PIP_WORK_ROOT", str(work))
    monkeypatch.setenv("PIP_VAULT_PATH", str(tmp_path / "vault.json"))
    monkeypatch.setenv("PIP_VAULT_KEY_FILE", str(tmp_path / "vault.key"))
    monkeypatch.setenv("PIP_VAULT_ALLOW_CREATE", "1")
    monkeypatch.setenv("PIP_JOBS_PATH", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("PIP_MODEL_CONFIG", str(tmp_path / "model.json"))
    monkeypatch.setenv("PIP_DESKTOP_DRIVER", "fake")
    monkeypatch.delenv("PIP_VAULT_SOCK", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PIP_DEFAULT_MODEL", raising=False)
    set_driver(FakeDesktop())
    yield tmp_path
    set_driver(None)


@pytest.fixture
async def client(isolate_pip_files, monkeypatch):
    from api import server
    from boot import boot_os

    # Importing the brain loads .env and can put a model key back.
    for name in (
        "GEMINI_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "USE_ANTIGRAVITY_CLI",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "host=127.0.0.1 port=1 dbname=pip_absent user=pip connect_timeout=1",
    )
    monkeypatch.setenv("PIP_WORK_ROOT", str(isolate_pip_files / "work"))
    monkeypatch.setenv("PIP_VAULT_PATH", str(isolate_pip_files / "vault.json"))
    monkeypatch.setenv("PIP_VAULT_KEY_FILE", str(isolate_pip_files / "vault.key"))
    monkeypatch.setenv("PIP_VAULT_ALLOW_CREATE", "1")
    monkeypatch.setenv("PIP_JOBS_PATH", str(isolate_pip_files / "jobs.sqlite"))
    monkeypatch.setenv("PIP_MODEL_CONFIG", str(isolate_pip_files / "model.json"))
    monkeypatch.setenv("PIP_DESKTOP_DRIVER", "fake")
    monkeypatch.delenv("PIP_VAULT_SOCK", raising=False)

    kernel, registry, scheduler = await boot_os()
    router = kernel.get_module("model_router")
    if router is not None:
        for adapter in getattr(router, "_adapter_list", []):
            if hasattr(adapter, "_api_key"):
                adapter._api_key = None
    server.kernel = kernel
    server.os_state["kernel"] = kernel
    server.os_state["registry"] = registry
    server.os_state["scheduler"] = scheduler
    server._notifications.clear()
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    server._notifications.clear()


async def test_health_and_chat_answer_as_pip(client):
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["kernel_ready"] is True

    chat = await client.post(
        "/internal/chat",
        json={"message": "hi", "conversation_id": "local-1", "user_id": "krishna"},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["response"].startswith("Hi, I'm Pip")
    assert "Gemini Flash processed" not in body["response"]
    assert "You are Pip, a small" not in body["response"]
    assert body["conversation_id"] == "local-1"

    empty = await client.post("/internal/chat", json={"message": "   "})
    assert empty.status_code == 400


async def test_approval_round_trip_never_returns_the_secret(client):
    from vault.store import VaultStore

    store = VaultStore()
    store.put("browser-login", "s3cret-value")
    record = store.request_approval("use-credential", "browser-login", "fill a browser login")

    listed = await client.get("/internal/approvals")
    assert listed.status_code == 200
    assert listed.json()["approvals"][0]["id"] == record["id"]
    assert "s3cret-value" not in listed.text

    missing = await client.post("/internal/approvals/missing", json={"allow": True})
    assert missing.status_code == 404

    refused = await client.post(f"/internal/approvals/{record['id']}", json={"allow": False})
    assert refused.status_code == 200
    assert refused.json()["approval"]["status"] == "refused"
    assert (await client.get("/internal/approvals")).json()["approvals"] == []


async def test_job_fire_notifies_once(client):
    fired = await client.post(
        "/internal/jobs/fire",
        json={
            "job": {
                "name": "pip-hello-alarm",
                "payload": {"type": "notify", "message": "Pip here. One thing is due."},
            }
        },
    )
    assert fired.status_code == 200
    assert fired.json()["state"] == "nudge"

    notes = await client.get("/internal/notifications")
    assert notes.json()["notifications"][0]["message"] == "Pip here. One thing is due."
    assert (await client.get("/internal/notifications")).json()["notifications"] == []

    opened = await client.post(
        "/internal/jobs/fire",
        json={
            "job": {
                "name": "pip-page-check",
                "payload": {"tool": "browser_open", "url": "https://example.com"},
            }
        },
    )
    assert opened.json()["state"] == "done"
    assert opened.json()["result"]["url"] == "https://example.com"
