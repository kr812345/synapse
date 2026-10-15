import json
import pytest
from httpx import AsyncClient, ASGITransport
from api import server
from boot import boot_os
from models.model_router import ModelRouter
from models.adapters.base import BaseModelAdapter


class FailingStreamAdapter(BaseModelAdapter):
    tier = "tier1"
    name = "FailingAdapter"
    model_id = "failing-1"

    async def generate(self, prompt: str, system=None, **kwargs) -> str:
        raise RuntimeError("primary adapter down")

    async def stream_generate(self, prompt: str, system=None, **kwargs):
        raise RuntimeError("primary stream down")
        yield ""  # pragma: no cover


class WorkingStreamAdapter(BaseModelAdapter):
    tier = "tier2"
    name = "WorkingAdapter"
    model_id = "working-2"

    async def generate(self, prompt: str, system=None, **kwargs) -> str:
        return "fallback stream works"


async def _ensure_kernel():
    if server.kernel is None:
        kernel, registry, scheduler = await boot_os()
        server.kernel = kernel
        server.os_state["kernel"] = kernel
        server.os_state["registry"] = registry
        server.os_state["scheduler"] = scheduler


@pytest.mark.asyncio
async def test_internal_chat_stream_sse():
    await _ensure_kernel()
    transport = ASGITransport(app=server.app)
    events = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/internal/chat/stream",
            json={
                "user_id": "stream_user",
                "conversation_id": "stream_session",
                "message": "ping timing test",
            },
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            assert resp.headers.get("x-accel-buffering") == "no"
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    events.append(payload)

    token_events = [e["token"] for e in events if "token" in e]
    done_events = [e for e in events if e.get("done") is True]
    assert len(token_events) > 1
    assert len(done_events) == 1
    full_reply = "".join(token_events)
    assert "[ ^ _ ^ ]" in full_reply


@pytest.mark.asyncio
async def test_model_router_stream_fallback():
    router = ModelRouter(adapters=[FailingStreamAdapter(), WorkingStreamAdapter()])

    chunks = []
    async for token in router.stream_generate("ping fallback"):
        chunks.append(token)

    assert "".join(chunks) == "fallback stream works"


@pytest.mark.asyncio
async def test_internal_chat_stream_empty_message_returns_400():
    await _ensure_kernel()
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/internal/chat/stream",
            json={"user_id": "u1", "conversation_id": "s1", "message": "   "},
        )
    assert resp.status_code == 400
