# Milestone 3 Test Suite & Integration Verification Analysis

## Executive Summary
This document provides a comprehensive test design analysis and specification for Milestone 3 (Commercial & Operations Departments) of the Synapse AI OS. Milestone 3 requires programmatic verification across four specific test modules:
1. `tests/test_marketing.py` (F-MKT-4)
2. `tests/test_sales.py` (F-SLS-4)
3. `tests/test_personal.py` (F-PRS-3)
4. `tests/test_echo.py` (F-ECH-2)

All four test modules must strictly enforce genuine event-driven task processing, functional output generation, exception isolation boundaries, and total elimination of hardcoded mock strings (e.g., `"mocked marketing manager result"`, `"mocked social media result"`, `"mocked sales manager result"`, `"mocked personal manager result"`, `"mocked assistant result"`).

---

## 1. Architectural Foundation & Shared Test Mechanics

### 1.1 Kernel & Module Interface Integration
Every department manager and worker operates within the Synapse AI OS event-driven architecture.
- **Kernel (`kernel/kernel.py`)**: Central control plane. Modules register via `kernel.register_module(module)`. Modules must implement the `Module` ABC (`shared/interfaces.py`), declaring a string `@property name` and an `async handle_event(event: Event) -> None` method.
- **Base Department Module (`departments/base.py`)**: Wraps `BaseAgent` implementations into `BaseDepartmentModule(Module)`.
  - Automatically names the module `department.<dept>` (e.g. `department.marketing`, `department.sales`, `department.personal`).
  - Injects `kernel` reference via `set_kernel(kernel)`.
  - Listens for `event.event_type in ("department.execute_task", "task.assigned")` or direct unicast (`event.destination == self.name`).
  - Calls `await self.agent.execute(task_data)`.
  - Emits `department.task_completed` on success or `department.task_failed` on exception.
- **Event Bus (`events/event_bus.py`)**: Message broker supporting unicast (`destination == module_name`), broadcast (`destination == "*"`), and topic subscription wildcard patterns (`bus.subscribe_topic(module, pattern)`).

### 1.2 Verification Standards
Every test file must satisfy the following criteria:
1. **Event-Driven Execution**: Tests must instantiate `Kernel`, register department modules, send `Event` objects, and await response events.
2. **Output Structure & Correctness**: Outputs must return rich, structured dictionaries (e.g. campaign plans, social posts, blog drafts, qualified leads, outreach pitches, calendar schedules) rather than placeholder strings.
3. **Mock String Prohibition**: Assertions must explicitly check `assert "mocked" not in str(result).lower()`.
4. **Error Handling**: Exception raising inside `agent.execute` must be handled gracefully by `BaseDepartmentModule` and result in a `department.task_failed` event without crashing the `Kernel` or `EventBus`.

---

## 2. Test Specifications by Department

### 2.1 Marketing Department Tests — `tests/test_marketing.py` (F-MKT-4)

#### Component Overview
- **`MarketingManager` (`departments/marketing/manager.py`)**: Department manager supervising campaign strategy and task delegation.
- **`SocialWorker` (`departments/marketing/social_worker.py`)**: Specialist for social media post generation (Twitter/LinkedIn).
- **`ContentWorker` (`departments/marketing/content_worker.py`)**: Specialist for blog posts, press releases, and marketing copy.

#### Required Test Scenarios

##### 1. `test_marketing_manager_campaign_execution(fresh_kernel, harness_client)`
- **Goal**: Verify end-to-end event handling for `MarketingManager` via `BaseDepartmentModule`.
- **Inputs**: Send `Event(source=client, destination="department.marketing", event_type="department.execute_task", payload={"task": {"id": "mkt-101", "description": "launch Q3 social marketing campaign"}})`
- **Expected Behavior**: `BaseDepartmentModule` invokes `MarketingManager.execute()`. Emits `department.task_completed` back to client.
- **Assertions**:
  - `completed_event.payload["status"] == "success"`
  - `completed_event.payload["task_id"] == "mkt-101"`
  - Result payload contains structured campaign metrics (e.g., campaign name, target platforms, strategy overview).
  - `"mocked marketing manager result"` is **NOT** present in `completed_event.payload["result"]`.

