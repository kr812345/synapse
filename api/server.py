from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from kernel.kernel import Kernel
from shared.models import Event
import asyncio
import json

app = FastAPI()

# A global reference for the websocket active connections
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from shared.interfaces import Module

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

# Global bridge instance to be registered with the kernel in main.py
bridge = WebSocketBridge()
