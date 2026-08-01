from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from .backend_worker import BackendWorker

class EngineeringManager(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="engineering", role="manager")
        self.workers = [BackendWorker(f"{id}_worker1", "Bob")]

    def allowed_tools(self) -> List[str]:
        return ["jira", "github"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_repo"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "engineering" in task_description.lower() or "code" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked engineering manager result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass
