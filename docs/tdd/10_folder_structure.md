# 10. Folder Structure

The AI OS codebase is strictly organized to enforce the "Day 1 Senior Engineer" architectural boundaries. No circular dependencies are allowed.

```text
ai-os/
│
├── kernel/                 # Phase 1: Core
│   ├── kernel.py           # Kernel interface and module manager
│   └── exceptions.py
│
├── events/                 # Phase 2: Communication
│   ├── event_bus.py
│   └── routing.py
│
├── scheduler/              # Phase 3: Orchestration
│   ├── scheduler.py
│   ├── dag_builder.py      # Breaks complex tasks into graphs
│   └── task_queue.py
│
├── memory/                 # Phase 4: Persistence
│   ├── memory_engine.py
│   ├── pgvector_driver.py  # DB connection and vector logic
│   └── consolidator.py     # Background deduplication CRON
│
├── registry/               # Phase 5: HR
│   ├── agent_registry.py
│   └── sdk/                # BaseAgent and core interfaces
│       └── base_agent.py
│
├── models/                 # Phase 6: Compute
│   ├── model_router.py
│   ├── adapters/
│   │   ├── gemini.py
│   │   ├── openrouter.py
│   │   └── antigravity.py
│   └── cost_tracker.py
│
├── tools/                  # Phase 7: Capabilities
│   ├── tool_registry.py
│   ├── sandbox.py          # Execution environment
│   └── library/            # Standard tools
│       ├── browser.py
│       ├── github.py
│       └── filesystem.py
│
├── departments/            # Phase 8+: The Workforce
│   ├── research/
│   │   ├── manager.py
│   │   └── workers/
│   │       ├── reddit.py
│   │       └── github.py
│   ├── engineering/
│   ├── marketing/
│   └── personal/
│
├── shared/                 # Universal types
│   ├── models.py           # Pydantic (Event, Task, Knowledge, AgentContract)
│   └── interfaces.py       # Module ABCs
│
├── database/               # Migrations and schemas
│   └── migrations/
│
├── dashboard/              # Phase 10: Next.js Web UI
│   ├── app/
│   ├── components/
│   └── public/
│
├── artifacts/              # Generated outputs (Git-ignored)
│   ├── research/
│   └── code/
│
├── docs/                   # The TDD and architectural wikis
│   └── tdd/
│
├── tests/                  # Pytest suite mapping 1:1 with modules
│
└── main.py                 # The bootloader
```