##### 2. `test_social_worker_capabilities_and_execution()`
- **Goal**: Verify `SocialWorker` capability matching (`can_handle`), tool permissions, and post generation.
- **Inputs**: Task description `"Draft Twitter announcement for AI OS launch"`.
- **Expected Behavior**: `can_handle` returns `True` for social/marketing tasks, `False` for devops/coding tasks. `allowed_tools` includes `["twitter", "linkedin"]`.
- **Assertions**:
  - `worker.department == "marketing"`
  - `worker.role == "social_media_manager"`
  - `await worker.execute(task)` returns `{"status": "success", "content": ..., "platform": "twitter"}`.
  - `"mocked social media result"` is **NOT** present in the result.

##### 3. `test_content_worker_blog_generation()`
- **Goal**: Verify `ContentWorker` capability matching, allowed tools (`["cms_editor", "seo_analyzer"]`), and long-form copy creation.
- **Inputs**: Task description `"Write technical blog article on event-driven architecture"`.
- **Expected Behavior**: `can_handle` returns `True`. Generates structured blog post content.
- **Assertions**:
  - `worker.role == "content_writer"`
  - Result contains `title`, `body`, `seo_keywords`, `status: "success"`.
  - No hardcoded stub strings present.

##### 4. `test_marketing_analytics_tool_execution(fresh_kernel, harness_client)`
- **Goal**: Verify marketing agents can execute tools via `ToolRegistry` registered as a Kernel module.
- **Inputs**: Send `Event(destination="tool_registry", event_type="tool.execute", payload={"tool_name": "analytics", "agent": {"id": "mkt_mgr", "allowed_tools": ["analytics"]}, "kwargs": {"metric": "conversion_rate"}})`
- **Assertions**:
  - Tool execution response event `tool.execution_result` received.
  - Response status is `"success"`.

##### 5. `test_marketing_department_broadcast_event(fresh_kernel, harness_client)`
- **Goal**: Verify `MarketingManager` responds correctly to pub/sub broadcast events (`destination="*"`).
- **Inputs**: Send broadcast `Event(destination="*", event_type="task.assigned", payload={"task": {"id": "mkt-b1", "description": "marketing campaign strategy"}})`
- **Assertions**:
  - Receives `department.task_completed` event with `task_id == "mkt-b1"`.

---

### 2.2 Sales Department Tests — `tests/test_sales.py` (F-SLS-4)

#### Component Overview
- **`SalesManager` (`departments/sales/manager.py`)**: Manager handling B2B lead generation, CRM tracking, and sales deal pipelines.
- **`OutreachWorker` (`departments/sales/outreach_worker.py`)**: Specialist creating customized cold emails, sales pitches, and follow-ups.

#### Required Test Scenarios

##### 1. `test_sales_manager_lead_generation(fresh_kernel, harness_client)`
- **Goal**: Verify `SalesManager` lead generation campaign execution over Kernel event bus.
- **Inputs**: Send `Event(destination="department.sales", event_type="department.execute_task", payload={"task": {"id": "sls-201", "description": "lead generation for enterprise SaaS accounts"}})`
- **Expected Behavior**: `SalesManager` executes lead qualification workflow.
- **Assertions**:
  - Response `department.task_completed` received.
  - Payload status is `"success"`, `task_id == "sls-201"`.
  - Output contains lead records, lead score, industry segment, and CRM status.
  - Zero mocked strings present.

