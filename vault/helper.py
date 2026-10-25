"""Local unlock helper.

The brain talks to this process over a Unix socket. The helper holds the
vault key. Action reads are refused unless the approval id is already allowed.
Run: python -m vault.helper serve
"""

from __future__ import annotations

import json
import os
import socket
import sys

from vault.store import VaultError, VaultStore

DEFAULT_SOCK = "/run/pip/vault.sock"


def handle(store: VaultStore, request: dict) -> dict:
    op = request.get("op")
    try:
        if op == "get":
            value = store.get(
                request["name"],
                purpose=request.get("purpose", "runtime"),
                approval_id=request.get("approval_id"),
            )
            return {"ok": True, "value": value}
        if op == "put":
            store.put(request["name"], request["value"])
            return {"ok": True}
        if op == "list":
            return {"ok": True, "names": store.list_names()}
        return {"ok": False, "error": "unknown op"}
    except VaultError as exc:
        return {"ok": False, "error": str(exc)}
    except KeyError as exc:
        return {"ok": False, "error": f"missing {exc}"}


def _own_socket(sock_path: str) -> None:
    """Let the pip user talk to a root-owned helper. The directory stays private."""
    os.chmod(sock_path, 0o660)
    group_name = os.environ.get("PIP_VAULT_GROUP", "pip")
    try:
        import grp

        gid = grp.getgrnam(group_name).gr_gid
        os.chown(sock_path, os.getuid(), gid)
    except (KeyError, PermissionError, OSError):
        pass


def serve(sock_path: str) -> None:
    parent = os.path.dirname(sock_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.exists(sock_path):
        os.remove(sock_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    _own_socket(sock_path)
    server.listen(8)
    store = VaultStore()
    while True:
        conn, _addr = server.accept()
        try:
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
            if not data:
                continue
            request = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
            response = handle(store, request)
            conn.sendall(json.dumps(response).encode("utf-8") + b"\n")
        finally:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "serve":
        print("usage: python -m vault.helper serve", file=sys.stderr)
        return 2
    sock_path = os.environ.get("PIP_VAULT_SOCK", DEFAULT_SOCK)
    serve(sock_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
