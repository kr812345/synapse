from shared.interfaces import Module, KernelInterface
from shared.models import Event
import logging

logger = logging.getLogger(__name__)

class EchoDepartment(Module):
    def __init__(self):
        self.kernel: KernelInterface = None
        
    @property
    def name(self) -> str:
        return "echo_department"
        
    def set_kernel(self, kernel: KernelInterface):
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        logger.info(f"EchoDepartment received event: {event.event_type} with payload: {event.payload}")
        if event.event_type == "ping":
            logger.info("EchoDepartment responding with pong...")
            response = Event(
                source=self.name,
                destination=event.source,
                event_type="pong",
                payload={"original_payload": event.payload}
            )
            if self.kernel:
                await self.kernel.send_event(response)
