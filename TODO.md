# Synapse Project TODO

## Phase 3: Research Department Setup
- [x] Implement `ResearchManager` in `departments/research/manager.py`.
- [x] Implement `RedditWorker` in `departments/research/reddit_worker.py`.
- [x] Implement `GitHubWorker` in `departments/research/github_worker.py`.
- [x] Implement `HNWorker` in `departments/research/hn_worker.py`.
- [x] Register the Research Department agents in the registry. (Created structure)
- [x] Write tests for the Research Department.

## Phase 4: Database Integration
- [x] Update `memory/memory_engine.py` to use `psycopg2` or `asyncpg` to connect to PostgreSQL.
- [x] Update the schema to support `pgvector` for embeddings.
- [x] Migrate the `events`, `tasks`, `artifacts`, `knowledge_graph`, `agents`, and `metrics` tables to PostgreSQL.
- [x] Update unit tests in `tests/test_memory.py` to reflect the changes (using a test DB if needed).

## Phase 5: The Dashboard
- [x] Initialize a Next.js / TypeScript Web App in a new directory (e.g. `dashboard/`).
- [x] Build WebSocket integration within the AI OS Kernel to stream events.
- [x] Create live rendering components in the dashboard (DAG visualization, Agent hierarchy, Logs).

## Phase 6: Expansion (Integration & Testing)
- [x] Register `EngineeringManager` and `BackendWorker`.
- [x] Register `MarketingManager` and `SocialWorker`.
- [x] Register `PersonalManager` and `AssistantWorker`.
- [x] Write unit tests for all Phase 6 departments.
