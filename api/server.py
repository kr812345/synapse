from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.models import Event
import asyncio
import json
from boot import boot_os
from shared.interfaces import Module

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
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
        # We broadcast any event that passes through the OS so the dashboard can see it
        await manager.broadcast(event.model_dump_json())

bridge = WebSocketBridge()
os_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Boot the OS when the server starts
    kernel, registry, scheduler = await boot_os()
    kernel.register_module(bridge)
    
    os_state['kernel'] = kernel
    os_state['registry'] = registry
    os_state['scheduler'] = scheduler
    print("[SERVER] Connected OS to API Server.")
    yield
    print("[SERVER] Shutting down OS...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # We can optionally handle incoming websocket messages here
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from pydantic import BaseModel
class TaskRequest(BaseModel):
    task: str

@app.post("/api/task")
async def submit_task(req: TaskRequest):
    kernel = os_state.get('kernel')
    if not kernel:
        return {"status": "error", "message": "Kernel not initialized"}
    
    import uuid
    task_id = f"web_task_{uuid.uuid4().hex[:8]}"
    task_event = Event(
        source="web_ui",
        destination="scheduler",
        event_type="task.create",
        payload={"task": {"id": task_id, "description": req.task, "requester": "web_ui"}}
    )
    await kernel.send_event(task_event)
    return {"status": "success", "task_id": task_id}
