from shared.interfaces import KernelInterface, Module
from shared.models import Event
from events.event_bus import EventBus
import logging

logger = logging.getLogger(__name__)

class Kernel(KernelInterface):
    def __init__(self):
        self.event_bus = EventBus()
        self.modules = {}

    def register_module(self, module: Module) -> None:
        """Register a module to the OS and attach it to the Event Bus."""
        self.modules[module.name] = module
        self.event_bus.register_subscriber(module)
        
        # Inject kernel reference if the module supports it
        if hasattr(module, 'set_kernel'):
            module.set_kernel(self)

    async def send_event(self, event: Event) -> None:
        """Submit an event to the Kernel to be routed."""
        await self.event_bus.handle_event(event)
        
    async def shutdown(self):
        """Fire a system shutdown broadcast event."""
        await self.send_event(Event(source="kernel", destination="*", event_type="system.shutdown", payload={}))
