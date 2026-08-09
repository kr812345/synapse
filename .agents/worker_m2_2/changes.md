# Implementation Changes Report — Technical Departments Null-Safety & Test Expansion

**Worker**: `worker_m2_2`  
**Milestone**: Milestone 2 — Technical Departments (Iteration 2)  
**Date**: 2026-08-06  

---

## Summary of Changes

In Iteration 2 of Milestone 2, `worker_m2_2` addressed the root causes of the Iteration 1 gate rejection by implementing defensive null-safety guards across `EngineeringManager`, `ResearchManager`, all 3 Engineering workers, and all 5 Research workers, and expanding the test suites in `tests/test_engineering.py` and `tests/test_research.py`.

---

## Detailed File Modification Breakdown

### 1. `departments/engineering/manager.py` (`EngineeringManager`)
- **`handle_event(event)`**:
  - Moved payload extraction and `task_id` resolution completely inside the `try:` block.
  - Guarded payload extraction with `payload = (event.payload if event and event.payload is not None else {})`.
  - Added safe extraction for dict vs. non-dict task payloads to prevent `AttributeError: 'NoneType' object has no attribute 'get'`.
- **`execute(task)`**:
  - Handled `task = None` explicitly to set `task_desc = ""` and `task_id = None`.
  - Handled `task.get("description") = None` (where `dict.get()` returns `None` instead of default) by extracting `raw_desc` with `is not None` guard before falling back to `str(task)`.
  - Handled objects with `description = None` using explicit `is not None` fallback to `""`.
  - Enforced string type conversion on `task_desc` (`if not isinstance(task_desc, str): task_desc = str(task_desc)`) before evaluating `.lower()`.
- **`can_handle(task_description)`**:
  - Maintained defensive `if not task_description or not isinstance(task_description, str): return False` guard against `None` or non-string inputs.

### 2. `departments/engineering/backend_worker.py` (`BackendWorker`)
- **`execute(task)`**:
  - Added null-safety check for `task = None`, `task.get("description") = None`, and objects with `description = None`.
  - Guaranteed `task_desc` is a valid string prior to formatting generated code and string slicing (`task_desc[:50]`).

### 3. `departments/engineering/qa_worker.py` (`QAWorker`)
- **`execute(task)`**:
  - Added explicit `task = None` and `description = None` guards to prevent string interpolation with `"None"`.

### 4. `departments/engineering/devops_worker.py` (`DevOpsWorker`)
- **`execute(task)`**:
  - Added explicit `task = None` and `description = None` guards.

### 5. `departments/research/manager.py` (`ResearchManager`)
- **`handle_event(event)`**:
  - Moved payload extraction inside `try:` block with `payload = (event.payload if event and event.payload is not None else {})`.
  - Prevented unhandled `AttributeError` when processing `Event(payload=None)`.
- **`execute(task)`**:
  - Handled `task = None` by defaulting `task = {}`.
  - Safely extracted `query` checking `raw_q is not None` to prevent falling through to `None`.
  - Guarded `requested_sources = task.get("sources") or []` to guarantee `requested_sources` is an iterable list even when `sources = None`.
  - Coerced `query` to string before slicing `query[:50]`.
- **`can_handle(task_description)`**:
  - Guarded `task_description` when `None` or not a string.

### 6. Research Platform Workers (`github.py`, `hn.py`, `product_hunt.py`, `reddit.py`, `twitter.py`)
- **`can_handle(task_description)`**:
  - Added `if not task_description or not isinstance(task_description, str): return False` across all 5 workers.
- **`execute(task)`**:
  - Handled `task = None` by defaulting `task = {}`.
  - Guarded `query` extraction so that if `query` or `description` or `topic` is `None`, `query` becomes empty string `""`.
  - Guaranteed `query` is a string before calling `.lower()` or string operations.

### 7. `tests/test_engineering.py`
- Appended 5 new unit tests:
  1. `test_engineering_manager_handle_event_none_payload`: Validates `Event(payload=None)` handling in `handle_event`.
  2. `test_engineering_manager_execute_null_description`: Validates `task={"description": None}` execution.
  3. `test_engineering_manager_execute_none_task`: Validates `task=None` execution.
  4. `test_engineering_workers_none_input_robustness`: Validates `BackendWorker`, `QAWorker`, and `DevOpsWorker` with `None` inputs.
  5. `test_engineering_can_handle_none_inputs`: Validates `can_handle(None)` and non-string types.

### 8. `tests/test_research.py`
- Appended 6 new unit tests:
  1. `test_research_manager_handle_event_none_payload`: Validates `Event(payload=None)` handling.
  2. `test_research_manager_execute_null_description`: Validates `task={"description": None}` execution.
  3. `test_research_manager_execute_null_sources`: Validates `task={"sources": None}` execution.
  4. `test_research_manager_execute_none_task`: Validates `task=None` execution.
  5. `test_research_workers_none_input_robustness`: Validates all 5 research workers on `None` inputs.
  6. `test_research_can_handle_none_inputs`: Validates `can_handle(None)` and invalid input types.

---

## Verification Results

- Standard Pytest suite: `PYTHONPATH=. ./.venv/bin/pytest` -> **204 passed in 6.24s (100% PASS)**
- Challenger 1 Stress Test suite: `PYTHONPATH=. ./.venv/bin/pytest .agents/challenger_m2_1/test_engineering_stress.py -v` -> **9 passed in 0.71s (100% PASS)**
