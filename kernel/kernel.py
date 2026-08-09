from shared.interfaces import KernelInterface, Module
from shared.models import Event
from events.event_bus import EventBus
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Kernel(KernelInterface):
    def __init__(self):
        self.event_bus = EventBus()
        self.modules: Dict[str, Module] = {}
        self.started_at: datetime = datetime.now(timezone.utc)

    def register_module(self, module: Module) -> None:
        """Register a module to the OS with interface enforcement and reference injection."""
        if not isinstance(module, Module):
            raise TypeError(f"Module '{module}' must implement Module interface")
        if not hasattr(module, "name") or not module.name or not isinstance(module.name, str):
            raise ValueError("Module must have a valid non-empty 'name' property")

        self.modules[module.name] = module
        self.event_bus.register_subscriber(module)
        
        # Inject kernel reference if supported
        if hasattr(module, 'set_kernel') and callable(module.set_kernel):
            module.set_kernel(self)

        logger.info(f"Successfully registered module: {module.name}")

    def unregister_module(self, module_name: str) -> None:
        """Unregister a module dynamically at runtime."""
        if module_name in self.modules:
            del self.modules[module_name]
            self.event_bus.unregister_subscriber(module_name)
            logger.info(f"Unregistered module: {module_name}")

    def get_module(self, module_name: str) -> Optional[Module]:
        """Retrieve a registered module by name."""
        return self.modules.get(module_name)

    def has_module(self, module_name: str) -> bool:
        """Check if a module is currently registered."""
        return module_name in self.modules

    def list_modules(self) -> List[str]:
        """List all currently registered module names."""
        return list(self.modules.keys())

    async def send_event(self, event: Event) -> None:
        """Submit an event to the Kernel to be routed via EventBus."""
        await self.event_bus.handle_event(event)

    async def shutdown(self) -> None:
        """Broadcast system.shutdown event and gracefully terminate EventBus."""
        shutdown_event = Event(
            source="kernel",
            destination="*",
            event_type="system.shutdown",
            payload={}
        )
        await self.send_event(shutdown_event)
        if hasattr(self.event_bus, "shutdown") and callable(self.event_bus.shutdown):
            await self.event_bus.shutdown()

    def get_health_status(self) -> Dict[str, Any]:
        """Return comprehensive health metrics and registered module overview."""
        uptime_seconds = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        event_bus_stats = self.event_bus.get_stats() if hasattr(self.event_bus, "get_stats") else {}
        return {
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "modules": self.list_modules(),
            "module_count": len(self.modules),
            "event_bus": event_bus_stats
        }

