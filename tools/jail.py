"""Workspace jail for Pip's file tools.

Pip may read and write only inside PIP_WORK_ROOT (default /home/pip/work).
The vault, its key, the jobs database, the model config, and any .env file
stay outside that root and are refused even if the root is widened.
"""

from __future__ import annotations

import os

DEFAULT_WORK_ROOT = "/home/pip/work"

_SENSITIVE_ENV = (
    ("PIP_VAULT_PATH", "/var/lib/pip/vault.json"),
    ("PIP_VAULT_KEY_FILE", "/etc/pip/vault.key"),
    ("PIP_JOBS_PATH", "/var/lib/pip/jobs.sqlite"),
    ("PIP_MODEL_CONFIG", "/home/pip/.config/pip/model.json"),
)


class JailError(PermissionError):
    """Raised when a path leaves the workspace or names a secret file."""


def work_root() -> str:
    configured = os.environ.get("PIP_WORK_ROOT", DEFAULT_WORK_ROOT)
    return os.path.realpath(configured)


def _sensitive_paths() -> list[str]:
    found: list[str] = []
    for env_name, default in _SENSITIVE_ENV:
        raw = os.environ.get(env_name, default)
        if raw:
            found.append(os.path.realpath(raw))
    return found


def resolve_in_jail(path: str) -> str:
    """Return a real path inside the workspace, or raise JailError."""
    if path is None or not str(path).strip():
        raise JailError("path is required")

    root = work_root()
    raw = str(path)
    if os.path.isabs(raw):
        candidate = os.path.realpath(raw)
    else:
        candidate = os.path.realpath(os.path.join(root, raw))

    if candidate != root and not candidate.startswith(root + os.sep):
        raise JailError("path is outside the workspace")

    for blocked in _sensitive_paths():
        if candidate == blocked or candidate.startswith(blocked + os.sep):
            raise JailError("path is not available")

    if os.path.basename(candidate) == ".env" or candidate.endswith(os.sep + ".env"):
        raise JailError("path is not available")

    return candidate