##### 2. `test_outreach_worker_pitch_generation()`
- **Goal**: Verify `OutreachWorker` capabilities, tool permissions (`["email_draft", "pitch_generator"]`), forbidden actions (`["send_spam_blast"]`), and pitch output.
- **Inputs**: Task description `"Draft cold email pitch for CTO prospect"`.
- **Expected Behavior**: `can_handle` returns `True` for pitch/outreach/email descriptions. Generates email subject line and pitch body.
- **Assertions**:
  - `worker.department == "sales"`
  - `worker.role == "outreach_specialist"`
  - Result contains subject line, personalized body, call-to-action, status `"success"`.

##### 3. `test_sales_manager_permissions_and_crm_tools()`
- **Goal**: Verify `SalesManager` metadata: `allowed_tools` (`["crm_search", "lead_qualifier", "email_sender"]`), `forbidden_actions` (`["grant_unauthorized_discount"]`), `memory_access_level == "admin"`.
- **Assertions**: Exact match on tool permissions and security boundaries.

##### 4. `test_sales_department_task_failure_handling(fresh_kernel, harness_client)`
- **Goal**: Verify exception boundary handling when a sales worker fails (e.g. database error or CRM disconnection).
- **Inputs**: Use a failing sales agent mock or trigger an invalid task state.
- **Expected Behavior**: `BaseDepartmentModule` catches exception and emits `department.task_failed`.
- **Assertions**:
  - Event `department.task_failed` received.
  - `payload["status"] == "failed"`
  - `payload["error"]` contains exception details.

---

### 2.3 Personal Department Tests — `tests/test_personal.py` (F-PRS-3)

#### Component Overview
- **`PersonalManager` (`departments/personal/manager.py`)**: Manager handling executive assistance, personal operations, and daily scheduling.
- **`AssistantWorker` (`departments/personal/assistant_worker.py`)**: Worker managing calendar scheduling, reminders, and personal organization.

#### Required Test Scenarios

##### 1. `test_personal_manager_assistant_management(fresh_kernel, harness_client)`
- **Goal**: Verify `PersonalManager` event-driven task processing via `BaseDepartmentModule`.
- **Inputs**: Send `Event(destination="department.personal", event_type="department.execute_task", payload={"task": {"id": "prs-301", "description": "organize personal executive agenda for tomorrow"}})`
- **Expected Behavior**: `PersonalManager` executes agenda planning. Emits `department.task_completed`.
- **Assertions**:
  - `completed_event.payload["status"] == "success"`
  - `completed_event.payload["task_id"] == "prs-301"`
  - Result contains structured schedule timeline, priority items, and zero mocked strings (`"mocked personal manager result"` must NOT be present).

##### 2. `test_assistant_worker_schedule_execution()`
- **Goal**: Verify `AssistantWorker` task capabilities (`can_handle`), tool access (`["calendar", "email"]`), forbidden actions (`["delete_emails"]`), and schedule output.
- **Inputs**: Task dictionary `{"task_id": "asst-1", "description": "schedule team sync meeting at 2pm"}`
- **Expected Behavior**: `can_handle` returns `True` for schedule/personal tasks.
- **Assertions**:
  - `worker.department == "personal"`
  - `worker.role == "assistant"`
  - `await worker.execute(...)` returns dictionary with event title, start time, duration, participants, and status `"success"`.
  - `"mocked assistant result"` is **NOT** present.

##### 3. `test_personal_department_event_routing(fresh_kernel, harness_client)`
- **Goal**: Verify `PersonalManager` receives events via `task.assigned` topic routing.
- **Inputs**: Send `Event(destination="department.personal", event_type="task.assigned", payload={"task": {"id": "prs-302", "description": "personal expense reconciliation"}})`
- **Assertions**: Emits `department.task_completed` with `task_id == "prs-302"`.

##### 4. `test_personal_manager_permissions()`
- **Goal**: Verify security model for `PersonalManager` (`allowed_tools`: `["contacts", "finances"]`, `forbidden_actions`: `["authorize_payments"]`, `memory_access_level`: `"admin"`).
- **Assertions**: Verifies allowed tools list, forbidden actions list, and memory access level.

---

### 2.4 Echo Department Tests — `tests/test_echo.py` (F-ECH-2)

