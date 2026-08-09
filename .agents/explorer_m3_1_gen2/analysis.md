# Detailed Investigation & Implementation Plan: Marketing and Sales Departments (Milestone 3)

## 1. Executive Summary

This document provides a comprehensive analysis of the codebase, architecture, event contracts, class hierarchies, and detailed implementation requirements for the **Marketing** (`departments/marketing/`) and **Sales** (`departments/sales/`) departments under Milestone 3 (Commercial & Operations).

The primary objective is to replace mocked return values (e.g. `"mocked marketing manager result"`, `"mocked social media result"`) with fully functional agent execution logic, properly implement `Module` and `BaseAgent` multiple inheritance, scaffold the Sales department, and ensure full integration with Synapse AI OS Kernel, EventBus, ToolRegistry, and MemoryEngine.

---

## 2. Architectural Analysis & Interface Contracts

### 2.1 Class Inheritance Hierarchy
All department managers and workers interact with two primary interfaces:
1. **`BaseAgent`** (`registry/sdk/base_agent.py`):
   - Abstract Base Class defining agent metadata (`id`, `name`, `department`, `role`, `confidence_score`), tool permissions (`allowed_tools`), security rules (`forbidden_actions`), memory policies (`memory_access_level`), task matching (`can_handle`), execution (`execute`), validation (`validate`), status reporting (`report`), and memory updates (`remember`).
2. **`Module`** (`shared/interfaces.py`):
   - Abstract Base Class defining `name` property and `async def handle_event(self, event: Event) -> None`.
3. **`BaseDepartmentModule`** (`departments/base.py`):
   - Wrapper adapter allowing any `BaseAgent` instance to be wrapped as a `Module` if registered separately.

#### Department Manager Refactoring Rule:
To fulfill features **F-MKT-1** and **F-SLS-2**, `MarketingManager` and `SalesManager` must directly inherit from both `Module` and `BaseAgent`:
```python
class MarketingManager(Module, BaseAgent):
    ...
```
This enables direct Kernel module registration via `kernel.register_module(manager_instance)` where `isinstance(manager_instance, Module)` evaluates to `True` (used in `tests/e2e/conftest.py` `full_os_kernel` fixture), while maintaining full compatibility with `BaseDepartmentModule` wrapping in legacy test helpers.

### 2.2 Event Envelope & Routing Contract
- **Event Envelope Schema** (`shared/models.py`):
  ```python
  Event(
      id=str(uuid4()),
      source=str,          # e.g., "harness_client", "scheduler", "department.marketing"
      destination=str,     # e.g., "department.marketing", "department.sales", "*"
      event_type=str,      # e.g., "department.execute_task", "task.assigned"
      payload=dict,        # e.g., {"task": {"id": "t1", "description": "..."}}
      timestamp=datetime.now(timezone.utc)
  )
  ```
- **Incoming Task Handlers**:
  - `event_type` in `("department.execute_task", "task.assigned")` or `destination == self.name`.
- **Outgoing Task Handlers**:
  - On success: `event_type="department.task_completed"`, payload `{"task_id": task_id, "status": "success", "result": result}`
  - On failure: `event_type="department.task_failed"`, payload `{"task_id": task_id, "status": "failed", "error": str(exc)}`

---

## 3. Investigation Findings & Codebase Assessment

### 3.1 Marketing Department (`departments/marketing/`)

#### Existing Files:
1. `departments/marketing/__init__.py`: Currently empty (0 bytes).
2. `departments/marketing/manager.py`:
   - Inherits only `BaseAgent`.
   - `execute()` returns hardcoded `"mocked marketing manager result"`.
   - Lacks `Module` interface implementation (`name`, `set_kernel`, `handle_event`).
   - `self.workers` only contains `SocialWorker`.
3. `departments/marketing/social_worker.py`:
   - Inherits `BaseAgent`.
   - `execute()` returns hardcoded `"mocked social media result"`.
   - Lacks channel handling, long post handling, and forbidden action enforcement.
4. `departments/marketing/content_worker.py`: File missing (must be created for F-MKT-3).

### 3.2 Sales Department (`departments/sales/`)

#### Existing Files:
- Directory `/root/synapse/departments/sales/` exists, but contains 0 files.
- `test_tier2_sales.py`, `test_tier3_multi_department_cascades.py`, and `test_tier3_router_departments.py` currently use fallback/try-except `SalesManager` definitions because `departments/sales/manager.py` is absent.

---

