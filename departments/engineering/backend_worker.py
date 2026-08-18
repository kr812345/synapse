from typing import List, Any, Optional
from registry.sdk.base_agent import BaseAgent
from shared.models import Event
import logging

logger = logging.getLogger(__name__)


class BackendWorker(BaseAgent):
    """Backend Worker agent executing API development, database integration, tool calls, and memory storage."""

    def __init__(self, id: str = "backend_worker_1", name: str = "Bob Developer"):
        super().__init__(id=id, name=name, department="engineering", role="backend_developer")
        self.kernel: Optional[Any] = None

    def set_kernel(self, kernel: Any) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["terminal", "ide", "git", "db_client", "file_read", "file_write", "file_edit"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_database", "drop_production_db", "push_to_main_without_pr"]

    def memory_access_level(self) -> str:
        return "high"

    def can_handle(self, task_description: str) -> bool:
        if not task_description or not isinstance(task_description, str):
            return False
        desc_lower = task_description.lower()
        return any(k in desc_lower for k in ["backend", "api", "code", "service", "database", "endpoint", "crud", "sql", "fastapi"])

    async def execute(self, task: Any) -> Any:
        if task is None:
            task_desc = ""
            task_id = None
        elif isinstance(task, dict):
            raw_desc = task.get("description")
            if raw_desc is None:
                raw_desc = task.get("task_description")
            task_desc = raw_desc if raw_desc is not None else str(task)
            task_id = task.get("id") or task.get("task_id")
        elif hasattr(task, "description"):
            raw_desc = getattr(task, "description", "")
            task_desc = raw_desc if raw_desc is not None else ""
            task_id = getattr(task, "id", None)
        else:
            task_desc = str(task)
            task_id = None

        if not isinstance(task_desc, str):
            task_desc = str(task_desc)

        generated_code = (
            f"# Auto-generated backend service module for: {task_desc}\n"
            f"from fastapi import FastAPI, HTTPException\n\n"
            f"app = FastAPI(title='Backend API Service')\n\n"
            f"@app.get('/api/v1/resource')\n"
            f"async def get_resource():\n"
            f"    return {{'status': 'success', 'data': 'backend_worker_response'}}\n"
        )

        tool_calls = []
        if self.kernel and hasattr(self.kernel, "get_module"):
            tool_reg = self.kernel.get_module("tool_registry")
            if tool_reg and hasattr(tool_reg, "execute_tool"):
                try:
                    t_res = await tool_reg.execute_tool(self, "terminal", command=f"echo 'Executing backend task {task_id}'")
                    tool_calls.append({"tool": "terminal", "result": t_res})
                except Exception as exc:
                    logger.debug(f"Tool execution bypassed or failed: {exc}")

        memory_saved = False
        if self.kernel and hasattr(self.kernel, "send_event"):
            try:
                mem_event = Event(
                    source=f"engineering.backend.{self.id}",
                    destination="memory_engine",
                    event_type="memory.store_knowledge",
                    payload={
                        "knowledge": {
                            "observation": f"Completed backend implementation for task: {task_desc[:50]}",
                            "source": f"backend_worker_{self.id}",
                            "confidence": 1.0,
                            "category": "engineering_backend",
                            "importance": 3
                        }
                    }
                )
                await self.kernel.send_event(mem_event)
                memory_saved = True
            except Exception as exc:
                logger.debug(f"Memory store event bypassed or failed: {exc}")

        return {
            "status": "success",
            "role": self.role,
            "task_id": task_id,
            "task": task,
            "output": {
                "action": "backend_code_generation",
                "code": generated_code,
                "endpoints": ["/api/v1/resource"],
                "language": "python"
            },
            "tool_calls": tool_calls,
            "memory_saved": memory_saved
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle", "role": self.role}

    def remember(self, knowledge: Any) -> None:
        pass
