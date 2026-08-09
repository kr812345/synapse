from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from shared.interfaces import Module, KernelInterface
from shared.models import Event

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

class ToolRegistry(Module):
    def __init__(self):
        self._tools: Dict[str, ToolInterface] = {}
        self.kernel: Optional[KernelInterface] = None

    @property
    def name(self) -> str:
        return "tool_registry"

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def register(self, tool: ToolInterface):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolInterface]:
        return self._tools.get(name)

    async def execute_tool(self, agent: Any, name: str, **kwargs) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if hasattr(agent, "allowed_tools"):
            allowed = agent.allowed_tools() if callable(agent.allowed_tools) else agent.allowed_tools
        else:
            allowed = []

        if name not in allowed:
            agent_id = getattr(agent, "id", str(agent))
            raise PermissionDenied(f"Agent {agent_id} does not have permission to execute {name}")

        return await tool.execute(**kwargs)

    async def handle_event(self, event: Event) -> None:
        """
        Event handling contract for ToolRegistry module:
        - Listens for 'tool.execute' events.
        - Payload structure: {'tool_name': str, 'agent': dict or object, 'kwargs': dict}
        - Executes requested tool and emits 'tool.execution_result' or 'tool.execution_failed' event.
        """
        if event.event_type == "tool.execute":
            tool_name = event.payload.get("tool_name")
            agent_info = event.payload.get("agent", {})
            kwargs = event.payload.get("kwargs", {})

            class AgentProxy:
                def __init__(self, agent_id, allowed_list):
                    self.id = agent_id
                    self._allowed = allowed_list
                def allowed_tools(self):
                    return self._allowed

            if isinstance(agent_info, dict):
                agent_id = agent_info.get("id", event.source)
                allowed_list = agent_info.get("allowed_tools", [])
                agent_obj = AgentProxy(agent_id, allowed_list)
            else:
                agent_obj = agent_info

            try:
                result = await self.execute_tool(agent_obj, tool_name, **kwargs)
                if self.kernel:
                    resp_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="tool.execution_result",
                        payload={
                            "tool_name": tool_name,
                            "status": "success",
                            "result": result
                        }
                    )
                    await self.kernel.send_event(resp_event)
            except Exception as exc:
                if self.kernel:
                    err_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="tool.execution_failed",
                        payload={
                            "tool_name": tool_name,
                            "status": "failed",
                            "error": str(exc)
                        }
                    )
                    await self.kernel.send_event(err_event)

