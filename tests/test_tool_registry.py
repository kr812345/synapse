import pytest
from tools.tool_registry import ToolRegistry, ToolInterface, PermissionDenied
from registry.sdk.base_agent import BaseAgent
from typing import List, Any
import asyncio

class DummyTool(ToolInterface):
    name = "dummy"
    description = "Dummy tool"
    parameters = {}
    required_permissions = []

    async def execute(self, **kwargs) -> Any:
        return "success"

class DummyAgent(BaseAgent):
    def __init__(self, allowed: List[str]):
        super().__init__(id="1", name="Agent", department="Dept", role="Role")
        self._allowed = allowed

    def allowed_tools(self) -> List[str]:
        return self._allowed

    def forbidden_actions(self) -> List[str]:
        return []

    def memory_access_level(self) -> str:
        return "none"

    def can_handle(self, task_description: str) -> bool:
        return True

    async def execute(self, task: Any) -> Any:
        return None

    def validate(self, result: Any) -> bool:
        return True

    def report(self) -> Any:
        return None

    def remember(self, knowledge: Any) -> None:
        pass

@pytest.mark.asyncio
async def test_tool_execution():
    registry = ToolRegistry()
    registry.register(DummyTool())
    
    agent_allowed = DummyAgent(allowed=["dummy"])
    result = await registry.execute_tool(agent_allowed, "dummy")
    assert result == "success"
    
    agent_denied = DummyAgent(allowed=[])
    with pytest.raises(PermissionDenied):
        await registry.execute_tool(agent_denied, "dummy")
