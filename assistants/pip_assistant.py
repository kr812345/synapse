"""The single assistant registered when the brain boots."""

from typing import Any, List

from registry.sdk.base_agent import BaseAgent

PIP_TOOLS = [
    "file_read",
    "file_write",
    "file_edit",
    "browser_open",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_fill_login",
    "vault_put",
    "vault_list",
    "models_list",
    "models_use",
    "models_install",
    "jobs_list",
    "jobs_create",
]


class PipAssistant(BaseAgent):
    def __init__(self, id: str = "pip", name: str = "Pip"):
        super().__init__(id=id, name=name, department="pip", role="assistant", confidence_score=0.9)
        self._notes: list[Any] = []

    def allowed_tools(self) -> List[str]:
        return list(PIP_TOOLS)

    def forbidden_actions(self) -> List[str]:
        return ["send", "pay", "sign", "delete", "use-credential", "install-cli"]

    def memory_access_level(self) -> str:
        return "workspace"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        description = task.get("description", str(task)) if isinstance(task, dict) else str(task)
        action = ""
        if isinstance(task, dict):
            action = str(task.get("action", ""))
        if action in self.forbidden_actions():
            return {
                "status": "approval_required",
                "action": action,
                "detail": description,
            }
        return {
            "status": "accepted",
            "assistant": self.name,
            "task": description,
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") in {"accepted", "approval_required", "success"}

    def report(self) -> Any:
        return {"id": self.id, "name": self.name, "department": self.department}

    def remember(self, knowledge: Any) -> None:
        self._notes.append(knowledge)
