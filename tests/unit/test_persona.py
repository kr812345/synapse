"""Offline Pip replies."""

from persona.kiwi import (
    PIP_SYSTEM_PROMPT,
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
