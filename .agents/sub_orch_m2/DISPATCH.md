## 2026-08-05T21:37:32Z
You are the Sub-Orchestrator for Milestone 2: Technical Departments (Engineering & Research).
Your working directory is: /root/synapse/.agents/sub_orch_m2
Main project directory: /root/synapse
Parent conversation ID: 73b72fea-f420-4d08-baf3-939db509f237

Instructions:
1. MUST read ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md and PROJECT.md at /root/synapse/PROJECT.md.
2. Initialize your BRIEFING.md, progress.md, and SCOPE.md in /root/synapse/.agents/sub_orch_m2/.
3. Scope:
   - Engineering Department:
     - F-ENG-1: Refactor EngineeringManager (departments/engineering/manager.py) to inherit Module and BaseAgent, register with Kernel, remove "mocked engineering manager result", and execute functional coding/architecture tasks.
     - F-ENG-2: Refactor BackendWorker (departments/engineering/backend_worker.py) to execute actual backend coding, API task processing, tool calls, and memory storage, removing "mocked backend result".
     - F-ENG-3: Implement QAWorker (departments/engineering/qa_worker.py) and DevOpsWorker (departments/engineering/devops_worker.py).
     - F-ENG-4: Create tests/test_engineering.py testing EngineeringManager and workers.
   - Research Department:
     - F-RES-1: Refactor ResearchManager (departments/research/manager.py) to inherit Module and BaseAgent, register with Kernel, parse research requests, delegate to platform workers, aggregate results, and output research report artifacts.
     - F-RES-2: Refactor platform workers in departments/research/workers/ (github.py, hn.py, product_hunt.py, reddit.py, twitter.py) to perform functional query searches, process data, and return non-empty structured results.
     - F-RES-3: Create tests/test_research.py testing ResearchManager and platform workers.
4. Execute Milestone 2 using the iteration loop: Explorer -> Worker -> Reviewer -> Challenger -> Auditor (teamwork_preview_auditor). Verify every gate (build/tests pass, reviewers approve, challenger confirms, auditor clean).
5. Mark Milestone 2 complete in your SCOPE.md and send a handoff message back to parent when done.
