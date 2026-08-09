## 2026-08-06T03:07:32+05:30

You are the Sub-Orchestrator for Milestone 3: Commercial & Operations Departments (Marketing, Sales, Personal, Echo).
Your working directory is: /root/synapse/.agents/sub_orch_m3
Main project directory: /root/synapse
Parent conversation ID: 73b72fea-f420-4d08-baf3-939db509f237

Instructions:
1. MUST read ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md and PROJECT.md at /root/synapse/PROJECT.md.
2. Initialize your BRIEFING.md, progress.md, and SCOPE.md in /root/synapse/.agents/sub_orch_m3/.
3. Scope:
   - Marketing Department:
     - F-MKT-1: Refactor MarketingManager (departments/marketing/manager.py) to inherit Module and BaseAgent, register with Kernel, remove "mocked marketing manager result", and process campaign tasks.
     - F-MKT-2: Refactor SocialWorker (departments/marketing/social_worker.py) to generate real platform posts, enforce forbidden actions, removing "mocked social media result".
     - F-MKT-3: Implement ContentWorker (departments/marketing/content_worker.py).
     - F-MKT-4: Create tests/test_marketing.py.
   - Sales Department:
     - F-SLS-1: Scaffold departments/sales/ directory (__init__.py, manager.py, outreach_worker.py).
     - F-SLS-2: Implement SalesManager (departments/sales/manager.py) inheriting Module and BaseAgent, registered with Kernel, handling lead gen & CRM strategy.
     - F-SLS-3: Implement SalesWorker (departments/sales/outreach_worker.py) generating outreach pitches & emails.
     - F-SLS-4: Create tests/test_sales.py.
   - Personal Department:
     - F-PRS-1: Refactor PersonalManager (departments/personal/manager.py) to inherit Module and BaseAgent, register with Kernel, remove "mocked personal manager result", handle schedule & finance oversight.
     - F-PRS-2: Refactor AssistantWorker (departments/personal/assistant_worker.py) to process calendar/email tasks, removing "mocked assistant result".
     - F-PRS-3: Create tests/test_personal.py.
   - Echo Department:
     - F-ECH-1 & F-ECH-2: Verify EchoDepartment (departments/echo/echo_manager.py) and create tests/test_echo.py.
4. Execute Milestone 3 using the iteration loop: Explorer -> Worker -> Reviewer -> Challenger -> Auditor (teamwork_preview_auditor). Verify every gate (build/tests pass, reviewers approve, challenger confirms, auditor clean).
5. Mark Milestone 3 complete in your SCOPE.md and send a handoff message back to parent when done.
