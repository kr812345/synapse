"""Allowlisted CLI installers. The model cannot supply the command."""

from __future__ import annotations

INSTALLERS = {
    "claude-code": {
        "binary": "claude",
        "argv": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        "label": "Claude Code",
    },
    "cursor-cli": {
        "binary": "cursor-agent",
        "argv": ["bash", "-lc", "curl -fsSL https://cursor.com/install | bash"],
        "label": "Cursor CLI",
    },
    "antigravity": {
        "binary": "agy",
        "argv": None,
        "label": "Antigravity CLI",
        "note": "Place the agy binary on PATH. Pip does not download it.",
    },
}