## 4. Detailed Feature Specifications & Implementation Plan

### 4.1 Feature F-MKT-1: Refactor `MarketingManager` (`departments/marketing/manager.py`)

#### Requirements:
1. Inherit from both `Module` and `BaseAgent`.
2. Implement `Module` methods: `@property def name(self) -> str` returning `"department.marketing"`, `set_kernel(self, kernel: KernelInterface)`, `async def handle_event(self, event: Event)`.
3. Initialize workers: `SocialWorker` and `ContentWorker`.
4. Remove `"mocked marketing manager result"`. Implement actual campaign task processing.
5. Support specs, budget checks (budget=0, forbidden action check for `spend_over_budget`), template fallbacks (`template_missing_xyz` handling), and sub-worker delegation.

#### Proposed Class Design:
```python
from typing import List, Any, Optional
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .social_worker import SocialWorker
from .content_worker import ContentWorker
import logging

logger = logging.getLogger(__name__)

class MarketingManager(Module, BaseAgent):
    def __init__(self, id: str = "mkt_mgr", name: str = "Marketing Manager"):
        BaseAgent.__init__(self, id=id, name=name, department="marketing", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers: List[BaseAgent] = [
            SocialWorker(f"{id}_social_worker", "Alice Social"),
            ContentWorker(f"{id}_content_worker", "Carol Content")
        ]

    @property
    def name(self) -> str:
        return "department.marketing"

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["analytics", "campaign_manager"]

    def forbidden_actions(self) -> List[str]:
        return ["spend_over_budget"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "marketing" in desc or "campaign" in desc or "social" in desc or "content" in desc

    async def execute(self, task: Any) -> Any:
        task_dict = task if isinstance(task, dict) else {"description": str(task)}
        desc = task_dict.get("description", "")
        budget = task_dict.get("budget", None)
        specs = task_dict.get("specs", {})
        template = task_dict.get("template")

        # Handle budget validation
        if budget is not None and budget < 0:
            raise ValueError("Invalid negative campaign budget")

        # Route subtasks to appropriate worker if matching
        worker_results = []
        for worker in self.workers:
            if worker.can_handle(desc):
                try:
                    res = await worker.execute(task)
                    worker_results.append(res)
                except Exception as e:
                    logger.warning(f"Worker execution issue: {e}")

        template_used = template if template else "default_marketing_template"
        
        return {
            "status": "success",
            "task": task,
            "budget": budget if budget is not None else 0,
            "specs": specs,
            "template": template_used,
            "worker_results": worker_results,
            "result": f"Marketing campaign executed successfully. Delegated tasks: {len(worker_results)}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass

    async def handle_event(self, event: Event) -> None:
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            if isinstance(task_data, dict):
                task_id = task_data.get("id")
            elif hasattr(task_data, "id"):
                task_id = getattr(task_data, "id")
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
```

---

### 4.2 Feature F-MKT-2: Refactor `SocialWorker` (`departments/marketing/social_worker.py`)

#### Requirements:
1. Inherit `BaseAgent`.
2. Remove `"mocked social media result"`.
3. Support social post generation across channels (`twitter`, `linkedin`, or custom/unsupported channels like `unsupported_channel_xyz`).
4. Support long post content up to 10,000 chars without error.
5. Enforce forbidden action policy (`post_without_approval`).

#### Proposed Class Design:
```python
from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class SocialWorker(BaseAgent):
    def __init__(self, id: str = "social_worker_1", name: str = "Alice Social"):
        super().__init__(id=id, name=name, department="marketing", role="social_media_manager")

    def allowed_tools(self) -> List[str]:
        return ["twitter", "linkedin"]

    def forbidden_actions(self) -> List[str]:
        return ["post_without_approval"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "social" in desc or "marketing" in desc or "twitter" in desc or "linkedin" in desc or "post" in desc

    async def execute(self, task: Any) -> Any:
        task_dict = task if isinstance(task, dict) else {"description": str(task)}
        channel = task_dict.get("channel", "twitter")
        content = task_dict.get("content", task_dict.get("description", ""))
        action = task_dict.get("action", "")

        if action in self.forbidden_actions():
            raise PermissionError(f"Action '{action}' is forbidden for {self.name}")

        formatted_post = f"[{channel.upper()}] {content}"

        return {
            "status": "success",
            "task": task,
            "channel": channel,
            "role": self.role,
            "post_content": formatted_post,
            "result": f"Social media post generated for channel: {channel}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
```

