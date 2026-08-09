## 2026-08-06T02:01:06Z
You are Worker 2 for Iteration 2 of Milestone 2: Technical Departments (Engineering & Research Null-Safety & Test Expansion).
Your working directory is: /root/synapse/.agents/worker_m2_2
Main project directory: /root/synapse

MANDATORY FIRST STEP: Read the following files:
- /root/synapse/.agents/ORIGINAL_REQUEST.md
- /root/synapse/PROJECT.md
- /root/synapse/.agents/sub_orch_m2/SCOPE.md
- /root/synapse/.agents/sub_orch_m2/GATE_STATUS.md
- /root/synapse/.agents/challenger_m2_1/handoff.md
- /root/synapse/.agents/explorer_m2_1_it2/analysis.md
- /root/synapse/.agents/explorer_m2_2_it2/analysis.md
- /root/synapse/.agents/explorer_m2_3_it2/analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
- departments/engineering/manager.py
- departments/engineering/backend_worker.py
- departments/engineering/qa_worker.py
- departments/engineering/devops_worker.py
- departments/research/manager.py
- departments/research/workers/github.py
- departments/research/workers/hn.py
- departments/research/workers/product_hunt.py
- departments/research/workers/reddit.py
- departments/research/workers/twitter.py
- tests/test_engineering.py
- tests/test_research.py

Implementation Tasks:
1. Implement defensive null-safety guards in `EngineeringManager` (`departments/engineering/manager.py`):
   - `handle_event(event)`: Extract payload inside `try:` block with `payload = (event.payload if event and event.payload is not None else {})`.
   - `execute(task)`: Guard `task` and `description`: handle `task=None`, `task.get("description")=None`, non-string descriptions, etc.
   - `can_handle(task_type)`: Guard `task_type` when `None`.
2. Implement defensive null-safety guards in `ResearchManager` (`departments/research/manager.py`):
   - `handle_event(event)`: Extract payload safely with `payload = (event.payload if event and event.payload is not None else {})`.
   - `execute(task)`: Handle `task=None`, `task.get("sources")=None` (guard `requested_sources = task.get("sources") or []`), `description=None`, etc.
   - `can_handle(task_type)`: Guard `task_type` when `None`.
3. Audit and add null-safety guards to engineering workers (`backend_worker.py`, `qa_worker.py`, `devops_worker.py`) and research workers (`github.py`, `hn.py`, `product_hunt.py`, `reddit.py`, `twitter.py`).
4. Expand test suites in `tests/test_engineering.py` and `tests/test_research.py` to add unit tests for `Event(..., payload=None)`, `task={"description": None}`, `task=None`, and `task={"sources": None}`.

Verification:
After implementing changes, run `PYTHONPATH=. ./.venv/bin/pytest` to ensure 100% of tests pass.

Write your changes report to `/root/synapse/.agents/worker_m2_2/changes.md` and handoff report to `/root/synapse/.agents/worker_m2_2/handoff.md`.
Then send a completion message to parent.
