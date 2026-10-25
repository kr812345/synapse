import pytest
from httpx import AsyncClient, ASGITransport
from api import server
from boot import boot_os
from persona.kiwi import KIWI_PERSONA, KIWI_SYSTEM_PROMPT, build_chat_prompt


async def _ensure_kernel():
    if server.kernel is None:
        kernel, registry, scheduler = await boot_os()
        server.kernel = kernel
        server.os_state["kernel"] = kernel
        server.os_state["registry"] = registry
        server.os_state["scheduler"] = scheduler


@pytest.mark.asyncio
async def test_health_endpoint():
    await _ensure_kernel()
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "kiwi-brain"
    assert data["version"] == "0.1.0"
    assert data["kernel_ready"] is True


@pytest.mark.asyncio
async def test_internal_chat_endpoint():
    await _ensure_kernel()
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/internal/chat",
            json={
                "user_id": "test_user",
                "conversation_id": "test_session_1",
                "message": "hello kiwi, how are you?",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data and len(data["response"]) > 0
    assert data["reply"] == data["response"]
    assert data["conversation_id"] == "test_session_1"
    assert data["session_id"] == "test_session_1"
    assert "Pip" in data["response"]


@pytest.mark.asyncio
async def test_internal_chat_empty_message_returns_400():
    await _ensure_kernel()
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/internal/chat",
            json={"user_id": "u1", "conversation_id": "s1", "message": "   "},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_internal_chat_kernel_not_ready_returns_503():
    prev_kernel = server.kernel
    prev_state_kernel = server.os_state.get("kernel")
    server.kernel = None
    server.os_state["kernel"] = None
    try:
        transport = ASGITransport(app=server.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/internal/chat",
                json={"user_id": "u1", "conversation_id": "s1", "message": "hello"},
            )
        assert resp.status_code == 503
    finally:
        server.kernel = prev_kernel
        server.os_state["kernel"] = prev_state_kernel


def test_kiwi_persona_prompt_builder():
    assert KIWI_PERSONA["name"] == "Pip"
    assert "You are Pip" in KIWI_SYSTEM_PROMPT
    prompt = build_chat_prompt(
        "let's test latency",
        history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey!"}],
        context={"device": "mobile"},
    )
    assert "device=mobile" in prompt
    assert "user: hi" in prompt
    assert "pip: hey!" in prompt
    assert "user: let's test latency" in prompt
