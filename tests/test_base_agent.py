import pytest
from registry.sdk.base_agent import BaseAgent
from typing import List, Any

class DummyAgent(BaseAgent):
    def allowed_tools(self) -> List[str]:
        return ["browser"]

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "read-only"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        return {"status": "done"}

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return "report"

    def remember(self, knowledge: Any) -> None:
        pass

def test_dummy_agent():
    agent = DummyAgent(id="1", name="Agent1", department="Test", role="Tester")
    assert agent.id == "1"
    assert agent.allowed_tools() == ["browser"]
    assert agent.memory_access_level() == "read-only"
