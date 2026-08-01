from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class BackendWorker(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="engineering", role="backend_developer")

    def allowed_tools(self) -> List[str]:
        return ["terminal", "ide"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_database"]

    def memory_access_level(self) -> str:
        return "high"

    def can_handle(self, task_description: str) -> bool:
        return "backend" in task_description.lower() or "api" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked backend result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
