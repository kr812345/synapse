# 11. Development Milestones

To prevent the OS from becoming a tangled mess, development is strictly gated by milestones. Every milestone must result in a fully runnable, tested state before progressing.

## Phase 0: Architecture (Current)
- Deliverables: The Technical Design Document (TDD).
- Status: **COMPLETE**

## Phase 1: Kernel & Infrastructure
1. **Milestone 1**: AI OS Kernel Core API.
2. **Milestone 2**: Event Bus (In-memory routing).
3. **Milestone 3**: Agent Registry (Data models and directory).
4. **Milestone 4**: Task Scheduler (Task models and basic state machine).
5. **Milestone 5**: Memory Engine (In-memory MVP).
6. **Milestone 6**: Model Router (Stubbed routing logic).

## Phase 2: Agent SDK & Tools
7. **Milestone 7**: The `BaseAgent` SDK implementation.
8. **Milestone 8**: Tool Registry and Standard Library (Filesystem, Browser).

## Phase 3: The First Department
9. **Milestone 9**: Research Department Setup.
   - Implement Research Manager.
   - Implement Reddit Worker, GitHub Worker, HN Worker.
10. **Milestone 10**: End-to-End Test.
    - Submit a task via CLI: "Research AI startup ideas on Reddit and HN."
    - Verify DAG execution, tool usage, artifact generation, and memory storage.

## Phase 4: Database Integration
11. **Milestone 11**: Swap in-memory `MemoryEngine` for PostgreSQL + pgvector.
12. **Milestone 12**: Swap in-memory state tracking for PostgreSQL ledgers (`events`, `tasks` tables).

## Phase 5: The Dashboard
13. **Milestone 13**: Next.js / TypeScript Web App initialization.
14. **Milestone 14**: WebSocket integration with the AI OS Kernel.
15. **Milestone 15**: Live Rendering (DAG visualization, Agent hierarchy, Logs).

## Phase 6: Expansion
16. **Milestone 16**: Engineering Department.
17. **Milestone 17**: Marketing Department.
18. **Milestone 18**: Personal Department.

## Rules for Progression:
- Never skip documentation.
- Never write placeholder code that cannot scale (e.g., using a global variable instead of the Event Bus).
- Prefer composition over inheritance everywhere except the `BaseAgent` interface.
