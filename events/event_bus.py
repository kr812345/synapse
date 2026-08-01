from shared.models import Event
from shared.interfaces import Module
import asyncio
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventBus(Module):
    def __init__(self):
        self.subscribers: Dict[str, Module] = {}

    @property
    def name(self) -> str:
        return "event_bus"

    def register_subscriber(self, module: Module) -> None:
        if module.name in self.subscribers:
            logger.warning(f"Module {module.name} is already registered.")
        self.subscribers[module.name] = module
        logger.info(f"Registered module: {module.name}")

    async def handle_event(self, event: Event) -> None:
        """The event bus itself routes events."""
        logger.info(f"Routing event: {event.event_type} from {event.source} to {event.destination}")
        
        # Broadcast
        if event.destination == "*":
            tasks = []
            for name, module in self.subscribers.items():
                if name != event.source:  # Don't send broadcast back to sender
                    tasks.append(module.handle_event(event))
            if tasks:
                await asyncio.gather(*tasks)
            return

        # Direct message
        if event.destination in self.subscribers:
            module = self.subscribers[event.destination]
            await module.handle_event(event)
        else:
            logger.error(f"Destination {event.destination} not found for event {event.id}")
