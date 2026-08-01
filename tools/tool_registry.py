from abc import ABC, abstractmethod
from typing import Any, Dict, List

class ToolInterface(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str]

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

class PermissionDenied(Exception):
    pass

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolInterface] = {}

    def register(self, tool: ToolInterface):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolInterface:
        return self._tools.get(name)

    async def execute_tool(self, agent: Any, name: str, **kwargs) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if name not in agent.allowed_tools():
            raise PermissionDenied(f"Agent {agent.id} does not have permission to execute {name}")

        return await tool.execute(**kwargs)
