from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class SocialWorker(BaseAgent):
    def __init__(self, id: str = "social_worker_1", name: str = "Alice Social"):
        super().__init__(id=id, name=name, department="marketing", role="social_media_manager")

    def allowed_tools(self) -> List[str]:
        return ["twitter", "linkedin"]

    def forbidden_actions(self) -> List[str]:
        return ["post_without_approval"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "social" in desc or "marketing" in desc or "twitter" in desc or "linkedin" in desc or "post" in desc

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            task_dict = task
            content = task_dict.get("content") or task_dict.get("description") or str(task)
            channel = task_dict.get("channel", "twitter")
            action = task_dict.get("action", "")
        elif hasattr(task, "description"):
            content = getattr(task, "description", str(task))
            channel = getattr(task, "channel", "twitter")
            action = getattr(task, "action", "")
            task_dict = {"description": content}
        else:
            content = str(task)
            channel = "twitter"
            action = ""
            task_dict = {"description": content}

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for agent {self.name}")

        formatted_post = f"[{channel.upper()}] {content}"

        return {
            "status": "success",
            "task": task,
            "channel": channel,
            "role": self.role,
            "post_content": formatted_post,
            "result": f"Social media post generated for channel: {channel}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