#### Component Overview
- **`EchoDepartment` (`departments/echo/echo_manager.py`)**: Diagnostic infrastructure module implementing `Module` directly. Re-emits `"pong"` events in response to `"ping"` events.

#### Required Test Scenarios

##### 1. `test_echo_department_ping_pong(fresh_kernel, harness_client)`
- **Goal**: Verify basic ping-pong lifecycle.
- **Inputs**: Register `EchoDepartment`. Send `Event(source=client, destination="echo_department", event_type="ping", payload={"msg": "hello_echo"})`
- **Expected Behavior**: Emits `Event(source="echo_department", destination=client, event_type="pong", payload={"original_payload": {"msg": "hello_echo"}})`
- **Assertions**:
  - `pong_event.source == "echo_department"`
  - `pong_event.destination == harness_client.name`
  - `pong_event.event_type == "pong"`
  - `pong_event.payload["original_payload"]["msg"] == "hello_echo"`

##### 2. `test_echo_department_payload_preservation(fresh_kernel, harness_client)`
- **Goal**: Verify that complex, deeply nested payloads are preserved without modification or truncation.
- **Inputs**: Send `ping` event with payload containing dicts, lists, ints, floats, booleans, and null values.
- **Assertions**: `pong_event.payload["original_payload"]` matches the sent dictionary exactly (`assert pong_event.payload["original_payload"] == complex_payload`).

##### 3. `test_echo_department_source_routing(fresh_kernel, harness_client)`
- **Goal**: Verify that the destination of the `pong` event dynamically matches the `source` of the incoming `ping` event.
- **Inputs**: Send ping event from client `"custom_tester"`.
- **Assertions**: `pong_event.destination == "custom_tester"`.

##### 4. `test_echo_department_ignore_non_ping_events(fresh_kernel, harness_client)`
- **Goal**: Verify that `EchoDepartment` ignores non-ping events and emits no response events.
- **Inputs**: Send `Event(destination="echo_department", event_type="info", payload={})`
- **Assertions**: Client receives zero events (`len(harness_client.received_events) == 0`).

##### 5. `test_echo_department_kernel_integration(fresh_kernel, harness_client)`
- **Goal**: Verify runtime kernel registration, presence in `kernel.list_modules()`, and health check inclusion in `kernel.get_health_status()`.
- **Assertions**:
  - `"echo_department"` in `kernel.list_modules()`.
  - `kernel.get_health_status()["modules"]` contains `"echo_department"`.

---

## 3. Implementation Checklist for Test Files

| Test File | Required Class Tests | Event Tests | Tool Tests | Negative / Error Tests | Zero Mock String Tests |
|---|---|---|---|---|---|
| `tests/test_marketing.py` | `MarketingManager`, `SocialWorker`, `ContentWorker` | `department.execute_task`, `task.assigned` | `analytics`, `cms_editor` | Exception handling | Check no `"mocked marketing manager result"`, `"mocked social media result"` |
| `tests/test_sales.py` | `SalesManager`, `OutreachWorker` | `department.execute_task`, `task.assigned` | `crm_search`, `email_draft` | `department.task_failed` on agent error | Check no `"mocked sales manager result"` |
| `tests/test_personal.py` | `PersonalManager`, `AssistantWorker` | `department.execute_task`, `task.assigned` | `calendar`, `contacts` | Task execution failure boundary | Check no `"mocked personal manager result"`, `"mocked assistant result"` |
| `tests/test_echo.py` | `EchoDepartment` | `ping` -> `pong`, non-ping ignore | N/A | Ignored unhandled event types | N/A (Diagnostic module) |

---

## 4. Verification Command
To verify that all new unit & integration test files pass 100%:
```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_marketing.py tests/test_sales.py tests/test_personal.py tests/test_echo.py
```
And to verify the entire test suite across all tiers and standalone test files:
```bash
PYTHONPATH=. ./.venv/bin/pytest
```
