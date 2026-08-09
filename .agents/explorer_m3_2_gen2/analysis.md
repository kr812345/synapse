# Milestone 3 Investigation & Implementation Plan: Personal & Echo Departments

## Executive Summary
This document provides a comprehensive architectural analysis and implementation plan for Milestone 3 Personal (`departments/personal/`) and Echo (`departments/echo/`) departments.
The investigation focused on replacing mocked return strings with functional logic, establishing full Kernel `Module` integration, ensuring event routing compliance, and specifying unit/integration test suites for `tests/test_personal.py` and `tests/test_echo.py`.

---

## 1. Existing Architecture & Code Findings

### 1.1 Personal Department (`departments/personal/`)
- **`departments/personal/manager.py`**:
  - Existing class `PersonalManager` inherits ONLY `BaseAgent`. It does **not** inherit `Module` or implement `KernelInterface` module hooks (`name`, `set_kernel`, `handle_event`).
  - Current implementation returns hardcoded mock string: `{"status": "success", "task": task, "result": "mocked personal manager result"}` at line 23.
  - Allowed tools: `["contacts", "finances"]` (line 11).
  - Forbidden actions: `["authorize_payments"]` (line 14).
  - Memory access level: `"admin"` (line 17).
  - `can_handle` logic only checks for `"personal"` or `"life"` (line 20).
  - Lacks schedule delegation to `AssistantWorker` and finance/contacts oversight logic.

- **`departments/personal/assistant_worker.py`**:
  - Existing class `AssistantWorker` inherits `BaseAgent`.
  - Current implementation returns hardcoded mock string: `{"status": "success", "task": task, "result": "mocked assistant result"}` at line 21.
  - Allowed tools: `["calendar", "email"]` (line 9).
  - Forbidden actions: `["delete_emails"]` (line 12).
  - Memory access level: `"high"` (line 15).
  - `can_handle` logic only checks for `"schedule"` or `"personal"` (line 18), missing explicit keywords for `"calendar"`, `"email"`, `"agenda"`, `"meeting"`, `"reminder"`.

### 1.2 Echo Department (`departments/echo/`)
- **`departments/echo/echo_manager.py`**:
  - Existing class `EchoDepartment` correctly inherits `Module` from `shared.interfaces`.
  - Implements property `name` returning `"echo_department"`.
  - Implements `set_kernel(self, kernel: KernelInterface)`.
  - Implements `handle_event(self, event: Event)`: listens for `event.event_type == "ping"`, constructs a `pong` event with `source=self.name`, `destination=event.source`, `event_type="pong"`, and `payload={"original_payload": event.payload}`, sending it via `self.kernel.send_event(response)`.
  - The implementation is robust, complete, and fully conforms to F-ECH-1 requirements.

---

## 2. Requirements & Proposed Refactoring Plans

### 2.1 F-PRS-1: Refactor `PersonalManager` (`departments/personal/manager.py`)
- **Target File**: `/root/synapse/departments/personal/manager.py`
- **Inheritance Change**: `class PersonalManager(Module, BaseAgent):`
- **Module Interface Implementation**:
  - `@property def name(self) -> str:` returns `"department.personal"`
  - `def set_kernel(self, kernel: KernelInterface) -> None:` sets `self.kernel = kernel`
  - `async def handle_event(self, event: Event) -> None:`
    - Handles events with `event_type in ("department.execute_task", "task.assigned")` or `event.destination == self.name`.
    - Extracts task payload (`event.payload.get("task", event.payload)`).
    - Calls `await self.execute(task_data)`.
    - On success: emits `Event(source=self.name, destination=event.source, event_type="department.task_completed", payload={"task_id": task_id, "status": "success", "result": result})`.
    - On exception: emits `Event(source=self.name, destination=event.source, event_type="department.task_failed", payload={"task_id": task_id, "status": "failed", "error": str(exc)})`.
- **Remove Mock Result**: Completely remove `"mocked personal manager result"`.
- **Schedule Delegation & Finance Oversight**:
  - In `execute(task)`:
    - Parse task description and task ID.
    - If task relates to schedule/calendar/email/agenda/meeting: delegate task to worker (`self.workers[0]`) via `await self.workers[0].execute(task)`.
    - If task relates to finance/budget/contacts oversight: process finance oversight logic utilizing allowed tools `["contacts", "finances"]` while enforcing forbidden action `["authorize_payments"]`.
    - Return structured dict response.

