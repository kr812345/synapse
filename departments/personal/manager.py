from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from .assistant_worker import AssistantWorker

class PersonalManager(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="personal", role="manager")
        self.workers = [AssistantWorker(f"{id}_worker1", "Charlie")]

    def allowed_tools(self) -> List[str]:
        return ["contacts", "finances"]

    def forbidden_actions(self) -> List[str]:
        return ["authorize_payments"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "personal" in task_description.lower() or "life" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked personal manager result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass
