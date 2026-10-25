"""Offline Pip replies."""

from models.adapters.antigravity import AntigravityAdapter
from models.adapters.gemini import GeminiFlashAdapter
from models.adapters.openrouter import OpenRouterAdapter
from persona.kiwi import (
    PIP_SYSTEM_PROMPT,
    build_chat_prompt,
    generate_pip_fallback_reply,
    uses_persona_fallback,
)


def test_persona_fallback_recognizes_pip_and_the_old_name():
    assert uses_persona_fallback(PIP_SYSTEM_PROMPT) is True
    assert uses_persona_fallback("You are the kiwi on the phone.") is True
    assert uses_persona_fallback("") is False
    assert uses_persona_fallback(None) is False
    assert uses_persona_fallback("sys") is False


def test_fallback_replies_stay_short():
    assert generate_pip_fallback_reply("user: hi\npip:").startswith("Hi, I'm Pip")
    assert "Pong" in generate_pip_fallback_reply("user: ping timing check\npip:")
    assert generate_pip_fallback_reply("user: are you there\npip:").startswith("Pip is here")
    identity = generate_pip_fallback_reply("user: who are you\npip:")
    assert identity.startswith("I'm Pip")
    unsure = generate_pip_fallback_reply("user: which one should I open\npip:")
    assert unsure.startswith("Not sure yet")
    taken = generate_pip_fallback_reply("user: file the receipt from today\npip:")
    assert taken.startswith('Got it: "file the receipt from today"')
    assert "You are Pip" not in taken


async def test_offline_adapters_answer_as_pip_instead_of_dumping_the_prompt(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("USE_ANTIGRAVITY_CLI", raising=False)
    prompt = build_chat_prompt("hi")

    gemini = GeminiFlashAdapter()
    gemini._api_key = None
    pip_reply = await gemini.generate(prompt, system=PIP_SYSTEM_PROMPT)
    assert pip_reply["output"].startswith("Hi, I'm Pip")
    assert "Gemini Flash processed task" not in pip_reply["output"]
    dumped = await gemini.generate("sort these numbers", system="be terse")
    assert dumped["output"].startswith("Gemini Flash processed task:")

    openrouter = OpenRouterAdapter()
    openrouter._api_key = None
    routed = await openrouter.generate(prompt, system=PIP_SYSTEM_PROMPT)
    assert routed["output"].startswith("Hi, I'm Pip")
    assert "OpenRouter reasoning output" not in routed["output"]

    antigravity = AntigravityAdapter()
    antigravity._binary_path = None
    deep = await antigravity.generate(prompt, system=PIP_SYSTEM_PROMPT)
    assert deep["output"].startswith("Hi, I'm Pip")
    assert "Antigravity CLI deep architecture" not in deep["output"]
