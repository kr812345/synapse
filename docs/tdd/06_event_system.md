# 6. Event System

The Event Bus is the only way components in the AI OS communicate. There are no synchronous HTTP requests between internal departments, and no direct Python method calls between modules.

## 6.1 The Event Envelope
Every message in the system conforms to the `Event` schema:

```json
{
  "id": "event-uuid-9999",
  "source": "research_manager",
  "destination": "scheduler",
  "event_type": "task.create",
  "payload": {
    "task": {
      "description": "Analyze Reddit for AI startup ideas",
      "priority": "high"
    }
  },
  "timestamp": "2026-08-02T10:00:00Z"
}
```

## 6.2 Standard Event Types
To ensure predictability, the OS defines a strict registry of event types:

### Task Lifecycle
- `task.create`: Sent to the Scheduler to initiate a DAG.
- `task.assigned`: Emitted when an agent is matched.
- `task.executing`: Agent begins work.
- `task.completed`: Agent finished successfully. Payload includes the `artifact_id`.
- `task.failed`: Agent failed. Triggers retry or escalation.

### Memory & State
- `memory.store_knowledge`: Sent to Memory Engine to persist a fact.
- `memory.query`: Sent to Memory Engine to retrieve context.
- `artifact.created`: Sent when a file is written to disk.

### System
- `system.boot`: Emitted by Kernel on startup.
- `system.shutdown`: Graceful termination request.
- `module.registered`: When a new plugin comes online.

## 6.3 Routing Mechanisms
The Event Bus supports two routing paradigms:
1. **Point-to-Point (Unicast)**: The `destination` field is explicitly set (e.g., `"scheduler"`). Only the target module processes it.
2. **Broadcast (Pub/Sub)**: The `destination` field is `*`. All registered modules receive the event. Useful for `system.shutdown` or major state changes that the Dashboard needs to render.

## 6.4 Event Durability
In Phase 1, the Event Bus is an in-memory dictionary routing asyncio tasks. 
In Phase 3+, this can be hot-swapped for a Redis Pub/Sub or RabbitMQ broker, allowing the AI OS components to be distributed across physical servers without changing a single line of business logic.
