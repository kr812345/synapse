from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class GitHubWorker(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="research", role="worker")

    def allowed_tools(self) -> List[str]:
        return ["github_api", "browser"]

    def forbidden_actions(self) -> List[str]:
        return ["create_issue", "push_code"]

    def memory_access_level(self) -> str:
        return "read_only"

    def can_handle(self, task_description: str) -> bool:
        return "github" in task_description.lower() or "repo" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked github research"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
