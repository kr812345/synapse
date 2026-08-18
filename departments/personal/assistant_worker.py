from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class AssistantWorker(BaseAgent):
    def __init__(self, id: str = "assistant_w1", name: str = "Charlie Assistant"):
        super().__init__(id=id, name=name, department="personal", role="assistant")

    def allowed_tools(self) -> List[str]:
        return ["calendar", "email", "ppt_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_emails"]

    def memory_access_level(self) -> str:
        return "high"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return any(k in desc for k in ["schedule", "calendar", "email", "personal", "agenda", "meeting", "reminder"])

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            desc = task_dict.get("description", str(task))
            task_id = task_dict.get("id", "unknown")
            action_req = task_dict.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            task_id = getattr(task, "id", "unknown")
            action_req = getattr(task, "action", "")
            task_dict = {"description": desc}
        else:
            desc = str(task)
            task_id = "unknown"
            action_req = ""
            task_dict = {"description": desc}

        if action_req in self.forbidden_actions():
            raise PermissionError(f"Action '{action_req}' is forbidden for agent {self.name}")

        desc_lower = desc.lower()

        if any(k in desc_lower for k in ["calendar", "schedule", "meeting", "agenda"]):
            action = "calendar_management"
            details = f"Processed schedule/calendar task '{desc}'. Calendar events updated."
        elif any(k in desc_lower for k in ["email", "message", "inbox"]):
            action = "email_processing"
            details = f"Processed email task '{desc}'. Drafted/reviewed messages (delete_emails action forbidden)."
        else:
            action = "general_assistant_task"
            details = f"Processed assistant task '{desc}'."

        return {
            "status": "success",
            "worker": self.name,
            "task_id": task_id,
            "action": action,
            "task": task,
            "result": {
                "summary": details,
                "tools_used": self.allowed_tools(),
                "output": details
            }
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
