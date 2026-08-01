from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class RedditWorker(BaseAgent):
    def __init__(self, id: str = "reddit_worker", name: str = "Reddit Worker", department: str = "Research", role: str = "Worker", confidence_score: float = 0.9):
        super().__init__(id, name, department, role, confidence_score)

    def allowed_tools(self) -> List[str]:
        return ["reddit_api_search"]

    def forbidden_actions(self) -> List[str]:
        return ["post_content"]

    def memory_access_level(self) -> str:
        return "isolated"

    def can_handle(self, task_description: str) -> bool:
        return "reddit" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "source": "reddit", "data": []}

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict)

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