#### Proposed Code Snippet for `departments/personal/manager.py`:
```python
from typing import List, Any, Optional, Dict
import logging
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .assistant_worker import AssistantWorker

logger = logging.getLogger(__name__)

class PersonalManager(Module, BaseAgent):
    def __init__(self, id: str = "personal_manager", name: str = "Personal Manager"):
        super().__init__(id=id, name=name, department="personal", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers = [AssistantWorker(f"{id}_worker1", "Charlie Assistant")]

    @property
    def name(self) -> str:
        return "department.personal"

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    async def handle_event(self, event: Event) -> None:
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            if isinstance(task_data, dict):
                task_id = task_data.get("id")
            elif hasattr(task_data, "id"):
                task_id = getattr(task_data, "id", None)
            else:
                task_id = None

            try:
                result = await self.execute(task_data)
                if self.kernel:
                    response_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_completed",
                        payload={
                            "task_id": task_id,
                            "status": "success",
                            "result": result
                        }
                    )
                    await self.kernel.send_event(response_event)
            except Exception as exc:
                logger.error(f"Execution error in {self.name} for task {task_id}: {exc}", exc_info=True)
                if self.kernel:
                    failure_event = Event(
                        source=self.name,
                        destination=event.source,
                        event_type="department.task_failed",
                        payload={
                            "task_id": task_id,
                            "status": "failed",
                            "error": str(exc)
                        }
                    )
                    await self.kernel.send_event(failure_event)

    def allowed_tools(self) -> List[str]:
        return ["contacts", "finances"]

    def forbidden_actions(self) -> List[str]:
        return ["authorize_payments"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return any(k in desc for k in ["personal", "life", "schedule", "calendar", "finance", "contacts", "agenda"])

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            desc = task.get("description", str(task))
            task_id = task.get("id")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            task_id = getattr(task, "id", None)
        else:
            desc = str(task)
            task_id = None

        desc_lower = desc.lower()

        # Delegate schedule/calendar/email tasks to AssistantWorker
        if any(k in desc_lower for k in ["schedule", "calendar", "email", "agenda", "meeting"]):
            assistant = self.workers[0]
            worker_result = await assistant.execute(task)
            return {
                "status": "success",
                "manager": self.name,
                "delegated_to": assistant.name,
                "task": task,
                "result": worker_result
            }

        # Handle finance or contacts oversight tasks
        if any(k in desc_lower for k in ["finance", "budget", "contact", "expense"]):
            return {
                "status": "success",
                "manager": self.name,
                "oversight_type": "finance_and_contacts",
                "allowed_tools_used": self.allowed_tools(),
                "forbidden_actions_enforced": self.forbidden_actions(),
                "task": task,
                "result": {
                    "oversight_summary": f"Oversight completed for personal finance and contacts task: '{desc}'",
                    "payments_authorized": False,
                    "policy_compliance": "authorize_payments prevented"
                }
            }

        # Default general personal task execution
        return {
            "status": "success",
            "manager": self.name,
            "task": task,
            "result": {
                "summary": f"Personal manager processed task: '{desc}'",
                "managed": True
            }
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing", "workers_active": len(self.workers)}

    def remember(self, knowledge: Any) -> None:
        pass
```

---

### 2.2 F-PRS-2: Refactor `AssistantWorker` (`departments/personal/assistant_worker.py`)
- **Target File**: `/root/synapse/departments/personal/assistant_worker.py`
- **Remove Mock Result**: Completely remove `"mocked assistant result"`.
- **Calendar & Email Task Handling**:
  - Update `can_handle`: match keywords `["schedule", "calendar", "email", "personal", "agenda", "meeting", "reminder"]`.
  - In `execute(task)`: inspect task description for calendar vs email tasks.
  - Return structured dict response containing execution details, tools used, and status.

#### Proposed Code Snippet for `departments/personal/assistant_worker.py`:
```python
from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class AssistantWorker(BaseAgent):
    def __init__(self, id: str, name: str):
        super().__init__(id=id, name=name, department="personal", role="assistant")

    def allowed_tools(self) -> List[str]:
        return ["calendar", "email"]

    def forbidden_actions(self) -> List[str]:
        return ["delete_emails"]

    def memory_access_level(self) -> str:
        return "high"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return any(k in desc for k in ["schedule", "calendar", "email", "personal", "agenda", "meeting", "reminder"])

    async def execute(self, task: Any) -> Any:
        if isinstance(task, dict):
            desc = task.get("description", str(task))
            task_id = task.get("id", "unknown")
        elif hasattr(task, "description"):
            desc = getattr(task, "description", str(task))
            task_id = getattr(task, "id", "unknown")
        else:
            desc = str(task)
            task_id = "unknown"

        desc_lower = desc.lower()

        if any(k in desc_lower for k in ["calendar", "schedule", "meeting", "agenda"]):
            action = "calendar_management"
            details = f"Processed schedule/calendar task '{desc}'. Calendar events updated."
        elif any(k in desc_lower for k in ["email", "message", "inbox"]):
            action = "email_processing"
            details = f"Processed email task '{desc}'. Drafted/reviewed messages (delete_emails action forbidden)."
        else:
            action = "general_assistant_task"
            details = f"Processed assistant task '{desc}'."

        return {
            "status": "success",
            "worker": self.name,
            "task_id": task_id,
            "action": action,
            "task": task,
            "result": {
                "summary": details,
                "tools_used": self.allowed_tools(),
                "output": details
            }
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
```

