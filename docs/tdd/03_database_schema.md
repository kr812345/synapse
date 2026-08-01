# 3. Database Schema

The AI OS requires a robust, relational, and vector-capable database. **PostgreSQL with the `pgvector` extension** is the chosen foundation.

## 3.1 Core Tables

### `events`
An immutable ledger of every action in the OS. Essential for debugging, auditing, and time-travel reconstruction.
- `id` (UUID, PK)
- `source` (VARCHAR)
- `destination` (VARCHAR)
- `event_type` (VARCHAR)
- `payload` (JSONB)
- `timestamp` (TIMESTAMPTZ, Indexed)

### `tasks`
Tracks the nodes in the Task Graphs (DAGs).
- `id` (UUID, PK)
- `parent_task_id` (UUID, FK -> tasks.id, Nullable)
- `description` (TEXT)
- `status` (VARCHAR: pending, executing, validating, completed, failed)
- `assigned_agent` (VARCHAR)
- `dependencies` (JSONB) - Array of task IDs that must complete before this one starts.
- `result_payload` (JSONB)
- `created_at` (TIMESTAMPTZ)
- `completed_at` (TIMESTAMPTZ)

### `artifacts`
Tracks the tangible outputs produced by agents.
- `id` (UUID, PK)
- `task_id` (UUID, FK -> tasks.id)
- `agent_id` (VARCHAR)
- `title` (VARCHAR)
- `file_path` (VARCHAR) - Where the actual markdown/code file lives on disk.
- `summary` (TEXT)
- `embedding` (VECTOR(768)) - pgvector column for semantic search over artifacts.
- `created_at` (TIMESTAMPTZ)

### `knowledge_graph` (Memory)
The structured long-term memory of the system. Instead of chat histories, we store atomic observations.
- `id` (UUID, PK)
- `observation` (TEXT) - The atomic fact (e.g., "Competitor X launched feature Y").
- `source` (VARCHAR) - Where this came from (e.g., URL, Task ID).
- `confidence` (FLOAT) - 0.0 to 1.0.
- `category` (VARCHAR) - e.g., 'competitor_analysis', 'user_preference'.
- `importance` (INT) - 1 to 10 scale.
- `embedding` (VECTOR(768)) - pgvector column for semantic retrieval.
- `expiration` (TIMESTAMPTZ, Nullable) - For temporal facts that decay.
- `created_at` (TIMESTAMPTZ)

### `agents`
Tracks the registered agents and their historical performance.
- `id` (VARCHAR, PK) - e.g., 'research_reddit_worker'.
- `department` (VARCHAR)
- `role` (VARCHAR)
- `total_tasks_completed` (INT)
- `success_rate` (FLOAT)
- `last_active` (TIMESTAMPTZ)

### `metrics`
For the Phase 4 Dashboard to render charts instantly.
- `id` (UUID, PK)
- `metric_name` (VARCHAR) - e.g., 'api_cost', 'tasks_per_hour'.
- `value` (FLOAT)
- `timestamp` (TIMESTAMPTZ)

## 3.2 Schema Design Principles
1. **JSONB for Flexibility**: `payload`, `dependencies`, and `result_payload` use JSONB. This allows the OS to evolve rapidly without constantly running schema migrations.
2. **Vector First**: `pgvector` is treated as a first-class citizen. Both `artifacts` and `knowledge_graph` are deeply embedded.
3. **Immutable Ledgers**: The `events` table is append-only. No updates, no deletes.
