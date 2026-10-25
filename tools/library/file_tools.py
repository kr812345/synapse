import os
from typing import Any

from tools.jail import JailError, resolve_in_jail
from tools.tool_registry import ToolInterface


def _fail(exc: Exception) -> str:
    if isinstance(exc, JailError):
        return f"Error: {exc}"
    return f"Error: {exc}"


class FileRead(ToolInterface):
    name = "file_read"
    description = "Read a file inside the Pip workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path inside the workspace."}
        },
        "required": ["path"],
    }
    required_permissions = ["read"]

    async def execute(self, path: str = "", **kwargs) -> Any:
        try:
            safe = resolve_in_jail(path)
            with open(safe, "r", encoding="utf-8") as handle:
                return handle.read()
        except Exception as exc:
            return _fail(exc)


class FileWrite(ToolInterface):
    name = "file_write"
    description = "Create or overwrite a file inside the Pip workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path inside the workspace."},
            "content": {"type": "string", "description": "Content to write."},
        },
        "required": ["path", "content"],
    }
    required_permissions = ["write"]

    async def execute(self, path: str = "", content: str = "", **kwargs) -> Any:
        try:
            safe = resolve_in_jail(path)
            parent = os.path.dirname(safe)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(safe, "w", encoding="utf-8") as handle:
                handle.write(content)
            return f"File successfully written to {safe}"
        except Exception as exc:
            return _fail(exc)


class FileEdit(ToolInterface):
    name = "file_edit"
    description = "Replace one snippet in a file inside the Pip workspace."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "target": {"type": "string"},
            "replacement": {"type": "string"},
        },
        "required": ["path", "target", "replacement"],
    }
    required_permissions = ["write"]

    async def execute(self, path: str = "", target: str = "", replacement: str = "", **kwargs) -> Any:
        try:
            safe = resolve_in_jail(path)
            with open(safe, "r", encoding="utf-8") as handle:
                content = handle.read()
            if target not in content:
                return f"Error: Target text not found in {safe}"
            updated = content.replace(target, replacement, 1)
            with open(safe, "w", encoding="utf-8") as handle:
                handle.write(updated)
            return f"File successfully edited at {safe}"
        except Exception as exc:
            return _fail(exc)