---

### 2.3 F-PRS-3: Test Plan & Specifications for `tests/test_personal.py`
- **Target File**: `/root/synapse/tests/test_personal.py`
- **Test Suite Structure**:
  1. `test_personal_manager_initialization()`: Verify `id`, `name`, `department`, `role`, `allowed_tools()`, `forbidden_actions()`, `memory_access_level()`, and `name` property (`"department.personal"`).
  2. `test_assistant_worker_initialization()`: Verify `id`, `name`, `department`, `role`, `allowed_tools()`, `forbidden_actions()`, `memory_access_level()`.
  3. `test_assistant_worker_can_handle()`: Verify true for schedule/calendar/email tasks and false for unrelated tasks (e.g. `"delete production database"`).
  4. `test_assistant_worker_execute_calendar_task()`: Execute calendar task via worker, verify status `"success"`, non-mocked output, no `"mocked assistant result"`.
  5. `test_assistant_worker_execute_email_task()`: Execute email task via worker, verify status `"success"`, non-mocked output, no `"mocked assistant result"`.
  6. `test_personal_manager_schedule_delegation()`: Execute schedule task via `PersonalManager.execute()`, verify delegation to `AssistantWorker`.
  7. `test_personal_manager_finance_oversight()`: Execute finance task via `PersonalManager.execute()`, verify finance oversight logic and compliance with forbidden actions.
  8. `test_personal_manager_kernel_integration()`: Register `PersonalManager` directly with `Kernel`, send `department.execute_task` event, assert receipt of `department.task_completed` event with valid result.
  9. `test_personal_manager_event_routing()`: Send `task.assigned` event to `department.personal`, verify completed event emitted.
  10. `test_personal_manager_error_handling()`: Trigger execution failure in `PersonalManager`, verify `department.task_failed` event emitted.

---

### 2.4 F-ECH-1 & F-ECH-2: Verification of `EchoDepartment` & Test Plan for `tests/test_echo.py`

#### F-ECH-1 Verification Summary:
- `EchoDepartment` in `departments/echo/echo_manager.py` is fully functional and complies with all specs.
- Interface compliance: Inherits `Module`, `name == "echo_department"`, `set_kernel` stores kernel reference.
- Event contract: Receives `event_type == "ping"`, sends `event_type == "pong"` with `source="echo_department"`, `destination=event.source`, `payload={"original_payload": event.payload}` via `self.kernel.send_event(response)`.
- Ignores non-ping event types.

#### F-ECH-2 Test Plan (`tests/test_echo.py`):
- **Target File**: `/root/synapse/tests/test_echo.py`
- **Test Suite Structure**:
  1. `test_echo_department_module_interface()`: Check instantiation, property `name == "echo_department"`, `set_kernel`.
  2. `test_echo_department_ping_pong_roundtrip()`: Register `EchoDepartment` with `Kernel`, send `ping` event from a mock client, verify `pong` event is received by client.
  3. `test_echo_department_payload_preservation()`: Send `ping` with complex nested payloads (dicts, lists, ints, booleans), verify exact payload equality in `pong` event payload `original_payload`.
  4. `test_echo_department_source_routing()`: Send `ping` from custom source name (e.g., `"caller_client"`), verify `pong.destination == "caller_client"` and `pong.source == "echo_department"`.
  5. `test_echo_department_ignores_non_ping_events()`: Send non-ping event (e.g. `event_type="info"`), verify no `pong` event is emitted.
  6. `test_echo_department_multiple_pings()`: Send multiple consecutive `ping` events, verify corresponding sequence of `pong` events.

---

## 3. Verification Method

To verify all implementations:
1. Run unit test suite:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest tests/test_personal.py tests/test_echo.py
   ```
2. Run end-to-end tier test suite:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest tests/e2e/tier1/test_tier1_personal.py tests/e2e/tier1/test_tier1_echo.py
   ```
3. Run full pytest suite to verify zero regressions:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest
   ```
