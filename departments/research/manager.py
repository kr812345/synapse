from typing import List, Any
from registry.sdk.base_agent import BaseAgent
from .reddit_worker import RedditWorker
from .github_worker import GitHubWorker
from .hn_worker import HNWorker

class ResearchManager(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="research", role="manager")
        self.workers = [
            RedditWorker(f"{id}_reddit", "Reddit Researcher"),
            GitHubWorker(f"{id}_github", "GitHub Researcher"),
            HNWorker(f"{id}_hn", "HackerNews Researcher")
        ]

    def allowed_tools(self) -> List[str]:
        return ["search", "browser"]

    def forbidden_actions(self) -> List[str]:
        return ["post_content", "delete_content"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        return "research" in task_description.lower() or "find" in task_description.lower() or "analyze" in task_description.lower()

    async def execute(self, task: Any) -> Any:
        return {"status": "success", "task": task, "result": "mocked research manager result"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return {"status": "managing research"}

    def remember(self, knowledge: Any) -> None:
        pass
