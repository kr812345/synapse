from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class OutreachWorker(BaseAgent):
    def __init__(self, id: str = "outreach_w1", name: str = "Oscar Outreach"):
        super().__init__(id=id, name=name, department="sales", role="outreach_specialist")

    def allowed_tools(self) -> List[str]:
        return ["email_draft", "pitch_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["send_spam_blast"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "pitch" in desc or "outreach" in desc or "email" in desc or "sales" in desc

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            desc = task_dict.get("description", str(task))
            action = task_dict.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            action = getattr(task, "action", "")
            task_dict = {"description": desc}
        else:
            desc = str(task)
            action = ""
            task_dict = {"description": desc}

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        return {
            "status": "success",
            "role": self.role,
            "task": task,
            "result": f"custom sales pitch generated for: {desc}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass

# Alias for feature and test naming compatibility
SalesWorker = OutreachWorker
