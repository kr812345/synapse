# Scope: Milestone 3 - Commercial & Operations Departments

## Architecture
- Marketing: `departments/marketing/` (manager.py, social_worker.py, content_worker.py)
- Sales: `departments/sales/` (__init__.py, manager.py, outreach_worker.py)
- Personal: `departments/personal/` (manager.py, assistant_worker.py)
- Echo: `departments/echo/` (echo_manager.py)
- Tests: `tests/test_marketing.py`, `tests/test_sales.py`, `tests/test_personal.py`, `tests/test_echo.py`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 32 | F-MKT-1 | Real campaign management in `MarketingManager` (remove "mocked marketing manager result") | M3 | PROJECT.md |
| 33 | F-MKT-2 | Real post generation in `SocialWorker` (remove "mocked social media result") | M3 | PROJECT.md |
| 34 | F-MKT-3 | Implement `ContentWorker` in marketing department | M3 | PROJECT.md |
| 35 | F-MKT-4 | Create unit & integration test file `tests/test_marketing.py` | M3 | PROJECT.md |
| 36 | F-SLS-1 | Create `departments/sales/` directory, `__init__.py`, `manager.py`, `outreach_worker.py` | M3 | PROJECT.md |
| 37 | F-SLS-2 | Implement functional `SalesManager` with lead generation & CRM tools | M3 | PROJECT.md |
| 38 | F-SLS-3 | Implement functional `SalesWorker` with email draft & pitch generation | M3 | PROJECT.md |
| 39 | F-SLS-4 | Create unit & integration test file `tests/test_sales.py` | M3 | PROJECT.md |
| 40 | F-PRS-1 | Real assistant management in `PersonalManager` (remove "mocked personal manager result") | M3 | PROJECT.md |
| 41 | F-PRS-2 | Real task/schedule execution in `AssistantWorker` (remove "mocked assistant result") | M3 | PROJECT.md |
| 42 | F-PRS-3 | Create unit & integration test file `tests/test_personal.py` | M3 | PROJECT.md |
| 43 | F-ECH-1 | Preserve and verify `EchoDepartment` ping/pong event module | M3 | PROJECT.md |
| 44 | F-ECH-2 | Create unit & integration test file `tests/test_echo.py` | M3 | PROJECT.md |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M3 | Commercial & Operations Departments | Marketing, Sales, Personal, Echo departments and tests | M1 | DONE |

## Interface Contracts
- All managers inherit `Module` and `BaseAgent` and register with `Kernel`.
- Event handling for departments: listen for `department.execute_task` or `task.assigned`, emit `department.task_completed` or `task.complete`.
