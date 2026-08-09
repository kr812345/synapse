from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class ContentWorker(BaseAgent):
    def __init__(self, id: str = "content_worker_1", name: str = "Carol Content"):
        super().__init__(id=id, name=name, department="marketing", role="content_writer")

    def allowed_tools(self) -> List[str]:
        return ["cms_editor", "seo_analyzer"]

    def forbidden_actions(self) -> List[str]:
        return ["publish_unapproved_copy"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "content" in desc or "blog" in desc or "article" in desc or "copywriting" in desc

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            desc = task.get("description", str(task))
            action = task.get("action", "")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            action = getattr(task, "action", "")
        else:
            desc = str(task)
            action = ""

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        return {
            "status": "success",
            "role": self.role,
            "task": task,
            "result": f"content article generated for task: {desc}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