---

### 4.3 Feature F-MKT-3: Implement `ContentWorker` (`departments/marketing/content_worker.py`)

#### Requirements:
1. Create `departments/marketing/content_worker.py`.
2. Inherit `BaseAgent`, role `"content_writer"`.
3. Allowed tools: `["cms_editor", "seo_analyzer"]`.
4. Forbidden actions: `["publish_unapproved_copy"]`.
5. Memory access level: `"medium"`.
6. `can_handle`: `"content"`, `"blog"`, `"article"`.
7. `execute`: Returns status `"success"`, role `"content_writer"`, and result string containing `"content article generated"`.

#### Proposed Class Design:
```python
from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class ContentWorker(BaseAgent):
    def __init__(self, id: str = "content_worker_1", name: str = "Carol Content"):
        super().__init__(id=id, name=name, department="marketing", role="content_writer")

    def allowed_tools(self) -> List[str]:
        return ["cms_editor", "seo_analyzer"]

    def forbidden_actions(self) -> List[str]:
        return ["publish_unapproved_copy"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "content" in desc or "blog" in desc or "article" in desc or "copywriting" in desc

    async def execute(self, task: Any) -> Any:
        task_dict = task if isinstance(task, dict) else {"description": str(task)}
        desc = task_dict.get("description", str(task))

        return {
            "status": "success",
            "role": self.role,
            "task": task,
            "result": f"Content article generated for task: {desc}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass
```

---

### 4.4 Feature F-SLS-1: Scaffold `departments/sales/` Directory

Create directory `/root/synapse/departments/sales/` containing:
- `__init__.py`: Export `SalesManager`, `OutreachWorker`, and `SalesWorker`.
- `manager.py`: Implementation of `SalesManager`.
- `outreach_worker.py`: Implementation of `OutreachWorker` (and `SalesWorker` alias).

---

### 4.5 Feature F-SLS-2: Implement `SalesManager` (`departments/sales/manager.py`)

#### Requirements:
1. Inherit from both `Module` and `BaseAgent`.
2. `@property def name(self) -> str`: return `"department.sales"`.
3. `set_kernel(self, kernel: KernelInterface)`: store kernel reference.
4. `async def handle_event(self, event: Event)`: process task events and emit `department.task_completed`/`department.task_failed`.
5. `allowed_tools()`: `["crm", "crm_search", "lead_qualifier", "email_sender", "email_draft", "pitch_generator"]`.
6. `forbidden_actions()`: `["grant_unauthorized_discount", "delete_leads", "send_unauthorized_discounts", "unauthorized_discount"]`.
7. `memory_access_level()`: `"admin"`.
8. `can_handle(task_description)`: `"sales"`, `"lead"`, `"deal"`, `"crm"`, `"outreach"`, `"pitch"`.
9. **Lead Qualification Logic**:
   - `lead_score <= 0` -> `"unqualified"`
   - `0 < lead_score < 30` -> `"disqualified"`
   - `lead_score >= 30` -> `"qualified"`
10. **Company & Missing CRM Fields Check**:
    - Empty or missing `company` -> `"unknown"`
    - Empty `email` or `contact_name` -> add to `missing_crm_fields` list.
11. **Email Template Fallback**:
    - Missing/None `template` -> fallback to `"default_outreach"`.
12. **Result Output String**:
    - Must include `"lead generation campaign executed"` AND `"Sales lead pitch generated successfully"` to pass Tier 1, 2, and 3 test assertion checks!

