# Scope: Milestone 2 — Technical Departments (Engineering & Research)

## Scope Overview
Milestone 2 delivers functional backend logic for the Technical Departments (Engineering & Research), removing all mock responses and implementing real task execution, delegation, tool usage, memory integration, event bus interactions, defensive null-safety handling, and unit/integration tests.

## Feature Inventory

| # | Feature | Description | Milestone | File Boundaries | Status |
|---|---------|-------------|-----------|-----------------|--------|
| 1 | F-ENG-1 | Refactor `EngineeringManager` (`departments/engineering/manager.py`) to inherit `Module` and `BaseAgent`, register with Kernel, remove `"mocked engineering manager result"`, execute functional tasks | M2 | `departments/engineering/manager.py` | DONE |
| 2 | F-ENG-2 | Refactor `BackendWorker` (`departments/engineering/backend_worker.py`) to execute actual backend coding, API processing, tool calls, and memory storage, removing `"mocked backend result"` | M2 | `departments/engineering/backend_worker.py` | DONE |
| 3 | F-ENG-3 | Implement `QAWorker` (`departments/engineering/qa_worker.py`) and `DevOpsWorker` (`departments/engineering/devops_worker.py`) | M2 | `departments/engineering/qa_worker.py`, `departments/engineering/devops_worker.py` | DONE |
| 4 | F-ENG-4 | Create `tests/test_engineering.py` testing `EngineeringManager` and engineering workers | M2 | `tests/test_engineering.py` | DONE |
| 5 | F-RES-1 | Refactor `ResearchManager` (`departments/research/manager.py`) to inherit `Module` and `BaseAgent`, register with Kernel, parse research requests, delegate to platform workers, aggregate results, and output research reports | M2 | `departments/research/manager.py` | DONE |
| 6 | F-RES-2 | Refactor platform workers in `departments/research/workers/` (`github.py`, `hn.py`, `product_hunt.py`, `reddit.py`, `twitter.py`) to perform functional query searches, process data, return structured results | M2 | `departments/research/workers/` | DONE |
| 7 | F-RES-3 | Create `tests/test_research.py` testing `ResearchManager` and platform workers | M2 | `tests/test_research.py` | DONE |

## Milestone Status
- Milestone 2: Technical Departments (Engineering & Research) — DONE

## Interface Contracts
- Department Module interface: `Module`, `set_kernel`, `handle_event`
- Event bus conventions:
  - Input task events: `department.execute_task`, `engineering.task`, `research.task`, `task.assigned`
  - Output task events: `department.task_completed`, `engineering.result`, `research.result`, `task.complete`
