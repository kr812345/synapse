import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from boot import boot_os
from persona.kiwi import KIWI_SYSTEM_PROMPT, build_chat_prompt
from shared.interfaces import Module
from shared.models import Event


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                pass


manager = ConnectionManager()


class WebSocketBridge(Module):
    def __init__(self):
        self.kernel = None

    @property
    def name(self) -> str:
        return "websocket_bridge"

    def set_kernel(self, kernel):
        self.kernel = kernel

    async def handle_event(self, event: Event):
        await manager.broadcast(event.model_dump_json())


bridge = WebSocketBridge()
os_state: Dict[str, Any] = {}
kernel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kernel
    booted_kernel, registry, scheduler = await boot_os()
    booted_kernel.register_module(bridge)

    kernel = booted_kernel
    os_state["kernel"] = booted_kernel
    os_state["registry"] = registry
    os_state["scheduler"] = scheduler
    print("[SERVER] Connected Synapse OS (Kiwi Brain) to API Server.")
    yield
    print("[SERVER] Shutting down Synapse OS...")


app = FastAPI(title="Synapse OS & Kiwi Brain API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    task: Optional[str] = None
    goal: Optional[str] = None


class InternalChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class InternalChatResponse(BaseModel):
    response: str
    reply: str
    conversation_id: str
    session_id: str
    model_used: str
    metadata: Optional[Dict[str, Any]] = None


def _get_active_kernel():
    return kernel if kernel is not None else os_state.get("kernel")


def _get_router_and_memory():
    active_kernel = _get_active_kernel()
    if not active_kernel:
        raise HTTPException(status_code=503, detail="Kiwi Brain kernel is not initialized")

    router = None
    memory = None

    if hasattr(active_kernel, "get_module"):
        router = active_kernel.get_module("model_router")
        memory = active_kernel.get_module("memory_engine")

    if not router:
        router = getattr(active_kernel, "model_router", None)
    if not memory:
        memory = getattr(active_kernel, "memory", None)

    if not router:
        raise HTTPException(status_code=503, detail="Kiwi Brain ModelRouter is not available")

    return router, memory


@app.get("/health")
async def health_check():
    """Health check endpoint queried by the Go API Gateway."""
    active_kernel = _get_active_kernel()
    return {
        "status": "ok",
        "service": "kiwi-brain",
        "version": "0.1.0",
        "kernel_ready": active_kernel is not None,
    }


@app.post("/internal/chat", response_model=InternalChatResponse)
async def internal_chat(req: InternalChatRequest):
    """Synchronous internal chat endpoint called by Go Gateway POST /api/secure/chat."""
    clean_message = (req.message or "").strip()
    if not clean_message:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    router, memory = _get_router_and_memory()
    conv_id = req.conversation_id or req.session_id or f"conv-{uuid.uuid4().hex[:8]}"
    user_id = req.user_id or "default"

    start_ts = time.perf_counter()
    history = memory.get_chat_history(conv_id, limit=10) if (memory and hasattr(memory, "get_chat_history")) else []
    prompt = build_chat_prompt(clean_message, history=history, context=req.context)
    preferred_adapter = router.decide_model(clean_message)

    try:
        exec_res = await router.generate_with_fallback(
            prompt=prompt,
            system=KIWI_SYSTEM_PROMPT,
            preferred_adapter=preferred_adapter,
        )
        reply_text = exec_res.get("output", "") if isinstance(exec_res, dict) else str(exec_res)
        model_used = (
            exec_res.get("model_name", getattr(preferred_adapter, "model_id", str(preferred_adapter)))
            if isinstance(exec_res, dict)
            else getattr(preferred_adapter, "model_id", str(preferred_adapter))
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model generation failed: {e}")

    if memory and hasattr(memory, "store_chat"):
        memory.store_chat(conv_id, "user", clean_message)
        memory.store_chat(conv_id, "assistant", reply_text)

    elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)

    return InternalChatResponse(
        response=reply_text,
        reply=reply_text,
        conversation_id=conv_id,
        session_id=conv_id,
        model_used=model_used,
        metadata={
            "user_id": user_id,
            "latency_ms": elapsed_ms,
            "memory_degraded": getattr(memory, "degraded", False) if memory else True,
        },
    )


@app.post("/internal/chat/stream")
async def internal_chat_stream(req: InternalChatRequest):
    """
    Server-Sent Events (SSE) streaming endpoint called by Go Gateway WebSocket Hub.
    Emits:
      data: {"token": "<chunk>"}\n\n
      data: {"done": true}\n\n
    """
    clean_message = (req.message or "").strip()
    if not clean_message:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    router, memory = _get_router_and_memory()
    conv_id = req.conversation_id or req.session_id or f"conv-{uuid.uuid4().hex[:8]}"

    history = memory.get_chat_history(conv_id, limit=10) if (memory and hasattr(memory, "get_chat_history")) else []
    prompt = build_chat_prompt(clean_message, history=history, context=req.context)
    preferred_adapter = router.decide_model(clean_message)

    async def event_generator():
        collected_tokens: List[str] = []
        try:
            async for token in router.stream_generate(
                prompt=prompt,
                system=KIWI_SYSTEM_PROMPT,
                preferred_adapter=preferred_adapter,
            ):
                if token:
                    collected_tokens.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"

            full_reply = "".join(collected_tokens).strip()
            if full_reply and memory and hasattr(memory, "store_chat"):
                memory.store_chat(conv_id, "user", clean_message)
                memory.store_chat(conv_id, "assistant", full_reply)

            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            print(f"[KiwiBrain] Error during stream_generate: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


_notifications: List[dict] = []


class JobFireRequest(BaseModel):
    job: Dict[str, Any]


class ApprovalDecision(BaseModel):
    allow: bool


@app.get("/internal/approvals")
async def list_approvals():
    from vault.store import VaultStore

    return {"approvals": VaultStore().pending_approvals()}


@app.post("/internal/approvals/{approval_id}")
async def decide_approval(approval_id: str, body: ApprovalDecision):
    from vault.store import VaultError, VaultStore

    try:
        record = VaultStore().resolve_approval(approval_id, body.allow)
    except VaultError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"approval": record}


@app.get("/internal/notifications")
async def list_notifications():
    rows = list(_notifications)
    _notifications.clear()
    return {"notifications": rows}


@app.post("/internal/jobs/fire")
async def fire_job(req: JobFireRequest):
    """Called by pip-cron. Notify the phone, or open a page, and record the state."""
    job = req.job or {}
    payload = job.get("payload") or {}
    name = job.get("name", "")
    if payload.get("type") == "notify":
        note = {
            "job": name,
            "message": payload.get("message", ""),
            "state": "nudge",
        }
        _notifications.append(note)
        return {"status": "ok", "state": "nudge"}
    if payload.get("tool") == "browser_open":
        from tools.library.desktop import BrowserOpen

        result = await BrowserOpen().execute(url=payload.get("url", ""))
        state = "done" if result.get("status") == "ok" else "blocked"
        _notifications.append(
            {
                "job": name,
                "message": payload.get("url", ""),
                "state": state,
            }
        )
        return {"status": "ok", "state": state, "result": result}
    _notifications.append({"job": name, "message": "", "state": "working"})
    return {"status": "ok", "state": "working"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/task")
async def submit_task(req: TaskRequest):
    active_kernel = _get_active_kernel()
    if not active_kernel:
        return {"status": "error", "message": "Kernel not initialized"}

    task_desc = req.task or req.goal or ""
    task_id = f"web_task_{uuid.uuid4().hex[:8]}"
    task_event = Event(
        source="web_ui",
        destination="scheduler",
        event_type="task.create",
        payload={"task": {"id": task_id, "description": task_desc, "requester": "web_ui"}},
    )
    await active_kernel.send_event(task_event)
    return {"status": "success", "task_id": task_id}
