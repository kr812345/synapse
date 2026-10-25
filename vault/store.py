"""Envelope-encrypted secret store.

Secrets are AES-GCM ciphertext in a JSON file. The 32-byte key lives in a
separate file, outside the workspace. Audit rows record the secret's name,
never its value. An action-purpose read is refused unless an approval id
has already been allowed.
"""

from __future__ import annotations

import base64
import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Optional

import fcntl
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DEFAULT_STORE = "/var/lib/pip/vault.json"
DEFAULT_KEY = "/etc/pip/vault.key"


class VaultError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VaultStore:
    def __init__(
        self,
        store_path: Optional[str] = None,
        key_path: Optional[str] = None,
        allow_create: bool = False,
    ):
        self.store_path = store_path or os.environ.get("PIP_VAULT_PATH", DEFAULT_STORE)
        self.key_path = key_path or os.environ.get("PIP_VAULT_KEY_FILE", DEFAULT_KEY)
        self.allow_create = allow_create

    def _load_key(self) -> bytes:
        if not os.path.exists(self.key_path):
            if not self.allow_create:
                raise VaultError("vault is locked")
            parent = os.path.dirname(self.key_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            key = AESGCM.generate_key(bit_length=256)
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
            return key
        with open(self.key_path, "rb") as handle:
            key = handle.read()
        if len(key) != 32:
            raise VaultError("vault key must be 32 bytes")
        return key

    def _empty(self) -> dict:
        return {"entries": {}, "audit": [], "approvals": {}}

    def _read_unlocked(self) -> dict:
        if not os.path.exists(self.store_path):
            return self._empty()
        with open(self.store_path, "r", encoding="utf-8") as handle:
            raw = handle.read().strip()
        if not raw:
            return self._empty()
        data = json.loads(raw)
        data.setdefault("entries", {})
        data.setdefault("audit", [])
        data.setdefault("approvals", {})
        return data

    def _write_unlocked(self, data: dict) -> None:
        parent = os.path.dirname(self.store_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        temporary = self.store_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.store_path)

    def _mutate(self, fn):
        parent = os.path.dirname(self.store_path) or "."
        os.makedirs(parent, exist_ok=True)
        lock_path = self.store_path + ".lock"
        with open(lock_path, "a", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                data = self._read_unlocked()
                result = fn(data)
                self._write_unlocked(data)
                return result
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _encrypt(self, value: str) -> dict:
        aes = AESGCM(self._load_key())
        nonce = os.urandom(12)
        ciphertext = aes.encrypt(nonce, value.encode("utf-8"), None)
        return {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ct": base64.b64encode(ciphertext).decode("ascii"),
        }

    def _decrypt(self, blob: dict) -> str:
        aes = AESGCM(self._load_key())
        nonce = base64.b64decode(blob["nonce"])
        ciphertext = base64.b64decode(blob["ct"])
        return aes.decrypt(nonce, ciphertext, None).decode("utf-8")

    def _socket(self) -> Optional[str]:
        path = os.environ.get("PIP_VAULT_SOCK")
        if path and os.path.exists(path):
            return path
        return None

    def _rpc(self, payload: dict) -> dict:
        sock_path = self._socket()
        if not sock_path:
            raise VaultError("vault helper is not available")
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.connect(sock_path)
            client.sendall(json.dumps(payload).encode("utf-8") + b"\n")
            data = b""
            while b"\n" not in data:
                chunk = client.recv(65536)
                if not chunk:
                    break
                data += chunk
        finally:
            client.close()
        if not data:
            raise VaultError("vault helper returned nothing")
        response = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
        if not response.get("ok"):
            raise VaultError(response.get("error") or "vault request failed")
        return response

    def put(self, name: str, value: str) -> None:
        if not name or not str(name).strip():
            raise VaultError("secret name is required")
        if self._socket():
            self._rpc({"op": "put", "name": name, "value": value})
            return
        blob = self._encrypt(value)

        def apply(data: dict) -> None:
            data["entries"][name] = blob
            data["audit"].append(
                {
                    "ts": _now(),
                    "name": name,
                    "tool": "vault_put",
                    "decision": "stored",
                }
            )

        self._mutate(apply)

    def has(self, name: str) -> bool:
        if self._socket():
            return name in self.list_names()
        try:
            data = self._read_unlocked()
        except FileNotFoundError:
            return False
        return name in data.get("entries", {})

    def list_names(self) -> list[str]:
        if self._socket():
            return list(self._rpc({"op": "list"}).get("names", []))
        if not os.path.exists(self.store_path):
            return []
        return sorted(self._read_unlocked().get("entries", {}).keys())

    def get(self, name: str, purpose: str = "runtime", approval_id: Optional[str] = None) -> str:
        """Return a secret. Action reads require an allowed approval id."""
        if self._socket():
            return self._rpc(
                {
                    "op": "get",
                    "name": name,
                    "purpose": purpose,
                    "approval_id": approval_id,
                }
            )["value"]

        def apply(data: dict) -> str:
            if purpose == "action":
                approval = data["approvals"].get(approval_id or "")
                if not approval or approval.get("status") != "allowed" or approval.get("secret") != name:
                    raise VaultError("approval required")
            blob = data["entries"].get(name)
            if not blob:
                raise VaultError("unknown secret")
            value = self._decrypt(blob)
            data["audit"].append(
                {
                    "ts": _now(),
                    "name": name,
                    "tool": purpose,
                    "decision": "read",
                }
            )
            return value

        return self._mutate(apply)

    def audit(self, name: str, tool: str, decision: str) -> None:
        def apply(data: dict) -> None:
            data["audit"].append(
                {
                    "ts": _now(),
                    "name": name,
                    "tool": tool,
                    "decision": decision,
                }
            )

        self._mutate(apply)

    def audit_log(self) -> list[dict]:
        if not os.path.exists(self.store_path):
            return []
        return list(self._read_unlocked().get("audit", []))

    def request_approval(self, action: str, secret: str, detail: str) -> dict:
        approval_id = base64.urlsafe_b64encode(os.urandom(9)).decode("ascii").rstrip("=")

        def apply(data: dict) -> dict:
            record = {
                "id": approval_id,
                "action": action,
                "secret": secret,
                "detail": detail,
                "status": "pending",
                "ts": _now(),
            }
            data["approvals"][approval_id] = record
            return record

        return self._mutate(apply)

    def resolve_approval(self, approval_id: str, allow: bool) -> dict:
        def apply(data: dict) -> dict:
            record = data["approvals"].get(approval_id)
            if not record:
                raise VaultError("unknown approval")
            record["status"] = "allowed" if allow else "refused"
            record["resolved_at"] = _now()
            data["audit"].append(
                {
                    "ts": record["resolved_at"],
                    "name": record.get("secret", ""),
                    "tool": record.get("action", ""),
                    "decision": record["status"],
                }
            )
            return record

        return self._mutate(apply)

    def pending_approvals(self) -> list[dict]:
        if not os.path.exists(self.store_path):
            return []
        data = self._read_unlocked()
        return [row for row in data.get("approvals", {}).values() if row.get("status") == "pending"]

    def get_approval(self, approval_id: str) -> Optional[dict]:
        if not os.path.exists(self.store_path):
            return None
        return self._read_unlocked().get("approvals", {}).get(approval_id)


def redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[redacted]")


def runtime_secret(name: str) -> Optional[str]:
    """Key for a model adapter. Environment first, then the vault. Never logged."""
    env_value = os.environ.get(name)
    if env_value:
        return env_value
    store = VaultStore()
    try:
        if store.has(name):
            return store.get(name, purpose="runtime")
    except VaultError:
        return None
    return None
