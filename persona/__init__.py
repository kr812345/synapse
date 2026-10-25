"""Pip persona. Legacy kiwi imports still resolve."""
from persona.kiwi import (
    KIWI_PERSONA,
    KIWI_SYSTEM_PROMPT,
    PIP_PERSONA,
    PIP_SYSTEM_PROMPT,
    build_chat_prompt,
    generate_kiwi_fallback_reply,
    generate_pip_fallback_reply,
)

__all__ = [
    "KIWI_PERSONA",
    "KIWI_SYSTEM_PROMPT",
    "PIP_PERSONA",
    "PIP_SYSTEM_PROMPT",
    "build_chat_prompt",
    "generate_kiwi_fallback_reply",
    "generate_pip_fallback_reply",
]
