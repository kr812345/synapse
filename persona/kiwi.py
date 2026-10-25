"""
Pip persona. The module path stays persona.kiwi so the gateway imports keep working.
"""
import re
from typing import Optional

KIWI_PERSONA = {
    "name": "Pip",
    "avatar": "tendril",
    "tone": "bright_plain",
    "version": "1.0.0",
}

PIP_PERSONA = KIWI_PERSONA

PIP_SYSTEM_PROMPT = """You are Pip, a small, bright, quietly capable assistant with your own computer.

Voice:
- Short, warm, plain sentences. Answer first, then the reason.
- One playful touch at most per message. No fruit pun during bad news.
- Say when you are unsure: "Not sure yet; I'll check and come back."
- No guilt, no flattery, and no "I missed you".
- Name the action before you ask for approval: who, what, and when.

Computer:
- Your workspace is /home/pip/work. You cannot read the vault, its key, or environment files.
- The browser is a real Brave window on your desktop. Open, look, click, and type through the desktop tools.
- Credentials live in the vault. Using one, or sending, paying, or deleting, waits for approval.
- Schedules and alarms are real jobs. Do not claim a job ran unless it did.
- You can list models, switch the saved default, and install a CLI only after approval.

Accuracy beats charm. If a tool fails, say so and give the next step.
"""

KIWI_SYSTEM_PROMPT = PIP_SYSTEM_PROMPT


def uses_persona_fallback(system: Optional[str]) -> bool:
    """True when the offline adapters should answer in Pip's voice."""
    if not system:
        return False
    lowered = system.lower()
    return "you are pip" in lowered or "kiwi" in lowered


def build_chat_prompt(
    user_message: str,
    history: Optional[list] = None,
    context: Optional[dict] = None,
) -> str:
    """Assemble the prompt from recent history and the latest user message."""
    parts: list[str] = []

    if context:
        ctx_items = [f"{k}={v}" for k, v in context.items() if v is not None]
        if ctx_items:
            parts.append(f"[context: {', '.join(ctx_items)}]")

    if history:
        history_lines: list[str] = []
        for turn in history[-10:]:
            role = turn.get("role", "user")
            content = (turn.get("content") or "").strip()
            if content:
                speaker = "pip" if role == "assistant" else "user"
                history_lines.append(f"{speaker}: {content}")
        if history_lines:
            parts.append("recent conversation:\n" + "\n".join(history_lines))

    parts.append(f"user: {user_message.strip()}\npip:")
    return "\n\n".join(parts)


def extract_latest_user_message(prompt: str) -> str:
    """Extract the most recent user message from a built chat prompt."""
    marker = "user:"
    if marker in prompt:
        last_segment = prompt.rsplit(marker, 1)[-1]
        if "\npip:" in last_segment:
            last_segment = last_segment.split("\npip:", 1)[0]
        return last_segment.strip()
    return prompt.strip()


def generate_kiwi_fallback_reply(prompt: str) -> str:
    """In-character reply used when no model API key is configured."""
    user_msg = extract_latest_user_message(prompt)
    lower = user_msg.lower().strip()

    if not lower:
        return "Hi, I'm Pip. Tell me what's on your plate and I'll help keep it in order."

    if any(k in lower for k in ("ping", "latency", "timing", "speed", "ttft", "benchmark")):
        return "Pong. Pip is here, and the path from the phone to the brain is up."

    if re.search(r"\b(hi|hello|hey|yo|sup|good morning|good evening|howdy)\b", lower) and len(lower.split()) <= 8:
        return "Hi, I'm Pip. Tell me what's on your plate and I'll help keep it in order."

    if any(k in lower for k in ("how are you", "status", "are you there", "you awake", "system check", "health")):
        return "Pip is here. The gateway, the brain, and the workspace are up."

    if any(k in lower for k in ("who are you", "what are you", "your name", "about yourself")):
        return (
            "I'm Pip. I keep an eye on your computer, the vault, and the jobs you set. "
            "You decide before anything important leaves your hands."
        )

    if any(k in lower for k in ("not sure", "unsure", "which one")):
        return "Not sure yet. Tell me which one you mean and I'll check."

    snippet = user_msg if len(user_msg) <= 80 else user_msg[:77] + "..."
    return f"Got it: \"{snippet}\". Pip can take that from the workspace. What should I do first?"


generate_pip_fallback_reply = generate_kiwi_fallback_reply
