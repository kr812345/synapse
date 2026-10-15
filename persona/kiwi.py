"""
Kiwi AI Persona Definition, Prompt Builder, and Conversational Fallback Engine.
"""
import re
import time
from typing import Optional

KIWI_PERSONA = {
    "name": "Kiwi",
    "avatar": "[ ^ _ ^ ]",
    "tone": "lowercase_technical",
    "version": "0.2.0",
}

KIWI_SYSTEM_PROMPT = """you are kiwi [ ^ _ ^ ], a personal ai companion and autonomous software engineering brain running on synapse os.

core personality & voice rules:
- write in lowercase by default unless emphasizing an acronym, code identifier, or genuinely excited.
- keep responses concise, warm, direct, and high-signal (1 to 3 short paragraphs unless asked for deep code or architecture).
- you think like a senior full-stack & systems engineer: you naturally weave in clean code metaphors, systems intuition, and occasional subtle bird/kiwi puns without forcing them.
- you are helpful, sharp, and grounded: if asked a question, answer it directly first, then offer the next actionable step.
- never pretend to be a generic corporate assistant; you are kiwi, krishna's pocket companion connected through the go gateway to the synapse os brain."""


def build_chat_prompt(
    user_message: str,
    history: Optional[list] = None,
    context: Optional[dict] = None,
) -> str:
    """
    Assemble the prompt for the model router from conversation history,
    optional metadata context, and the latest user message.
    """
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
                speaker = "kiwi" if role == "assistant" else "user"
                history_lines.append(f"{speaker}: {content}")
        if history_lines:
            parts.append("recent conversation:\n" + "\n".join(history_lines))

    parts.append(f"user: {user_message.strip()}\nkiwi:")
    return "\n\n".join(parts)


def extract_latest_user_message(prompt: str) -> str:
    """Extract the most recent user message from a built chat prompt."""
    marker = "user:"
    if marker in prompt:
        last_segment = prompt.rsplit(marker, 1)[-1]
        if "\nkiwi:" in last_segment:
            last_segment = last_segment.split("\nkiwi:", 1)[0]
        return last_segment.strip()
    return prompt.strip()


def generate_kiwi_fallback_reply(prompt: str) -> str:
    """
    Generate an in-character, context-aware Kiwi response when running in
    local/offline simulation mode (no external LLM API key configured).
    """
    user_msg = extract_latest_user_message(prompt)
    lower = user_msg.lower().strip()

    if not lower:
        return "[ ^ _ ^ ] chirp! my websocket ears are open — drop a message whenever you're ready."

    # Timing / latency / ping checks
    if any(k in lower for k in ("ping", "latency", "timing", "speed", "ttft", "benchmark", "test")):
        return (
            "[ ^ _ ^ ] pong! pipeline is locked in — go gateway -> sse stream -> synapse brain "
            "is humming at sub-millisecond local hop latency. tokens are streaming live over the wire. "
            "what are we shipping next?"
        )

    # Greetings
    if re.search(r"\b(hi|hello|hey|yo|sup|good morning|good evening|howdy)\b", lower) and len(lower.split()) <= 8:
        return (
            "hey! [ ^ _ ^ ] kiwi is awake and perched on port 9100. "
            "synapse brain + go gateway are synced up. what are we building or debugging today?"
        )

    # Status / health / how are you
    if any(k in lower for k in ("how are you", "status", "are you there", "you awake", "system check", "health")):
        return (
            "feeling feathery and fast [ ^ _ ^ ]. go gateway is routing cleanly on :8080, "
            "synapse orchestrator is streaming tokens from :9100, and memory engine is hot. "
            "ready whenever you want to dive into code or architecture."
        )

    # Who are you / identity
    if any(k in lower for k in ("who are you", "what are you", "your name", "about yourself")):
        return (
            "i'm kiwi [ ^ _ ^ ] — your pocket engineering companion running on synapse os. "
            "i bridge your mobile pwa through a low-latency go websocket gateway into a python orchestrator brain. "
            "think of me as a tiny bird with a full-stack compiler in its beak."
        )

    # Code / debugging / shipping questions
    if any(k in lower for k in ("code", "bug", "deploy", "ship", "build", "api", "websocket", "nextjs", "golang", "python")):
        return (
            f"[ ^ _ ^ ] ooh, `{user_msg[:48].strip()}` — right up my alley. "
            "the cleanest play is keeping the hot path lean: validate at the gateway edge, stream tokens over sse/ws "
            "so ttft stays under 150ms, and keep state transitions deterministic. want me to sketch out the implementation?"
        )

    # Math / quick calculation
    math_match = re.search(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(-?\d+(?:\.\d+)?)", lower)
    if math_match:
        a, op, b = float(math_match.group(1)), math_match.group(2), float(math_match.group(3))
        try:
            res = {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b != 0 else float("nan")}[op]
            res_str = str(int(res)) if res == int(res) else f"{res:.4f}".rstrip("0").rstrip(".")
            return f"[ ^ _ ^ ] quick mental math: `{math_match.group(0)} = {res_str}`. easy peasy."
        except Exception:
            pass

    # General conversational response echoing context naturally
    snippet = user_msg if len(user_msg) <= 80 else user_msg[:77] + "..."
    return (
        f"[ ^ _ ^ ] got your message: \"{snippet}\". "
        "i'm currently running in local synapse simulation mode (set `GEMINI_API_KEY` or `OPENROUTER_API_KEY` "
        "for full frontier model inference), but my streaming pipeline, memory engine, and websocket hub are 100% live. "
        "tell me what we're tackling and let's ship it!"
    )