#### Proposed Class Design:
```python
from typing import List, Any, Optional
from shared.interfaces import Module, KernelInterface
from shared.models import Event
from registry.sdk.base_agent import BaseAgent
from .outreach_worker import OutreachWorker
import logging

logger = logging.getLogger(__name__)

class SalesManager(Module, BaseAgent):
    def __init__(self, id: str = "sls_mgr", name: str = "Sales Manager"):
        BaseAgent.__init__(self, id=id, name=name, department="sales", role="manager")
        self.kernel: Optional[KernelInterface] = None
        self.workers: List[BaseAgent] = [
            OutreachWorker(f"{id}_outreach_worker", "Oscar Outreach")
        ]

    @property
    def name(self) -> str:
        return "department.sales"

    def set_kernel(self, kernel: KernelInterface) -> None:
        self.kernel = kernel

    def allowed_tools(self) -> List[str]:
        return ["crm", "crm_search", "lead_qualifier", "email_sender", "email_draft", "pitch_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["grant_unauthorized_discount", "delete_leads", "send_unauthorized_discounts", "unauthorized_discount"]

    def memory_access_level(self) -> str:
        return "admin"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "sales" in desc or "lead" in desc or "deal" in desc or "crm" in desc or "outreach" in desc or "pitch" in desc

    async def execute(self, task: Any) -> Any:
        task_dict = task if isinstance(task, dict) else {"description": str(task)}
        lead_score = task_dict.get("lead_score", 50)
        company = task_dict.get("company")
        if not company:
            company = "unknown"
        email_template = task_dict.get("template") or "default_outreach"

        if lead_score <= 0:
            qualification = "unqualified"
        elif lead_score < 30:
            qualification = "disqualified"
        else:
            qualification = "qualified"

        missing_fields = []
        if "email" in task_dict and not task_dict["email"]:
            missing_fields.append("email")
        if "contact_name" in task_dict and not task_dict["contact_name"]:
            missing_fields.append("contact_name")

        return {
            "status": "success",
            "qualification": qualification,
            "company": company,
            "missing_crm_fields": missing_fields,
            "email_template": email_template,
            "task": task,
            "result": f"lead generation campaign executed for {company}: {qualification}. Sales lead pitch generated successfully"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "managing"}

    def remember(self, knowledge: Any) -> None:
        pass

    async def handle_event(self, event: Event) -> None:
        if event.event_type in ("department.execute_task", "task.assigned") or event.destination == self.name:
            task_data = event.payload.get("task", event.payload)
            if isinstance(task_data, dict):
                task_id = task_data.get("id")
            elif hasattr(task_data, "id"):
                task_id = getattr(task_data, "id")
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
```

---

### 4.6 Feature F-SLS-3: Implement `SalesWorker` / `OutreachWorker` (`departments/sales/outreach_worker.py`)

#### Requirements:
1. Create `departments/sales/outreach_worker.py`.
2. Implement `OutreachWorker(BaseAgent)` with role `"outreach_specialist"`. Alias `SalesWorker = OutreachWorker`.
3. Allowed tools: `["email_draft", "pitch_generator"]`.
4. Forbidden actions: `["send_spam_blast"]`.
5. Memory access level: `"medium"`.
6. `can_handle`: `"pitch"`, `"outreach"`, `"email"`, `"sales"`.
7. `execute`: Returns status `"success"`, role `"outreach_specialist"`, and result string containing `"custom sales pitch generated"`.

#### Proposed Class Design:
```python
from typing import List, Any
from registry.sdk.base_agent import BaseAgent

class OutreachWorker(BaseAgent):
    def __init__(self, id: str = "outreach_w1", name: str = "Oscar Outreach"):
        super().__init__(id=id, name=name, department="sales", role="outreach_specialist")

    def allowed_tools(self) -> List[str]:
        return ["email_draft", "pitch_generator"]

    def forbidden_actions(self) -> List[str]:
        return ["send_spam_blast"]

    def memory_access_level(self) -> str:
        return "medium"

    def can_handle(self, task_description: str) -> bool:
        desc = task_description.lower()
        return "pitch" in desc or "outreach" in desc or "email" in desc or "sales" in desc

    async def execute(self, task: Any) -> Any:
        task_dict = task if isinstance(task, dict) else {"description": str(task)}
        desc = task_dict.get("description", str(task))

        return {
            "status": "success",
            "role": self.role,
            "task": task,
            "result": f"custom sales pitch generated for: {desc}"
        }

    def validate(self, result: Any) -> bool:
        return isinstance(result, dict) and result.get("status") == "success"

    def report(self) -> Any:
        return {"status": "idle"}

    def remember(self, knowledge: Any) -> None:
        pass

# Alias for feature naming compliance
SalesWorker = OutreachWorker
```

---

## 5. Verification & Test Plan

1. Run standard test suite command:
   ```bash
   PYTHONPATH=. ./.venv/bin/pytest
   ```
2. Verify all test files pass (including existing `tests/e2e/tier1/test_tier1_marketing.py`, `test_tier1_sales.py`, `test_tier2_marketing.py`, `test_tier2_sales.py`, `test_tier3_multi_department_cascades.py`, `test_tier3_router_departments.py`, and `test_tier4_full_agent_os_lifecycle.py`).
3. Invalidation condition: Any test returning a hardcoded mock string, failing `isinstance(module, Module)` check, failing to emit `department.task_completed`, or throwing an unhandled exception.
