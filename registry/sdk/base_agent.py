from abc import ABC, abstractmethod
from typing import List, Any

class BaseAgent(ABC):
    def __init__(self, id: str, name: str, department: str, role: str, confidence_score: float = 0.0):
        self.id = id
        self.name = name
        self.department = department
        self.role = role
        self.confidence_score = confidence_score

    @abstractmethod
    def allowed_tools(self) -> List[str]:
        pass

    @abstractmethod
    def forbidden_actions(self) -> List[str]:
        pass

    @abstractmethod
    def memory_access_level(self) -> str:
        pass

    @abstractmethod
    def can_handle(self, task_description: str) -> bool:
        pass

    @abstractmethod
    async def execute(self, task: Any) -> Any:
        pass

    @abstractmethod
    def validate(self, result: Any) -> bool:
        pass

    @abstractmethod
    def report(self) -> Any:
        pass

    @abstractmethod
    def remember(self, knowledge: Any) -> None:
        pass
