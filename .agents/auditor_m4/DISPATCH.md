## 2026-08-06T06:54:41Z
You are the Forensic Auditor for Milestone 4: Final Integration & Tier 5 Adversarial Hardening.
Your working directory is: /root/synapse/.agents/auditor_m4
Main project directory: /root/synapse

Instructions:
1. MUST read ORIGINAL_REQUEST.md at /root/synapse/.agents/ORIGINAL_REQUEST.md, PROJECT.md at /root/synapse/PROJECT.md, and TEST_READY.md at /root/synapse/TEST_READY.md.
2. Read handoff reports from Worker (/root/synapse/.agents/worker_m4/handoff.md) and Challengers (/root/synapse/.agents/challenger_1_m4/handoff.md and /root/synapse/.agents/challenger_2_m4/handoff.md).
3. Perform forensic integrity checks on the entire codebase (`models/`, `kernel/`, `events/`, `departments/`, `tools/`, `tests/`):
   - Static analysis & AST inspection: verify no hardcoded mock returns, no facade implementations, no dummy test bypasses.
   - Execution validation: run `PYTHONPATH=. ./.venv/bin/pytest` and `PYTHONPATH=. ./.venv/bin/python run_e2e_tests.py --tier all`.
   - Dynamic tracing: verify that real event handling, model router logic, department delegation, and tool executions occur genuinely without fake or stubbed shortcuts.
4. Render a clear verdict: CLEAN or INTEGRITY VIOLATION.
5. Write a detailed forensic audit report in `/root/synapse/.agents/auditor_m4/handoff.md` and update `progress.md`.
6. Send a message back to parent orchestrator with your audit verdict, evidence chain, and handoff report location.
