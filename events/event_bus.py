from shared.models import Event
from shared.interfaces import Module
import asyncio
import fnmatch
import logging
from typing import Dict, List, Set, Type, Optional, Any
from collections import defaultdict
from datetime import datetime, timezone
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventBus(Module):
    def __init__(self):
        self.subscribers: Dict[str, Module] = {}
        self.topic_subscribers: Dict[str, Set[Module]] = defaultdict(set)
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self.payload_schemas: Dict[str, Type[BaseModel]] = {}
        
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._running: bool = False
        
        self._events_processed: int = 0
        self._error_count: int = 0

    @property
    def name(self) -> str:
        return "event_bus"

    def register_subscriber(self, module: Module) -> None:
        if module.name in self.subscribers:
            logger.warning(f"Module {module.name} is already registered.")
        self.subscribers[module.name] = module
        logger.info(f"Registered module: {module.name}")

    def unregister_subscriber(self, module_name: str) -> None:
        if module_name in self.subscribers:
            del self.subscribers[module_name]
            logger.info(f"Unregistered module: {module_name}")
        
        # Remove from topic subscriptions as well
        for pattern, mods in list(self.topic_subscribers.items()):
            self.topic_subscribers[pattern] = {m for m in mods if m.name != module_name}

    def subscribe_topic(self, module: Module, topic_pattern: str) -> None:
        """Subscribe a module to event types matching a topic pattern (fnmatch wildcard)."""
        self.topic_subscribers[topic_pattern].add(module)
        logger.info(f"Module {module.name} subscribed to topic pattern: {topic_pattern}")

    def unsubscribe_topic(self, module: Module, topic_pattern: str) -> None:
        """Unsubscribe a module from a specific topic pattern."""
        if topic_pattern in self.topic_subscribers:
            self.topic_subscribers[topic_pattern].discard(module)

    def register_payload_schema(self, event_type: str, schema_cls: Type[BaseModel]) -> None:
        """Register a Pydantic schema class for validating payload of a specific event type."""
        self.payload_schemas[event_type] = schema_cls

    def validate_payload(self, event: Event) -> bool:
        """Validate event payload against registered schema if present."""
        if event.event_type in self.payload_schemas:
            schema_cls = self.payload_schemas[event.event_type]
            try:
                if hasattr(schema_cls, "model_validate"):
                    schema_cls.model_validate(event.payload)
                else:
                    schema_cls(**event.payload)
                return True
            except Exception as exc:
                logger.error(f"Payload validation failed for event {event.id} ({event.event_type}): {exc}")
                self.dead_letter_queue.append({
                    "event": event.model_dump() if hasattr(event, "model_dump") else event.__dict__,
                    "reason": f"Payload validation failed: {exc}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                return False
        return True

    async def start(self) -> None:
        """Start background queue processing task."""
        if not self._running:
            self._queue = asyncio.Queue()
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())

    async def shutdown(self) -> None:
        """Stop background queue processing task and drain remaining events."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def publish(self, event: Event) -> None:
        """Asynchronously enqueue an event for decoupled background processing."""
        if self._queue is not None and self._running:
            await self._queue.put(event)
        else:
            await self.handle_event(event)

    async def _process_queue(self) -> None:
        """Background worker processing events from the queue."""
        while self._running:
            try:
                if self._queue is None:
                    break
                event = await self._queue.get()
                await self.handle_event(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in queue processing worker: {exc}", exc_info=True)

    async def handle_event(self, event: Event) -> None:
        """Routes event to subscribers (unicast, broadcast, or topic subscribers) with error isolation."""
        logger.info(f"Routing event: {event.event_type} from {event.source} to {event.destination}")
        
        # 1. Payload validation
        if not self.validate_payload(event):
            return

        target_modules: Set[Module] = set()

        # 2. Destination matching (Broadcast vs Unicast)
        if event.destination == "*":
            for name, module in self.subscribers.items():
                if name != event.source:
                    target_modules.add(module)
        elif event.destination in self.subscribers:
            target_modules.add(self.subscribers[event.destination])

        # 3. Topic pattern matching
        for pattern, modules in self.topic_subscribers.items():
            if fnmatch.fnmatch(event.event_type, pattern):
                for module in modules:
                    if module.name != event.source:
                        target_modules.add(module)

        # 4. Dead-letter check for unroutable events
        if not target_modules and event.destination != "*":
            logger.error(f"Destination {event.destination} or topic pattern not found for event {event.id}")
            self.dead_letter_queue.append({
                "event": event.model_dump() if hasattr(event, "model_dump") else event.__dict__,
                "reason": f"No target subscriber found for destination '{event.destination}' or event_type '{event.event_type}'",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return

        # 5. Delivery with Error Boundary Isolation
        self._events_processed += 1

        async def safe_deliver(module: Module) -> None:
            try:
                await module.handle_event(event)
            except Exception as exc:
                self._error_count += 1
                logger.error(f"Handler exception in module '{module.name}' for event {event.id}: {exc}", exc_info=True)
                self.dead_letter_queue.append({
                    "event": event.model_dump() if hasattr(event, "model_dump") else event.__dict__,
                    "reason": f"Handler exception in module '{module.name}': {exc}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        if target_modules:
            await asyncio.gather(*[safe_deliver(m) for m in target_modules])

    def get_dead_letters(self) -> List[Dict[str, Any]]:
        """Return copies of dead-letter queue records."""
        return list(self.dead_letter_queue)

    def clear_dead_letters(self) -> None:
        """Clear the dead-letter queue."""
        self.dead_letter_queue.clear()

    async def reprocess_dead_letters(self) -> List[Event]:
        """Attempt to re-route all events currently in the dead-letter queue."""
        letters = list(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        reprocessed: List[Event] = []

        for record in letters:
            raw_evt = record.get("event")
            if isinstance(raw_evt, dict):
                evt = Event(**raw_evt)
            elif isinstance(raw_evt, Event):
                evt = raw_evt
            else:
                continue

            await self.handle_event(evt)
            reprocessed.append(evt)

        return reprocessed

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for EventBus."""
        return {
            "subscribers": len(self.subscribers),
            "topic_subscriptions": sum(len(mods) for mods in self.topic_subscribers.values()),
            "events_processed": self._events_processed,
            "errors": self._error_count,
            "dlq_size": len(self.dead_letter_queue)
        }

