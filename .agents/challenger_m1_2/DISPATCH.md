## 2026-08-06T03:05:23Z
You are Challenger 2 for Milestone 1: Core Infra Stress Testing.
Working Directory: /root/synapse/.agents/challenger_m1_2
Project Directory: /root/synapse

Required Files to Read First:
- /root/synapse/.agents/ORIGINAL_REQUEST.md
- /root/synapse/PROJECT.md
- /root/synapse/.agents/sub_orch_m1/SCOPE.md

Your Task:
1. Empirically verify Kernel & EventBus (KERN-001..004, EVTB-001..007, DEPT-001, DEPT-004) implementation.
2. Stress test event routing under load, unicast vs broadcast (`*`), wildcard topic subscriptions, async queue handling, DLQ routing for unroutable events, exception isolation, shutdown events, and DepartmentModule registration.
3. Run pytest: `PYTHONPATH=. ./.venv/bin/pytest`.
4. Render an explicit verdict (APPROVE or REJECT) in `/root/synapse/.agents/challenger_m1_2/handoff.md`.
5. Send a summary message back to parent with your verdict and test findings.
