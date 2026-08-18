import os
from typing import Any
from tools.tool_registry import ToolInterface

class FileRead(ToolInterface):
    name = "file_read"
    description = "Read the contents of a file on disk."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file."}
        },
        "required": ["path"]
    }
    required_permissions = ["read"]

    async def execute(self, path: str, **kwargs) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

class FileWrite(ToolInterface):
    name = "file_write"
    description = "Create or overwrite a file with new content."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file."},
            "content": {"type": "string", "description": "Content to write to the file."}
        },
        "required": ["path", "content"]
    }
    required_permissions = ["write"]

    async def execute(self, path: str, content: str, **kwargs) -> Any:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File successfully written to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

class FileEdit(ToolInterface):
    name = "file_edit"
    description = "Replace a specific snippet of text in a file."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file."},
            "target": {"type": "string", "description": "The exact text snippet to replace."},
            "replacement": {"type": "string", "description": "The new text snippet."}
        },
        "required": ["path", "target", "replacement"]
    }
    required_permissions = ["write"]

    async def execute(self, path: str, target: str, replacement: str, **kwargs) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if target not in content:
                return f"Error: Target text not found in {path}"
                
            new_content = content.replace(target, replacement, 1)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"File successfully edited at {path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"
