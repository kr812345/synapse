"""Vault create flag, approval gate, and redaction."""

import asyncio

import pytest

from vault.approvals import ApprovalGate
from vault.store import VaultError, VaultStore


def test_locked_vault_does_not_create_a_key(isolate_pip_files):
    store = VaultStore()
    with pytest.raises(VaultError, match="locked"):
        store.put("browser-login", "s3cret-value")
    assert not (isolate_pip_files / "vault.key").exists()


def test_allow_create_env_makes_a_key_and_hides_the_value(isolate_pip_files, monkeypatch):
    monkeypatch.setenv("PIP_VAULT_ALLOW_CREATE", "yes")
    store = VaultStore()
    store.put("browser-login", "s3cret-value")
    key = (isolate_pip_files / "vault.key").read_bytes()
    assert len(key) == 32
    raw = (isolate_pip_files / "vault.json").read_text(encoding="utf-8")
    assert "s3cret-value" not in raw
    assert store.list_names() == ["browser-login"]
    assert store.get("browser-login", purpose="runtime") == "s3cret-value"


def test_short_key_is_refused(isolate_pip_files):
    (isolate_pip_files / "vault.key").write_bytes(b"too-short")
    store = VaultStore()
    with pytest.raises(VaultError, match="32 bytes"):
        store.put("browser-login", "s3cret-value")


def test_action_read_needs_an_allowed_approval(isolate_pip_files):
    store = VaultStore(allow_create=True)
    store.put("browser-login", "s3cret-value")
    with pytest.raises(VaultError, match="approval"):
        store.get("browser-login", purpose="action")
    refused = store.request_approval("use-credential", "browser-login", "fill login")
    store.resolve_approval(refused["id"], False)
    with pytest.raises(VaultError, match="approval"):
        store.get("browser-login", purpose="action", approval_id=refused["id"])
    allowed = store.request_approval("use-credential", "browser-login", "fill login")
    store.resolve_approval(allowed["id"], True)
    assert store.get("browser-login", purpose="action", approval_id=allowed["id"]) == "s3cret-value"
    assert all("s3cret-value" not in str(row) for row in store.audit_log())


@pytest.mark.asyncio
async def test_approval_gate_wait_follows_the_decision(isolate_pip_files):
    gate = ApprovalGate(VaultStore(allow_create=True))
    refused = gate.request("send", "note", "send the note")

    async def refuse():
        gate.resolve(refused["id"], False)

    task = asyncio.create_task(refuse())
    assert await gate.wait(refused["id"], timeout=1) is False
    await task

    allowed = gate.request("send", "note", "send the note")

    async def allow():
        gate.resolve(allowed["id"], True)

    task = asyncio.create_task(allow())
    assert await gate.wait(allowed["id"], timeout=1) is True
    await task
    missing = await gate.wait("does-not-exist", timeout=0.05)
    assert missing is False
