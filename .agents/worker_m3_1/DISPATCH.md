## 2026-08-06T01:51:45Z
You are Worker 1 for Milestone 3 (Commercial & Operations Departments: Marketing, Sales, Personal, Echo).
Your working directory is: /root/synapse/.agents/worker_m3_1
Main project directory: /root/synapse

Mandatory files to read:
1. ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md
2. PROJECT.md at /root/synapse/PROJECT.md
3. SCOPE.md at /root/synapse/.agents/sub_orch_m3/SCOPE.md
4. Explorer 1 Analysis & Handoff at /root/synapse/.agents/explorer_m3_1_gen2/analysis.md and handoff.md
5. Explorer 2 Analysis & Handoff at /root/synapse/.agents/explorer_m3_2_gen2/analysis.md and handoff.md
6. Explorer 3 Analysis & Handoff at /root/synapse/.agents/explorer_m3_3_gen2/analysis.md and handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your tasks:
1. Marketing Department:
   - F-MKT-1: Refactor `MarketingManager` (`departments/marketing/manager.py`) to inherit `Module` and `BaseAgent` (`class MarketingManager(Module, BaseAgent):`), implement `@property def name(self) -> str:` returning `"department.marketing"`, `set_kernel`, `handle_event` for `department.execute_task` / `task.assigned`, remove `"mocked marketing manager result"`, and process campaign tasks (budget checks, specs processing, template fallbacks, delegating subtasks).
   - F-MKT-2: Refactor `SocialWorker` (`departments/marketing/social_worker.py`) to generate real platform posts (`twitter`, `linkedin`, etc.), enforce forbidden actions, handle long content (up to 10k chars), removing `"mocked social media result"`.
   - F-MKT-3: Implement `ContentWorker` (`departments/marketing/content_worker.py`) with role `"content_writer"`, allowed tools `["cms_editor", "seo_analyzer"]`, and article/blog post generation.
   - F-MKT-4: Create `tests/test_marketing.py` verifying unit methods, Kernel module registration, event handling, real output payload generation, and absence of mock strings.

2. Sales Department:
   - F-SLS-1: Scaffold `departments/sales/` directory (`__init__.py`, `manager.py`, `outreach_worker.py`).
   - F-SLS-2: Implement `SalesManager` (`departments/sales/manager.py`) inheriting `Module` and `BaseAgent` (`class SalesManager(Module, BaseAgent):`), `@property def name` returning `"department.sales"`, `set_kernel`, `handle_event`, lead qualification score thresholds (`<=0` unqualified, `<30` disqualified, `>=30` qualified), CRM missing fields (`email`, `contact_name`), company default (`"unknown"`), email template fallback (`"default_outreach"`). Include key output substrings `"lead generation campaign executed"` and `"Sales lead pitch generated successfully"`.
   - F-SLS-3: Implement `OutreachWorker` (and `SalesWorker` alias) (`departments/sales/outreach_worker.py`) generating outreach pitches & emails. Include key output substring `"custom sales pitch generated"`.
   - F-SLS-4: Create `tests/test_sales.py` verifying unit methods, Kernel registration, lead qualification logic, outreach pitch generation, event handling, and absence of mock strings.

3. Personal Department:
   - F-PRS-1: Refactor `PersonalManager` (`departments/personal/manager.py`) to inherit `Module` and `BaseAgent` (`class PersonalManager(Module, BaseAgent):`), `@property def name` returning `"department.personal"`, `set_kernel`, `handle_event`, remove `"mocked personal manager result"`, handle schedule & finance oversight.
   - F-PRS-2: Refactor `AssistantWorker` (`departments/personal/assistant_worker.py`) to process calendar and email tasks, removing `"mocked assistant result"`.
   - F-PRS-3: Create `tests/test_personal.py` verifying unit methods, Kernel registration, schedule/calendar/email tasks, event handling, and absence of mock strings.

4. Echo Department:
   - F-ECH-1 & F-ECH-2: Verify `EchoDepartment` (`departments/echo/echo_manager.py`) functionality and create `tests/test_echo.py` verifying ping/pong roundtrip, payload preservation, Kernel module registration, and event routing.

5. Build & Test Verification:
   - Run `PYTHONPATH=. ./.venv/bin/pytest` and ensure ALL 145 existing tests + all new unit tests pass with 100% success rate!

Write your changes report to `/root/synapse/.agents/worker_m3_1/changes.md` and handoff to `/root/synapse/.agents/worker_m3_1/handoff.md`.
