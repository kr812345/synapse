# 9. API Contracts

While internal communication is entirely event-driven via the Event Bus, the AI OS exposes a strictly typed API boundary for the Dashboard and external integrations. 

## 9.1 Dashboard API (WebSockets)

To support the real-time "Live Dashboard" (Phase 4), the OS spins up a WebSocket server. The Dashboard connects to this server and subscribes to the Event Bus in read-only mode.

### Outbound (OS -> Dashboard)
The Dashboard receives serialized `Event` objects.
- **Agent Status Updates**: Rendered instantly in the UI hierarchy.
- **DAG Progress**: Visual nodes turning from gray (pending) to blue (executing) to green (completed).
- **Live Logs**: Terminal-style output streamed directly from executing agents.

### Inbound (Dashboard -> OS)
The CEO can intervene in the OS via the Dashboard.
- `api.task.submit`: Triggers a `task.create` event in the OS.
- `api.tool.approve`: Resolves a pending HITL (Human-in-the-Loop) request.
- `api.system.halt`: Pauses the Scheduler (Emergency Stop).

## 9.2 Agent Contract Schema
The strict JSON schema that defines an Agent in the Registry.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "identity": { "type": "string" },
    "department": { "type": "string" },
    "goal": { "type": "string" },
    "responsibilities": {
      "type": "array",
      "items": { "type": "string" }
    },
    "forbidden_actions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "allowed_tools": {
      "type": "array",
      "items": { "type": "string" }
    },
    "memory_access": {
      "enum": ["none", "read-only", "read-write"]
    }
  },
  "required": ["identity", "department", "goal", "allowed_tools"]
}
```

## 9.3 Extensibility
Because the Kernel is completely decoupled from the transport layer, we can easily expose the OS via:
- REST API (FastAPI integration).
- gRPC (For inter-process communication with heavy ML services).
- Webhooks (To trigger external systems like Slack or Zapier on task completion).
