from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class RedditWorker(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="research", role="worker")

    def allowed_tools(self) -> List[str]:
        return ["reddit_api", "browser"]

    def forbidden_actions(self) -> List[str]:
        return ["post_comment", "upvote"]

    def memory_access_level(self) -> str:
        return "read_only"

    def can_handle(self, task_description: str) -> bool:
        return "reddit" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked reddit research"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
