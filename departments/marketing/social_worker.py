from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class SocialWorker(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="marketing", role="social_media_manager")

    def allowed_tools(self) -> List[str]:
        return ["twitter", "linkedin"]

    def forbidden_actions(self) -> List[str]:
        return ["post_without_approval"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        return "social" in task_description.lower() or "marketing" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked social media result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
