from abc import ABC, abstractmethod
from shared.models import Event

class Module(ABC):
    """Base class for all AI OS modules (Departments, Scheduler, Memory, etc.)"""
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Process an incoming event directed to this module."""
        pass

class KernelInterface(ABC):
    @abstractmethod
    def register_module(self, module: Module) -> None:
        pass
        
    @abstractmethod
    async def send_event(self, event: Event) -> None:
        pass
