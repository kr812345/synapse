from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from .social_worker import SocialWorker

class MarketingManager(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="marketing", role="manager")
        self.workers = [SocialWorker(f"{id}_worker1", "Alice")]

    def allowed_tools(self) -> List[str]:
        return ["analytics", "campaign_manager"]

    def forbidden_actions(self) -> List[str]:
        return ["spend_over_budget"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "marketing" in task_description.lower() or "campaign" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked marketing manager result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass
