from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class GithubWorker(BaseAgent):
    def __init__(self, id: str = "github_worker", name: str = "Github Worker", department: str = "Research", role: str = "Worker", confidence_score: float = 0.9):
        super().__init__(id, name, department, role, confidence_score)

    def allowed_tools(self) -> List[str]:
        return ["github_api_search", "github_repo_clone"]

    def forbidden_actions(self) -> List[str]:
        return ["commit_code", "push_code"]

    def memory_access_level(self) -> str:
        return "isolated"

    def can_handle(self, task_description: str) -> bool:
        return "github" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "source": "github", "data": []}

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict)

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
